"""
Export router — handles PDF export of playlist content.

Endpoints:
- GET /api/export/pdf/{playlist_id} — Download PDF with notes, flashcards, quiz
"""

import logging
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from db.database import get_db
from db import crud
from generators.pdf_export import generate_pdf

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["export"])


@router.get("/export/pdf/{playlist_id}")
async def export_pdf(playlist_id: int, db: AsyncSession = Depends(get_db)):
    """Export playlist content as a PDF document."""
    playlist = await crud.get_playlist(db, playlist_id)
    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist not found")

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

    filename = f"ytutor_{playlist.title[:50].replace(' ', '_')}.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )
