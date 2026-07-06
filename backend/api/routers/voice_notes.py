"""
Voice notes router.

Authenticated endpoints for recording/uploading spoken notes, transcribing them
with local Whisper, organizing the transcript, and exporting the result.
"""

import logging
import os
import re
import shutil
import tempfile
from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import get_current_user
from api.models.schemas import (
    VoiceNoteOrganizeRequest,
    VoiceNoteResponse,
    VoiceNotesListResponse,
)
from db import crud
from db.database import get_db
from generators.pdf_export import generate_pdf
from generators.voice_notes import organize_voice_transcript
from ingestion.transcript import transcribe_audio_file

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/voice-notes", tags=["voice-notes"])

MAX_UPLOAD_MB = int(os.getenv("VOICE_NOTE_MAX_UPLOAD_MB", "50"))
KEEP_AUDIO = os.getenv("VOICE_NOTE_KEEP_AUDIO", "false").lower() == "true"
ALLOWED_AUDIO_TYPES = {
    "audio/webm",
    "audio/wav",
    "audio/wave",
    "audio/x-wav",
    "audio/mpeg",
    "audio/mp3",
    "audio/mp4",
    "audio/m4a",
    "video/mp4",
}
ALLOWED_AUDIO_EXTENSIONS = {".webm", ".wav", ".mp3", ".m4a", ".mp4", ".mpeg", ".ogg", ".opus"}


