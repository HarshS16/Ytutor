"""
Pydantic request/response schemas for Ytutor AI API.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, EmailStr


# ── Auth Schemas ──────────────────────────────────────────────────

class UserCreate(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6)

class UserResponse(BaseModel):
    id: int
    email: str
    username: str

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse


class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ForgotPasswordResponse(BaseModel):
    message: str
    otp: Optional[str] = None  # Only populated when explicitly enabled for local development

class ResetPasswordRequest(BaseModel):
    email: EmailStr
    otp: str = Field(..., min_length=6, max_length=6)
    new_password: str = Field(..., min_length=6)

class ResetPasswordResponse(BaseModel):
    message: str


# ── Playlist Schemas ──────────────────────────────────────────────

class PlaylistImportRequest(BaseModel):
    """Request to import a YouTube playlist or standalone video."""
    playlist_url: str = Field(..., description="YouTube playlist or video URL")


class VideoInfo(BaseModel):
    """Video information within a playlist."""
    id: int
    video_id: str
    title: str
    duration: int = 0
    thumbnail: str = ""
    position: int = 0
    status: str = "pending"
    has_transcript: bool = False


class PlaylistResponse(BaseModel):
    """Response with playlist details."""
    id: int
    playlist_url: str
    youtube_playlist_id: str
    title: str
    description: str = ""
    thumbnail: str = ""
    channel: str = ""
    video_count: int = 0
    status: str = "pending"
    error_message: Optional[str] = None
    created_at: Optional[datetime] = None


class PlaylistWithVideosResponse(PlaylistResponse):
    """Playlist details with all video info."""
    videos: list[VideoInfo] = []


class PlaylistListResponse(BaseModel):
    """Response with list of playlists."""
    playlists: list[PlaylistResponse]
    total: int


# ── Chat Schemas ──────────────────────────────────────────────────

class ChatRequest(BaseModel):
    """Chat query request."""
    playlist_id: int = Field(..., description="Playlist ID to chat with")
    message: str = Field(..., min_length=1, max_length=2000, description="User message")
    session_id: str = Field(default="", description="Optional session ID")


class SourceCitation(BaseModel):
    """Source citation from a video."""
    video_title: str
    video_id: str = ""
    timestamp_start: float = 0
    timestamp_end: float = 0
    timestamp_display: str = ""
    snippet: str = ""
    score: float = 0


class ChatResponse(BaseModel):
    """Chat response with answer and sources."""
    answer: str
    sources: list[SourceCitation] = []
    found_context: bool = True


# ── Notes Schemas ─────────────────────────────────────────────────

class NotesGenerateRequest(BaseModel):
    """Request to generate notes."""
    playlist_id: int
    video_id: Optional[int] = None  # None = generate for all videos
    note_type: str = Field(default="detailed", pattern="^(concise|detailed|revision)$")


class NoteResponse(BaseModel):
    """Single note response."""
    id: int
    playlist_id: int
    video_id: Optional[int] = None
    content: str
    note_type: str
    created_at: Optional[datetime] = None


class NotesListResponse(BaseModel):
    """Response with list of notes."""
    notes: list[NoteResponse]
    total: int


# ── Flashcard Schemas ─────────────────────────────────────────────

class FlashcardGenerateRequest(BaseModel):
    """Request to generate flashcards."""
    playlist_id: int
    count: int = Field(default=10, ge=5, le=30)


class FlashcardResponse(BaseModel):
    """Single flashcard response."""
    id: int
    question: str
    answer: str
    difficulty: str = "medium"
    topic: str = ""


class FlashcardsListResponse(BaseModel):
    """Response with list of flashcards."""
    flashcards: list[FlashcardResponse]
    total: int


# ── Quiz Schemas ──────────────────────────────────────────────────

class QuizGenerateRequest(BaseModel):
    """Request to generate a quiz."""
    playlist_id: int
    count: int = Field(default=10, ge=5, le=30)


class QuizQuestionResponse(BaseModel):
    """Single quiz question response."""
    id: int
    question: str
    question_type: str = "mcq"
    options: Optional[list[str]] = None
    correct_answer: str
    explanation: str = ""


class QuizListResponse(BaseModel):
    """Response with list of quiz questions."""
    questions: list[QuizQuestionResponse]
    total: int


# ── Export Schemas ────────────────────────────────────────────────

class ExportRequest(BaseModel):
    """Request to export playlist content as PDF."""
    playlist_id: int
    include_notes: bool = True
    include_flashcards: bool = True
    include_quiz: bool = True


# ── Processing Status ────────────────────────────────────────────

class ProcessingStatus(BaseModel):
    """Playlist processing status with live progress."""
    playlist_id: int
    status: str
    videos_total: int = 0
    videos_processed: int = 0
    videos_failed: int = 0
    total_chunks: int = 0
    progress_percent: float = 0
    current_video: Optional[int] = None
    current_video_title: Optional[str] = None
    current_phase: Optional[str] = None
