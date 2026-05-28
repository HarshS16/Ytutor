"""
Quiz router — handles quiz generation and retrieval.

Endpoints:
- POST /api/quiz/generate — Generate quiz for a playlist
- GET  /api/quiz/{playlist_id} — Get generated quiz questions
"""

import asyncio
import logging
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.schemas import QuizGenerateRequest, QuizQuestionResponse, QuizListResponse
from db.database import get_db
from db import crud
from generators.quiz import generate_quiz

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["quiz"])


@router.post("/quiz/generate", response_model=QuizListResponse)
async def generate_quiz_endpoint(
    request: QuizGenerateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Generate quiz questions from playlist transcripts."""
    playlist = await crud.get_playlist(db, request.playlist_id)
    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist not found")

    if playlist.status != "ready":
        raise HTTPException(status_code=400, detail="Playlist is not ready yet")

    videos = await crud.get_playlist_videos(db, request.playlist_id)
    videos_with_transcript = [v for v in videos if v.transcript_text]

    if not videos_with_transcript:
        raise HTTPException(status_code=400, detail="No videos with transcripts")

    # Clear existing quizzes
    await crud.delete_playlist_quizzes(db, request.playlist_id)

    # Generate quiz questions
    per_video = max(3, request.count // len(videos_with_transcript))
    all_questions = []

    for video in videos_with_transcript:
        result = await asyncio.to_thread(
            generate_quiz,
            video.transcript_text,
            video.title,
            per_video,
        )

        if "questions" in result:
            all_questions.extend(result["questions"])

    all_questions = all_questions[:request.count]

    # Save to DB
    if all_questions:
        db_records = [
            {
                "playlist_id": request.playlist_id,
                "question": q["question"],
                "options": q.get("options"),
                "correct_answer": q["correct_answer"],
                "question_type": q.get("question_type", "mcq"),
                "explanation": q.get("explanation", ""),
            }
            for q in all_questions
        ]
        saved = await crud.create_quizzes_batch(db, db_records)
    else:
        saved = []

    return QuizListResponse(
        questions=[
            QuizQuestionResponse(
                id=q.id,
                question=q.question,
                question_type=q.question_type,
                options=q.options,
                correct_answer=q.correct_answer,
                explanation=q.explanation,
            )
            for q in saved
        ],
        total=len(saved),
    )


@router.get("/quiz/{playlist_id}", response_model=QuizListResponse)
async def get_quiz(playlist_id: int, db: AsyncSession = Depends(get_db)):
    """Get all quiz questions for a playlist."""
    quizzes = await crud.get_playlist_quizzes(db, playlist_id)
    return QuizListResponse(
        questions=[
            QuizQuestionResponse(
                id=q.id,
                question=q.question,
                question_type=q.question_type,
                options=q.options,
                correct_answer=q.correct_answer,
                explanation=q.explanation,
            )
            for q in quizzes
        ],
        total=len(quizzes),
    )
