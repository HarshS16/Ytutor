"""
CRUD operations for all database models.

Provides async functions for creating, reading, updating, and
deleting records in the SQLite database.
"""

import logging
from typing import Optional
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from db.models import Playlist, Video, Chunk, Note, Flashcard, Quiz, User, ChatMessage, VoiceNote

logger = logging.getLogger(__name__)


# ── User CRUD ───────────────────────────────────────────────────────

async def get_user_by_id(db: AsyncSession, user_id: int) -> Optional[User]:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalars().first()

async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    result = await db.execute(select(User).where(User.email == email))
    return result.scalars().first()

async def get_user_by_username(db: AsyncSession, username: str) -> Optional[User]:
    result = await db.execute(select(User).where(User.username == username))
    return result.scalars().first()

async def create_user(db: AsyncSession, email: str, username: str, password_hash: str) -> User:
    db_user = User(email=email, username=username, password_hash=password_hash)
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user

async def update_user_password(db: AsyncSession, user_id: int, new_password_hash: str) -> None:
    """Update a user's password hash."""
    stmt = update(User).where(User.id == user_id).values(password_hash=new_password_hash)
    await db.execute(stmt)
    await db.commit()
    logger.info(f"Password updated for user {user_id}")


# ── Playlist CRUD ─────────────────────────────────────────────────

async def create_playlist(
    db: AsyncSession, 
    playlist_url: str, 
    youtube_playlist_id: str,
    user_id: Optional[int] = None,
    title: str = "",
    description: str = "",
    thumbnail: str = "",
    channel: str = "",
    video_count: int = 0,
    status: str = "pending",
) -> Playlist:
    """Create a new playlist record."""
    playlist = Playlist(
        playlist_url=playlist_url,
        youtube_playlist_id=youtube_playlist_id,
        user_id=user_id,
        title=title,
        description=description,
        thumbnail=thumbnail,
        channel=channel,
        video_count=video_count,
        status=status,
    )
    db.add(playlist)
    await db.commit()
    await db.refresh(playlist)
    logger.info(f"Created playlist: {playlist.id} — {playlist.title}")
    return playlist


async def get_playlist(db: AsyncSession, playlist_id: int) -> Optional[Playlist]:
    """Get a playlist by ID."""
    result = await db.execute(select(Playlist).where(Playlist.id == playlist_id))
    return result.scalar_one_or_none()


async def get_playlist_by_youtube_id(db: AsyncSession, youtube_playlist_id: str) -> Optional[Playlist]:
    """Get a playlist by its YouTube playlist ID."""
    result = await db.execute(
        select(Playlist).where(Playlist.youtube_playlist_id == youtube_playlist_id)
    )
    return result.scalar_one_or_none()


async def get_all_playlists(db: AsyncSession, user_id: Optional[int] = None) -> list[Playlist]:
    """Get all playlists, optionally filtered by user."""
    stmt = select(Playlist).order_by(Playlist.created_at.desc())
    if user_id is not None:
        stmt = stmt.where(Playlist.user_id == user_id)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def update_playlist_status(
    db: AsyncSession, playlist_id: int, status: str, error_message: str = None
) -> None:
    """Update playlist processing status."""
    stmt = (
        update(Playlist)
        .where(Playlist.id == playlist_id)
        .values(status=status, error_message=error_message)
    )
    await db.execute(stmt)
    await db.commit()
    logger.info(f"Playlist {playlist_id} status → {status}")


async def update_playlist_metadata(db: AsyncSession, playlist_id: int, **kwargs) -> None:
    """Update playlist metadata fields."""
    stmt = update(Playlist).where(Playlist.id == playlist_id).values(**kwargs)
    await db.execute(stmt)
    await db.commit()


async def delete_playlist(db: AsyncSession, playlist_id: int) -> None:
    """Delete a playlist and all related data."""
    playlist = await get_playlist(db, playlist_id)
    if playlist:
        await db.delete(playlist)
        await db.commit()
        logger.info(f"Deleted playlist {playlist_id}")


# ── Video CRUD ────────────────────────────────────────────────────