def _safe_filename(title: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", title or "voice_note").strip("._-")
    return (safe[:50] or "voice_note") + ".pdf"


def _content_disposition(filename: str) -> str:
    encoded = quote(filename, safe="")
    return f"attachment; filename=\"ytutor_voice_note.pdf\"; filename*=UTF-8''{encoded}"


def _extension_for_upload(upload: UploadFile) -> str:
    suffix = Path(upload.filename or "").suffix.lower()
    if suffix in ALLOWED_AUDIO_EXTENSIONS:
        return suffix
    content_type = (upload.content_type or "").lower()
    if "webm" in content_type:
        return ".webm"
    if "wav" in content_type:
        return ".wav"
    if "mpeg" in content_type or "mp3" in content_type:
        return ".mp3"
    if "mp4" in content_type or "m4a" in content_type:
        return ".m4a"
    return ".audio"


def _is_supported_audio_upload(upload: UploadFile) -> bool:
    """
    Validate audio uploads without rejecting browser MIME parameters.

    MediaRecorder commonly sends values like "audio/webm;codecs=opus", while
    some file pickers use "application/octet-stream" for otherwise valid audio.
    """
    content_type = (upload.content_type or "").lower().split(";", 1)[0].strip()
    suffix = Path(upload.filename or "").suffix.lower()

    if content_type in ALLOWED_AUDIO_TYPES:
        return True
    if content_type.startswith("audio/"):
        return True
    if content_type.startswith("video/") and suffix in ALLOWED_AUDIO_EXTENSIONS:
        return True
    if content_type in {"", "application/octet-stream"} and suffix in ALLOWED_AUDIO_EXTENSIONS:
        return True
    return False


def _title_from_transcript(transcript: str, fallback: str) -> str:
    words = re.sub(r"\s+", " ", transcript or "").strip().split(" ")
    if not words:
        return fallback
    title = " ".join(words[:8]).strip(".,:;!?")
    return title[:80] or fallback


async def _require_owned_voice_note(
    db: AsyncSession,
    voice_note_id: int,
    user_id: int,
):
    note = await crud.get_voice_note(db, voice_note_id)
    if not note:
        raise HTTPException(status_code=404, detail="Voice note not found")
    if note.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to access this voice note")
    return note


@router.get("", response_model=VoiceNotesListResponse)
async def list_voice_notes(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """List saved voice-note sessions for the current user."""
    notes = await crud.get_user_voice_notes(db, current_user.id)
    return VoiceNotesListResponse(voice_notes=notes, total=len(notes))


@router.post("/transcribe", response_model=VoiceNoteResponse)
async def transcribe_voice_note(
    title: str = Form(default=""),
    audio: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Upload audio, transcribe it with local Whisper, and save the transcript."""
    raw_content_type = audio.content_type or ""
    content_type = raw_content_type.lower().split(";", 1)[0].strip()
    if not _is_supported_audio_upload(audio):
        logger.warning(
            "Rejected voice-note upload: filename=%s content_type=%s",
            audio.filename,
            raw_content_type,
        )
        raise HTTPException(status_code=400, detail="Unsupported audio format")

    max_bytes = MAX_UPLOAD_MB * 1024 * 1024
    suffix = _extension_for_upload(audio)
    temp_dir = Path(tempfile.mkdtemp(prefix="ytutor_voice_"))
    audio_path = temp_dir / f"voice_note{suffix}"
    saved_bytes = 0

    try:
        with audio_path.open("wb") as out_file:
            while True:
                chunk = await audio.read(1024 * 1024)
                if not chunk:
                    break
                saved_bytes += len(chunk)
                if saved_bytes > max_bytes:
                    raise HTTPException(
                        status_code=413,
                        detail=f"Audio is too large. Limit is {MAX_UPLOAD_MB} MB.",
                    )
                out_file.write(chunk)

        result = transcribe_audio_file(str(audio_path), label=f"voice-note-user-{current_user.id}")
        if not result:
            raise HTTPException(status_code=400, detail="Could not transcribe this audio")

        transcript = result["text"].strip()
        note_title = (title or "").strip() or _title_from_transcript(transcript, "Voice Note")
        note = await crud.create_voice_note(
            db,
            user_id=current_user.id,
            title=note_title[:256],
            raw_transcript=transcript,
            organized_content="",
            status="transcribed",
            detected_language=result.get("language", "") or "",
            duration_seconds=float(result.get("duration_seconds") or 0),
            audio_mime_type=content_type,
            error_message=None,
        )
        return note

    finally:
        if not KEEP_AUDIO:
            shutil.rmtree(temp_dir, ignore_errors=True)


@router.get("/{voice_note_id}", response_model=VoiceNoteResponse)
async def get_voice_note(
    voice_note_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get one saved voice-note session."""
    return await _require_owned_voice_note(db, voice_note_id, current_user.id)


@router.post("/{voice_note_id}/organize", response_model=VoiceNoteResponse)
async def organize_voice_note(
    voice_note_id: int,
    request: VoiceNoteOrganizeRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Organize a voice-note transcript into structured markdown notes."""
    note = await _require_owned_voice_note(db, voice_note_id, current_user.id)
    raw_transcript = (request.raw_transcript if request.raw_transcript is not None else note.raw_transcript).strip()
    if not raw_transcript:
        raise HTTPException(status_code=400, detail="Transcript is empty")

    title = (request.title or note.title or "Voice Note").strip()[:256]
    await crud.update_voice_note(
        db,
        voice_note_id,
        status="organizing",
        raw_transcript=raw_transcript,
        title=title,
        error_message=None,
    )

    try:
        organized = organize_voice_transcript(raw_transcript, title)
        await crud.update_voice_note(
            db,
            voice_note_id,
            organized_content=organized,
            raw_transcript=raw_transcript,
            title=title,
            status="ready",
            error_message=None,
        )
    except Exception as exc:
        logger.error("Voice note organization failed: %s", exc, exc_info=True)
        await crud.update_voice_note(
            db,
            voice_note_id,
            status="error",
            error_message=str(exc),
        )
        raise HTTPException(status_code=500, detail=str(exc))

    refreshed = await crud.get_voice_note(db, voice_note_id)
    return refreshed


@router.delete("/{voice_note_id}")
async def delete_voice_note(
    voice_note_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Delete a saved voice-note session."""
    await _require_owned_voice_note(db, voice_note_id, current_user.id)
    await crud.delete_voice_note(db, voice_note_id)
    return {"message": "Voice note deleted"}


@router.get("/{voice_note_id}/export/pdf")
async def export_voice_note_pdf(
    voice_note_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Export a voice note as a polished PDF."""
    note = await _require_owned_voice_note(db, voice_note_id, current_user.id)
    content = note.organized_content or note.raw_transcript
    if not content:
        raise HTTPException(status_code=400, detail="No voice note content to export")

    pdf_bytes = generate_pdf(
        playlist_title=note.title or "Voice Note",
        notes=[{"content": content, "note_type": "Voice"}],
    )
    filename = f"ytutor_voice_{_safe_filename(note.title)}"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": _content_disposition(filename)},
    )
