"""
Flashcards router — handles flashcard generation and retrieval.

Endpoints:
- POST /api/flashcards/generate — Generate flashcards for a playlist
- GET  /api/flashcards/{playlist_id} — Get generated flashcards
"""

import asyncio
import logging
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.schemas import FlashcardGenerateRequest, FlashcardResponse, FlashcardsListResponse
from api.auth import get_current_user
from db.database import get_db
from db import crud
from generators.flashcards import generate_flashcards

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["flashcards"])


@router.post("/flashcards/generate", response_model=FlashcardsListResponse)
async def generate_flashcards_endpoint(
    request: FlashcardGenerateRequest,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Generate flashcards from playlist transcripts."""
    playlist = await crud.get_playlist(db, request.playlist_id)
    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist not found")
        
    if playlist.user_id is not None and playlist.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this playlist")

    if playlist.status != "ready":
        raise HTTPException(status_code=400, detail="Playlist is not ready yet")

    # Get videos with transcripts
    videos = await crud.get_playlist_videos(db, request.playlist_id)
    videos_with_transcript = [v for v in videos if v.transcript_text]

    if not videos_with_transcript:
        raise HTTPException(status_code=400, detail="No videos with transcripts")

    # Clear existing flashcards
    await crud.delete_playlist_flashcards(db, request.playlist_id)

    # Combine transcripts and generate
    # Distribute count across videos
    per_video = max(3, request.count // len(videos_with_transcript))
    all_flashcards = []

    for video in videos_with_transcript:
        result = await asyncio.to_thread(
            generate_flashcards,
            video.transcript_text,
            video.title,
            per_video,
        )

        if "flashcards" in result:
            for fc in result["flashcards"]:
                fc["playlist_id"] = request.playlist_id
            all_flashcards.extend(result["flashcards"])

    # Trim to requested count
    all_flashcards = all_flashcards[:request.count]

    # Save to DB
    if all_flashcards:
        db_records = [
            {
                "playlist_id": request.playlist_id,
                "question": fc["question"],
                "answer": fc["answer"],
                "difficulty": fc.get("difficulty", "medium"),
                "topic": fc.get("topic", ""),
            }
            for fc in all_flashcards
        ]
        saved = await crud.create_flashcards_batch(db, db_records)
    else:
        saved = []

    return FlashcardsListResponse(
        flashcards=[
            FlashcardResponse(
                id=fc.id,
                question=fc.question,
                answer=fc.answer,
                difficulty=fc.difficulty,
                topic=fc.topic,
            )
            for fc in saved
        ],
        total=len(saved),
    )


@router.get("/flashcards/{playlist_id}", response_model=FlashcardsListResponse)
async def get_flashcards(
    playlist_id: int, 
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get all flashcards for a playlist."""
    playlist = await crud.get_playlist(db, playlist_id)
    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist not found")
        
    if playlist.user_id is not None and playlist.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this playlist")
        
    flashcards = await crud.get_playlist_flashcards(db, playlist_id)
    return FlashcardsListResponse(
        flashcards=[
            FlashcardResponse(
                id=fc.id,
                question=fc.question,
                answer=fc.answer,
                difficulty=fc.difficulty,
                topic=fc.topic,
            )
            for fc in flashcards
        ],
        total=len(flashcards),
    )