async def create_video(db: AsyncSession, **kwargs) -> Video:
    """Create a new video record."""
    video = Video(**kwargs)
    db.add(video)
    await db.commit()
    await db.refresh(video)
    return video


async def create_videos_batch(db: AsyncSession, videos_data: list[dict]) -> list[Video]:
    """Create multiple video records in a batch."""
    videos = [Video(**data) for data in videos_data]
    db.add_all(videos)
    await db.commit()
    for v in videos:
        await db.refresh(v)
    logger.info(f"Created {len(videos)} video records")
    return videos


async def get_video(db: AsyncSession, video_id: int) -> Optional[Video]:
    """Get a video by ID."""
    result = await db.execute(select(Video).where(Video.id == video_id))
    return result.scalar_one_or_none()


async def get_playlist_videos(db: AsyncSession, playlist_id: int) -> list[Video]:
    """Get all videos for a playlist, ordered by position."""
    result = await db.execute(
        select(Video)
        .where(Video.playlist_id == playlist_id)
        .order_by(Video.position)
    )
    return list(result.scalars().all())


async def update_video(db: AsyncSession, video_id: int, **kwargs) -> None:
    """Update video fields."""
    stmt = update(Video).where(Video.id == video_id).values(**kwargs)
    await db.execute(stmt)
    await db.commit()


# ── Chunk CRUD ────────────────────────────────────────────────────

async def create_chunks_batch(db: AsyncSession, chunks_data: list[dict]) -> list[Chunk]:
    """Create multiple chunk records in a batch."""
    chunks = [Chunk(**data) for data in chunks_data]
    db.add_all(chunks)
    await db.commit()
    logger.info(f"Created {len(chunks)} chunk records")
    return chunks


async def get_video_chunks(db: AsyncSession, video_id: int) -> list[Chunk]:
    """Get all chunks for a video."""
    result = await db.execute(
        select(Chunk)
        .where(Chunk.video_id == video_id)
        .order_by(Chunk.chunk_index)
    )
    return list(result.scalars().all())


# ── Notes CRUD ────────────────────────────────────────────────────

async def create_note(db: AsyncSession, **kwargs) -> Note:
    """Create a new note record."""
    note = Note(**kwargs)
    db.add(note)
    await db.commit()
    await db.refresh(note)
    return note


async def get_playlist_notes(db: AsyncSession, playlist_id: int) -> list[Note]:
    """Get all notes for a playlist."""
    result = await db.execute(
        select(Note)
        .where(Note.playlist_id == playlist_id)
        .order_by(Note.created_at.desc())
    )
    return list(result.scalars().all())


async def delete_playlist_notes(db: AsyncSession, playlist_id: int) -> None:
    """Delete all notes for a playlist."""
    result = await db.execute(
        select(Note).where(Note.playlist_id == playlist_id)
    )
    notes = result.scalars().all()
    for note in notes:
        await db.delete(note)
    await db.commit()


async def replace_playlist_notes(db: AsyncSession, playlist_id: int, notes_data: list[dict]) -> list[Note]:
    """Replace playlist notes in one commit after generation succeeds."""
    result = await db.execute(
        select(Note).where(Note.playlist_id == playlist_id)
    )
    old_notes = result.scalars().all()
    for note in old_notes:
        await db.delete(note)

    notes = [Note(**data) for data in notes_data]
    db.add_all(notes)
    await db.commit()

    for note in notes:
        await db.refresh(note)

    logger.info(f"Replaced notes for playlist {playlist_id}: {len(notes)} notes")
    return notes


# ── Flashcard CRUD ────────────────────────────────────────────────

async def create_flashcards_batch(db: AsyncSession, flashcards_data: list[dict]) -> list[Flashcard]:
    """Create multiple flashcard records."""
    flashcards = [Flashcard(**data) for data in flashcards_data]
    db.add_all(flashcards)
    await db.commit()
    logger.info(f"Created {len(flashcards)} flashcards")
    return flashcards


