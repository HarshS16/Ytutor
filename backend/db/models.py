"""
SQLAlchemy ORM models for Ytutor AI.

Defines tables: playlists, videos, chunks, notes, flashcards, quizzes.
"""

import json
from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, Text, Float, DateTime,
    ForeignKey, Enum as SAEnum, JSON
)
from sqlalchemy.orm import relationship
from db.database import Base


class User(Base):
    """User account model."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(256), unique=True, nullable=False, index=True)
    username = Column(String(128), unique=True, nullable=False)
    password_hash = Column(String(512), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    playlists = relationship("Playlist", back_populates="user", cascade="all, delete-orphan")
    chat_messages = relationship("ChatMessage", back_populates="user", cascade="all, delete-orphan")


class Playlist(Base):
    """A YouTube playlist imported by the user."""
    __tablename__ = "playlists"

    id = Column(Integer, primary_key=True, autoincrement=True)
    playlist_url = Column(String(512), nullable=False)
    youtube_playlist_id = Column(String(64), unique=True, nullable=False)
    title = Column(String(512), default="")
    description = Column(Text, default="")
    thumbnail = Column(String(512), default="")
    channel = Column(String(256), default="")
    video_count = Column(Integer, default=0)
    status = Column(
        String(20),
        default="pending",  # pending | extracting | processing | ready | error
    )
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True)

    # Relationships
    user = relationship("User", back_populates="playlists")
    videos = relationship("Video", back_populates="playlist", cascade="all, delete-orphan")
    notes = relationship("Note", back_populates="playlist", cascade="all, delete-orphan")
    flashcards = relationship("Flashcard", back_populates="playlist", cascade="all, delete-orphan")
    quizzes = relationship("Quiz", back_populates="playlist", cascade="all, delete-orphan")
    chat_messages = relationship("ChatMessage", back_populates="playlist", cascade="all, delete-orphan")


class Video(Base):
    """A single video within a playlist."""
    __tablename__ = "videos"

    id = Column(Integer, primary_key=True, autoincrement=True)
    playlist_id = Column(Integer, ForeignKey("playlists.id", ondelete="CASCADE"), nullable=False)
    video_id = Column(String(32), nullable=False)  # YouTube video ID
    title = Column(String(512), default="")
    duration = Column(Integer, default=0)  # Duration in seconds
    thumbnail = Column(String(512), default="")
    transcript_text = Column(Text, default="")
    summary = Column(Text, default="")
    position = Column(Integer, default=0)  # Order in playlist
    status = Column(
        String(20),
        default="pending",  # pending | processing | ready | error | no_transcript
    )
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    playlist = relationship("Playlist", back_populates="videos")
    chunks = relationship("Chunk", back_populates="video", cascade="all, delete-orphan")


class Chunk(Base):
    """A text chunk from a video transcript, stored for RAG retrieval."""
    __tablename__ = "chunks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    video_id = Column(Integer, ForeignKey("videos.id", ondelete="CASCADE"), nullable=False)
    chunk_text = Column(Text, nullable=False)
    chunk_index = Column(Integer, default=0)
    embedding_id = Column(String(64), default="")  # ChromaDB doc ID
    timestamp_start = Column(Float, default=0.0)  # Start time in seconds
    timestamp_end = Column(Float, default=0.0)  # End time in seconds
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    video = relationship("Video", back_populates="chunks")


class Note(Base):
    """Generated notes for a playlist or specific video."""
    __tablename__ = "notes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    playlist_id = Column(Integer, ForeignKey("playlists.id", ondelete="CASCADE"), nullable=False)
    video_id = Column(Integer, ForeignKey("videos.id", ondelete="SET NULL"), nullable=True)
    content = Column(Text, default="")
    note_type = Column(String(20), default="detailed")  # concise | detailed | revision
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    playlist = relationship("Playlist", back_populates="notes")


class Flashcard(Base):
    """Auto-generated flashcard from transcript content."""
    __tablename__ = "flashcards"

    id = Column(Integer, primary_key=True, autoincrement=True)
    playlist_id = Column(Integer, ForeignKey("playlists.id", ondelete="CASCADE"), nullable=False)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    difficulty = Column(String(10), default="medium")  # easy | medium | hard
    topic = Column(String(256), default="")
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    playlist = relationship("Playlist", back_populates="flashcards")


class Quiz(Base):
    """Auto-generated quiz question from transcript content."""
    __tablename__ = "quizzes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    playlist_id = Column(Integer, ForeignKey("playlists.id", ondelete="CASCADE"), nullable=False)
    question = Column(Text, nullable=False)
    options = Column(JSON, nullable=True)  # List of options (for MCQ)
    correct_answer = Column(Text, nullable=False)
    question_type = Column(String(20), default="mcq")  # mcq | true_false | short_answer
    explanation = Column(Text, default="")
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    playlist = relationship("Playlist", back_populates="quizzes")


class ChatMessage(Base):
    """Saved chat messages for persistent history."""
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    playlist_id = Column(Integer, ForeignKey("playlists.id", ondelete="CASCADE"), nullable=False)
    role = Column(String(20), nullable=False)  # "user" | "assistant"
    content = Column(Text, nullable=False)
    sources = Column(JSON, nullable=True)  # Used for assistant's citations
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    user = relationship("User", back_populates="chat_messages")
    playlist = relationship("Playlist", back_populates="chat_messages")
