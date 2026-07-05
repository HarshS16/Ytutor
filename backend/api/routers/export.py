"""
Export router — handles PDF export of playlist content.

Endpoints:
- GET /api/export/pdf/{playlist_id} — Download PDF with notes, flashcards, quiz
"""

import logging
import re
from urllib.parse import quote
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from db.database import get_db
from db import crud
from api.auth import get_current_user
from generators.pdf_export import generate_pdf

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["export"])


def _download_filename(title: str) -> str:
    """Build an HTTP-header-safe PDF download filename."""
    safe_title = re.sub(r"[^A-Za-z0-9._-]+", "_", title or "export").strip("._-")
    safe_title = safe_title[:50] or "export"
    return f"ytutor_{safe_title}.pdf"


def _content_disposition(filename: str) -> str:
    """
    Return an ASCII-only Content-Disposition header.

    Starlette encodes header values as latin-1, so non-ASCII filenames need
    the RFC 5987 filename* form instead of raw Unicode in filename.
    """
    encoded = quote(filename, safe="")
    return f"attachment; filename=\"ytutor_export.pdf\"; filename*=UTF-8''{encoded}"


@router.get("/export/pdf/{playlist_id}")
async def export_pdf(
    playlist_id: int, 
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Export playlist content as a PDF document."""
    playlist = await crud.get_playlist(db, playlist_id)
    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist not found")
        
    if playlist.user_id is not None and playlist.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this playlist")

    # Gather all content
    notes = await crud.get_playlist_notes(db, playlist_id)
    flashcards = await crud.get_playlist_flashcards(db, playlist_id)
    quizzes = await crud.get_playlist_quizzes(db, playlist_id)

    if not notes and not flashcards and not quizzes:
        raise HTTPException(
            status_code=400,
            detail="No content to export. Generate notes, flashcards, or quiz first.",
        )

    # Convert ORM objects to dicts for PDF generator
    notes_data = [
        {"content": n.content, "note_type": n.note_type}
        for n in notes
    ] if notes else None

    flashcards_data = [
        {
            "question": fc.question,
            "answer": fc.answer,
            "difficulty": fc.difficulty,
            "topic": fc.topic,
        }
        for fc in flashcards
    ] if flashcards else None

    quizzes_data = [
        {
            "question": q.question,
            "question_type": q.question_type,
            "options": q.options,
            "correct_answer": q.correct_answer,
            "explanation": q.explanation,
        }
        for q in quizzes
    ] if quizzes else None

    # Generate PDF
    pdf_bytes = generate_pdf(
        playlist_title=playlist.title,
        notes=notes_data,
        flashcards=flashcards_data,
        quizzes=quizzes_data,
    )

    filename = _download_filename(playlist.title)

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": _content_disposition(filename),
        },
    )
