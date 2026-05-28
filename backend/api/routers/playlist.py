"""
Playlist router — handles playlist import, retrieval, and status.

Endpoints:
- POST /api/playlist/import  — Import a new playlist
- GET  /api/playlists         — List all playlists
- GET  /api/playlist/{id}     — Get playlist details with videos
- GET  /api/playlist/{id}/status — Get processing status
- DELETE /api/playlist/{id}   — Delete a playlist
"""

import asyncio
import logging
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.schemas import (
    PlaylistImportRequest, PlaylistResponse, PlaylistWithVideosResponse,
    PlaylistListResponse, VideoInfo, ProcessingStatus,
)
from db.database import get_db
from db import crud
from ingestion.youtube import fetch_playlist_metadata, extract_playlist_id
from ingestion.pipeline import run_ingestion
from ingestion.vector_store import get_collection_stats

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["playlist"])


async def _background_ingest(playlist_id: int):
    """Run ingestion in the background with its own DB session."""
    from db.database import async_session
    async with async_session() as db:
        try:
            await run_ingestion(db, playlist_id)
        except Exception as e:
            logger.error(f"Background ingestion failed: {e}")
            await crud.update_playlist_status(db, playlist_id, "error", str(e))


@router.post("/playlist/import", response_model=PlaylistResponse)
async def import_playlist(
    request: PlaylistImportRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """
    Import a YouTube playlist.

    1. Validates the URL
    2. Extracts playlist metadata via yt-dlp
    3. Creates DB records
    4. Kicks off background processing (transcript extraction + embedding)
    """
    # Validate URL
    playlist_id_yt = extract_playlist_id(request.playlist_url)
    if not playlist_id_yt:
        raise HTTPException(status_code=400, detail="Invalid YouTube playlist URL")

    # Check if already imported
    existing = await crud.get_playlist_by_youtube_id(db, playlist_id_yt)
    if existing:
        return PlaylistResponse(
            id=existing.id,
            playlist_url=existing.playlist_url,
            youtube_playlist_id=existing.youtube_playlist_id,
            title=existing.title,
            description=existing.description,
            thumbnail=existing.thumbnail,
            channel=existing.channel,
            video_count=existing.video_count,
            status=existing.status,
            error_message=existing.error_message,
            created_at=existing.created_at,
        )

    # Fetch metadata from YouTube
    try:
        metadata = await asyncio.to_thread(fetch_playlist_metadata, request.playlist_url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to fetch playlist: {e}")
        raise HTTPException(status_code=502, detail="Failed to fetch playlist from YouTube")

    # Create playlist record
    playlist = await crud.create_playlist(
        db,
        playlist_url=request.playlist_url,
        youtube_playlist_id=metadata["playlist_id"],
        title=metadata["title"],
        description=metadata.get("description", ""),
        thumbnail=metadata.get("thumbnail", ""),
        channel=metadata.get("channel", ""),
        video_count=len(metadata["videos"]),
        status="extracting",
    )

    # Create video records
    videos_data = [
        {
            "playlist_id": playlist.id,
            "video_id": v["video_id"],
            "title": v["title"],
            "duration": v["duration"],
            "thumbnail": v["thumbnail"],
            "position": v["position"],
            "status": "pending",
        }
        for v in metadata["videos"]
    ]
    await crud.create_videos_batch(db, videos_data)

    # Start background processing
    background_tasks.add_task(_background_ingest, playlist.id)

    logger.info(f"Playlist imported: {playlist.id} — {playlist.title} ({len(metadata['videos'])} videos)")

    return PlaylistResponse(
        id=playlist.id,
        playlist_url=playlist.playlist_url,
        youtube_playlist_id=playlist.youtube_playlist_id,
        title=playlist.title,
        description=playlist.description,
        thumbnail=playlist.thumbnail,
        channel=playlist.channel,
        video_count=playlist.video_count,
        status=playlist.status,
        created_at=playlist.created_at,
    )


@router.get("/playlists", response_model=PlaylistListResponse)
async def list_playlists(db: AsyncSession = Depends(get_db)):
    """List all imported playlists."""
    playlists = await crud.get_all_playlists(db)
    return PlaylistListResponse(
        playlists=[
            PlaylistResponse(
                id=p.id,
                playlist_url=p.playlist_url,
                youtube_playlist_id=p.youtube_playlist_id,
                title=p.title,
                description=p.description,
                thumbnail=p.thumbnail,
                channel=p.channel,
                video_count=p.video_count,
                status=p.status,
                error_message=p.error_message,
                created_at=p.created_at,
            )
            for p in playlists
        ],
        total=len(playlists),
    )


@router.get("/playlist/{playlist_id}", response_model=PlaylistWithVideosResponse)
async def get_playlist(playlist_id: int, db: AsyncSession = Depends(get_db)):
    """Get playlist details with all video info."""
    playlist = await crud.get_playlist(db, playlist_id)
    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist not found")

    videos = await crud.get_playlist_videos(db, playlist_id)

    return PlaylistWithVideosResponse(
        id=playlist.id,
        playlist_url=playlist.playlist_url,
        youtube_playlist_id=playlist.youtube_playlist_id,
        title=playlist.title,
        description=playlist.description,
        thumbnail=playlist.thumbnail,
        channel=playlist.channel,
        video_count=playlist.video_count,
        status=playlist.status,
        error_message=playlist.error_message,
        created_at=playlist.created_at,
        videos=[
            VideoInfo(
                id=v.id,
                video_id=v.video_id,
                title=v.title,
                duration=v.duration,
                thumbnail=v.thumbnail,
                position=v.position,
                status=v.status,
                has_transcript=bool(v.transcript_text),
            )
            for v in videos
        ],
    )


@router.get("/playlist/{playlist_id}/status", response_model=ProcessingStatus)
async def get_playlist_status(playlist_id: int, db: AsyncSession = Depends(get_db)):
    """Get processing status for a playlist."""
    playlist = await crud.get_playlist(db, playlist_id)
    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist not found")

    videos = await crud.get_playlist_videos(db, playlist_id)
    processed = sum(1 for v in videos if v.status in ("ready", "no_transcript"))
    failed = sum(1 for v in videos if v.status == "error")
    total = len(videos)

    # Get chunk stats
    try:
        stats = get_collection_stats(playlist_id)
        total_chunks = stats.get("total_chunks", 0)
    except Exception:
        total_chunks = 0

    progress = (processed / total * 100) if total > 0 else 0

    return ProcessingStatus(
        playlist_id=playlist_id,
        status=playlist.status,
        videos_total=total,
        videos_processed=processed,
        videos_failed=failed,
        total_chunks=total_chunks,
        progress_percent=round(progress, 1),
    )


@router.delete("/playlist/{playlist_id}")
async def delete_playlist(playlist_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a playlist and all associated data."""
    playlist = await crud.get_playlist(db, playlist_id)
    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist not found")

    # Clear vector store
    try:
        from ingestion.vector_store import clear_collection
        clear_collection(playlist_id)
    except Exception as e:
        logger.warning(f"Error clearing vector store: {e}")

    await crud.delete_playlist(db, playlist_id)
    return {"status": "deleted", "playlist_id": playlist_id}
