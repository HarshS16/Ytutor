"""
Notes router: background hierarchical notes generation and retrieval.
"""

import asyncio
import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.schemas import (
    NotesGenerateRequest,
    NoteResponse,
    NotesListResponse,
    NotesGenerateJobResponse,
    NotesJobStatusResponse,
)
from api.auth import get_current_user
from db.database import get_db, async_session
from db import crud
from generators.notes import generate_hierarchical_notes
from ingestion.chunker import chunk_text

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["notes"])

_notes_jobs: dict[str, dict] = {}


def _job_response(job_id: str, job: dict) -> dict:
    return {
        "job_id": job_id,
        "status": job.get("status", "queued"),
        "playlist_id": job.get("playlist_id"),
        "note_type": job.get("note_type", "detailed"),
        "videos_total": job.get("videos_total", 0),
        "videos_done": job.get("videos_done", 0),
        "sections_total": job.get("sections_total", 0),
        "sections_done": job.get("sections_done", 0),
        "current_video_title": job.get("current_video_title"),
        "current_section": job.get("current_section"),
        "error": job.get("error"),
        "done": job.get("status") in ("complete", "error"),
    }


def _update_job(job_id: str, **kwargs) -> None:
    job = _notes_jobs.setdefault(job_id, {})
    job.update(kwargs)
    job["updated_at"] = datetime.now(timezone.utc).isoformat()


def _fallback_chunks_from_transcript(video) -> list[dict]:
    chunks = chunk_text(video.transcript_text or "")
    if not chunks:
        return []

    duration = float(video.duration or 0)
    total = len(chunks)
    result = []
    for idx, text in enumerate(chunks):
        result.append({
            "text": text,
            "timestamp_start": round((idx / total) * duration, 1) if duration else 0.0,
            "timestamp_end": round(((idx + 1) / total) * duration, 1) if duration else 0.0,
        })
    return result


async def _chunks_for_video(db: AsyncSession, video) -> list:
    chunks = await crud.get_video_chunks(db, video.id)
    if chunks:
        return [
            {
                "text": chunk.chunk_text,
                "timestamp_start": chunk.timestamp_start,
                "timestamp_end": chunk.timestamp_end,
            }
            for chunk in chunks
        ]
    return _fallback_chunks_from_transcript(video)


async def _run_notes_job(
    job_id: str,
    playlist_id: int,
    video_id: int | None,
    note_type: str,
    user_id: int,
) -> None:
    generated_notes: list[dict] = []

    try:
        async with async_session() as db:
            playlist = await crud.get_playlist(db, playlist_id)
            if not playlist:
                raise ValueError("Playlist not found")
            if playlist.user_id is not None and playlist.user_id != user_id:
                raise PermissionError("Not authorized to access this playlist")

            videos = await crud.get_playlist_videos(db, playlist_id)
            if video_id:
                videos = [v for v in videos if v.id == video_id]

            videos = [v for v in videos if v.transcript_text]
            if not videos:
                raise ValueError("No videos with transcripts available")

            _update_job(
                job_id,
                status="running",
                videos_total=len(videos),
                videos_done=0,
                sections_total=0,
                sections_done=0,
            )

            for video_index, video in enumerate(videos, start=1):
                chunks = await _chunks_for_video(db, video)
                _update_job(
                    job_id,
                    current_video_title=video.title,
                    current_section=f"Video {video_index}/{len(videos)}: preparing sections",
                )

                def progress(section_progress: dict) -> None:
                    section_index = section_progress["section_index"]
                    section_total = section_progress["sections_total"]
                    timestamp_range = section_progress["timestamp_range"]
                    prior_sections = _notes_jobs[job_id].get("_completed_before_video", 0)
                    _update_job(
                        job_id,
                        sections_total=prior_sections + section_total,
                        sections_done=prior_sections + max(0, section_index - 1),
                        current_section=(
                            f"Video {video_index}/{len(videos)}, "
                            f"section {section_index}/{section_total}: {timestamp_range}"
                        ),
                    )

                result = await asyncio.to_thread(
                    generate_hierarchical_notes,
                    chunks,
                    video.title,
                    note_type,
                    progress,
                )

                if "error" in result:
                    raise ValueError(result["error"])

                completed_before = _notes_jobs[job_id].get("_completed_before_video", 0)
                sections_total = result.get("sections_total", 0)
                _update_job(
                    job_id,
                    videos_done=video_index,
                    sections_total=completed_before + sections_total,
                    sections_done=completed_before + sections_total,
                    _completed_before_video=completed_before + sections_total,
                )

                generated_notes.append({
                    "playlist_id": playlist_id,
                    "video_id": video.id,
                    "content": result["content"],
                    "note_type": note_type,
                })

            await crud.replace_playlist_notes(db, playlist_id, generated_notes)

            _update_job(
                job_id,
                status="complete",
                current_section="Complete",
                current_video_title=None,
                error=None,
            )

    except Exception as exc:
        logger.error("Notes job %s failed: %s", job_id, exc, exc_info=True)
        _update_job(
            job_id,
            status="error",
            error=str(exc),
        )


@router.post("/notes/generate", response_model=NotesGenerateJobResponse)
async def generate_notes_endpoint(
    request: NotesGenerateRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """Start background hierarchical notes generation."""
    playlist = await crud.get_playlist(db, request.playlist_id)
    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist not found")

    if playlist.user_id is not None and playlist.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this playlist")

    videos = await crud.get_playlist_videos(db, request.playlist_id)
    if request.video_id:
        videos = [v for v in videos if v.id == request.video_id]

    videos_with_transcript = [v for v in videos if v.transcript_text]
    if not videos_with_transcript:
        raise HTTPException(status_code=400, detail="No videos with transcripts available")

    job_id = str(uuid.uuid4())
    _notes_jobs[job_id] = {
        "status": "queued",
        "playlist_id": request.playlist_id,
        "note_type": request.note_type,
        "videos_total": len(videos_with_transcript),
        "videos_done": 0,
        "sections_total": 0,
        "sections_done": 0,
        "current_video_title": None,
        "current_section": "Queued",
        "error": None,
        "user_id": current_user.id,
        "_completed_before_video": 0,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    background_tasks.add_task(
        _run_notes_job,
        job_id,
        request.playlist_id,
        request.video_id,
        request.note_type,
        current_user.id,
    )

    return NotesGenerateJobResponse(**_job_response(job_id, _notes_jobs[job_id]))


@router.get("/notes/status/{job_id}", response_model=NotesJobStatusResponse)
async def get_notes_job_status(
    job_id: str,
    current_user = Depends(get_current_user),
):
    """Get background notes generation progress."""
    job = _notes_jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Notes job not found")
    if job.get("user_id") != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this notes job")
    return NotesJobStatusResponse(**_job_response(job_id, job))


@router.get("/notes/{playlist_id}", response_model=NotesListResponse)
async def get_notes(
    playlist_id: int,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """Get generated notes for a playlist."""
    playlist = await crud.get_playlist(db, playlist_id)
    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist not found")

    if playlist.user_id is not None and playlist.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this playlist")

    notes = await crud.get_playlist_notes(db, playlist_id)
    return NotesListResponse(
        notes=[
            NoteResponse(
                id=n.id,
                playlist_id=n.playlist_id,
                video_id=n.video_id,
                content=n.content,
                note_type=n.note_type,
                created_at=n.created_at,
            )
            for n in notes
        ],
        total=len(notes),
    )
