"""
SQLite database connection and session management.

Uses SQLAlchemy async with aiosqlite for non-blocking DB operations.
Tables are auto-created on first connection.
"""

import os
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./ytutor.db")

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+asyncpg://", 1)
elif DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

# Neon DB adds query parameters like ?sslmode=require that asyncpg doesn't support directly
# or that break when parsed. We can safely strip the query string from the URL.
if "?" in DATABASE_URL and "sqlite" not in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.split("?")[0]

connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    connect_args=connect_args,
    pool_pre_ping=True,   # Test connections before use — fixes NeonDB idle disconnects
    pool_recycle=300,      # Recycle connections every 5 min (before NeonDB's timeout)
)

async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    """Base class for all ORM models."""
    pass


async def init_db():
    """Create all tables if they don't exist."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await _ensure_voice_note_columns(conn)


async def _ensure_voice_note_columns(conn):
    """Add optional voice-note columns for existing local databases."""
    dialect = conn.dialect.name
    columns = {
        "cleaned_transcript": "TEXT DEFAULT ''",
        "language_mode": "VARCHAR(32) DEFAULT 'hinglish'",
        "transcription_model": "VARCHAR(64) DEFAULT ''",
        "transcription_source": "VARCHAR(64) DEFAULT ''",
    }

    if dialect == "sqlite":
        result = await conn.execute(text("PRAGMA table_info(voice_notes)"))
        existing = {row[1] for row in result.fetchall()}
        for name, definition in columns.items():
            if name not in existing:
                await conn.execute(text(f"ALTER TABLE voice_notes ADD COLUMN {name} {definition}"))
    elif dialect in {"postgresql", "postgres"}:
        for name, definition in columns.items():
            await conn.execute(text(f"ALTER TABLE voice_notes ADD COLUMN IF NOT EXISTS {name} {definition}"))


async def get_db() -> AsyncSession:
    """Dependency that provides a database session."""
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()
