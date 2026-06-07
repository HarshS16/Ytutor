"""
Notes router — handles notes generation and retrieval.

Endpoints:
- POST /api/notes/generate — Generate notes for a playlist
- GET  /api/notes/{playlist_id} — Get generated notes
"""

import asyncio
import logging
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.schemas import NotesGenerateRequest, NoteResponse, NotesListResponse
from api.auth import get_current_user
from db.database import get_db
from db import crud
from generators.notes import generate_notes

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["notes"])


@router.post("/notes/generate", response_model=NotesListResponse)
async def generate_notes_endpoint(
    request: NotesGenerateRequest,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Generate notes for a playlist (or specific video)."""
    playlist = await crud.get_playlist(db, request.playlist_id)
    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist not found")
        
    if playlist.user_id is not None and playlist.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this playlist")

    if playlist.status != "ready":
        raise HTTPException(status_code=400, detail="Playlist is not ready yet")

    # Get videos with transcripts
    videos = await crud.get_playlist_videos(db, request.playlist_id)
    if request.video_id:
        videos = [v for v in videos if v.id == request.video_id]

    videos_with_transcript = [v for v in videos if v.transcript_text]
    if not videos_with_transcript:
        raise HTTPException(status_code=400, detail="No videos with transcripts available")

    # Clear existing notes for this playlist
    await crud.delete_playlist_notes(db, request.playlist_id)

    # Generate notes for each video
    created_notes = []
    for video in videos_with_transcript:
        result = await asyncio.to_thread(
            generate_notes,
            video.transcript_text,
            video.title,
            request.note_type,
        )

        if "error" in result:
            logger.warning(f"Notes generation failed for video {video.id}: {result['error']}")
            continue

        note = await crud.create_note(
            db,
            playlist_id=request.playlist_id,
            video_id=video.id,
            content=result["content"],
            note_type=request.note_type,
        )
        created_notes.append(note)

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
            for n in created_notes
        ],
        total=len(created_notes),
    )


@router.get("/notes/{playlist_id}", response_model=NotesListResponse)
async def get_notes(
    playlist_id: int, 
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
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