async def get_playlist_flashcards(db: AsyncSession, playlist_id: int) -> list[Flashcard]:
    """Get all flashcards for a playlist."""
    result = await db.execute(
        select(Flashcard)
        .where(Flashcard.playlist_id == playlist_id)
        .order_by(Flashcard.created_at.desc())
    )
    return list(result.scalars().all())


async def delete_playlist_flashcards(db: AsyncSession, playlist_id: int) -> None:
    """Delete all flashcards for a playlist."""
    result = await db.execute(
        select(Flashcard).where(Flashcard.playlist_id == playlist_id)
    )
    cards = result.scalars().all()
    for card in cards:
        await db.delete(card)
    await db.commit()


# ── Quiz CRUD ─────────────────────────────────────────────────────

async def create_quizzes_batch(db: AsyncSession, quizzes_data: list[dict]) -> list[Quiz]:
    """Create multiple quiz records."""
    quizzes = [Quiz(**data) for data in quizzes_data]
    db.add_all(quizzes)
    await db.commit()
    logger.info(f"Created {len(quizzes)} quiz questions")
    return quizzes


async def get_playlist_quizzes(db: AsyncSession, playlist_id: int) -> list[Quiz]:
    """Get all quiz questions for a playlist."""
    result = await db.execute(
        select(Quiz).where(Quiz.playlist_id == playlist_id).order_by(Quiz.id)
    )
    return list(result.scalars().all())


async def delete_playlist_quizzes(db: AsyncSession, playlist_id: int) -> None:
    """Delete all quizzes for a playlist."""
    result = await db.execute(
        select(Quiz).where(Quiz.playlist_id == playlist_id)
    )
    quizzes = result.scalars().all()
    for quiz in quizzes:
        await db.delete(quiz)
    await db.commit()


# ── Chat History CRUD ──────────────────────────────────────────────

async def save_chat_message(
    db: AsyncSession,
    user_id: int,
    playlist_id: int,
    role: str,
    content: str,
    sources: Optional[list] = None
) -> ChatMessage:
    """Save a chat message to history."""
    msg = ChatMessage(
        user_id=user_id,
        playlist_id=playlist_id,
        role=role,
        content=content,
        sources=sources
    )
    db.add(msg)
    await db.commit()
    await db.refresh(msg)
    return msg


async def get_chat_history(db: AsyncSession, user_id: int, playlist_id: int) -> list[ChatMessage]:
    """Get chat history for a specific user and playlist."""
    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.user_id == user_id, ChatMessage.playlist_id == playlist_id)
        .order_by(ChatMessage.created_at.asc())
    )
    return list(result.scalars().all())


# Voice Notes CRUD

async def create_voice_note(db: AsyncSession, **kwargs) -> VoiceNote:
    """Create a spoken voice-note session."""
    note = VoiceNote(**kwargs)
    db.add(note)
    await db.commit()
    await db.refresh(note)
    logger.info(f"Created voice note {note.id} for user {note.user_id}")
    return note


async def get_voice_note(db: AsyncSession, voice_note_id: int) -> Optional[VoiceNote]:
    """Get a voice note by ID."""
    result = await db.execute(select(VoiceNote).where(VoiceNote.id == voice_note_id))
    return result.scalar_one_or_none()


async def get_user_voice_notes(db: AsyncSession, user_id: int) -> list[VoiceNote]:
    """Get all voice notes for a user, newest first."""
    result = await db.execute(
        select(VoiceNote)
        .where(VoiceNote.user_id == user_id)
        .order_by(VoiceNote.updated_at.desc(), VoiceNote.created_at.desc())
    )
    return list(result.scalars().all())


async def update_voice_note(db: AsyncSession, voice_note_id: int, **kwargs) -> None:
    """Update voice-note fields."""
    stmt = update(VoiceNote).where(VoiceNote.id == voice_note_id).values(**kwargs)
    await db.execute(stmt)
    await db.commit()


async def delete_voice_note(db: AsyncSession, voice_note_id: int) -> None:
    """Delete a voice-note session."""
    note = await get_voice_note(db, voice_note_id)
    if note:
        await db.delete(note)
        await db.commit()
        logger.info(f"Deleted voice note {voice_note_id}")
