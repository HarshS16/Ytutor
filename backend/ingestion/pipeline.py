"""
Full ingestion pipeline orchestrator.

Coordinates the complete playlist processing flow:
1. Extract playlist metadata via yt-dlp
2. Fetch transcripts for each video
3. Clean and chunk transcripts
4. Generate embeddings
5. Store in ChromaDB
6. Update database records
"""

import asyncio
import logging
import time

from sqlalchemy.ext.asyncio import AsyncSession

from db import crud
from ingestion.youtube import fetch_playlist_metadata
from ingestion.transcript import fetch_transcript, process_transcript
from ingestion.chunker import chunk_with_timestamps
from ingestion.embedder import embed_texts
from ingestion.vector_store import upsert_chunks, clear_collection

logger = logging.getLogger(__name__)


async def run_ingestion(db: AsyncSession, playlist_id: int) -> dict:
    """
    Run the full ingestion pipeline for a playlist.

    Updates playlist and video statuses as processing progresses.

    Args:
        db: Database session
        playlist_id: ID of the playlist to process

    Returns:
        Dict with processing stats:
        - videos_processed, videos_failed, total_chunks, elapsed_seconds
    """
    start_time = time.time()

    logger.info(f"Starting ingestion for playlist {playlist_id}")
    await crud.update_playlist_status(db, playlist_id, "processing")

    stats = {
        "videos_processed": 0,
        "videos_failed": 0,
        "total_chunks": 0,
        "elapsed_seconds": 0,
        "errors": [],
    }

    try:
        # Get all videos for this playlist
        videos = await crud.get_playlist_videos(db, playlist_id)

        if not videos:
            await crud.update_playlist_status(db, playlist_id, "error", "No videos found")
            return stats

        # Clear existing vector data
        await asyncio.to_thread(clear_collection, playlist_id)

        # Process each video
        for video in videos:
            try:
                logger.info(f"Processing video {video.position + 1}/{len(videos)}: {video.title}")
                await crud.update_video(db, video.id, status="processing")

                # Step 1: Fetch transcript
                raw_transcript = await asyncio.to_thread(
                    fetch_transcript, video.video_id
                )

                if not raw_transcript:
                    logger.warning(f"No transcript for video {video.video_id}")
                    await crud.update_video(
                        db, video.id,
                        status="no_transcript",
                        error_message="No transcript available"
                    )
                    stats["videos_failed"] += 1
                    stats["errors"].append(f"No transcript: {video.title}")
                    continue

                # Step 2: Process transcript (clean + merge)
                processed = process_transcript(raw_transcript)

                if not processed["full_text"]:
                    await crud.update_video(
                        db, video.id,
                        status="error",
                        error_message="Transcript processing produced empty result"
                    )
                    stats["videos_failed"] += 1
                    continue

                # Save cleaned transcript to DB
                await crud.update_video(
                    db, video.id,
                    transcript_text=processed["full_text"],
                    status="processing",
                )

                # Step 3: Chunk transcript with timestamps
                chunks_with_ts = chunk_with_timestamps(
                    processed["full_text"],
                    processed["segments"],
                )

                if not chunks_with_ts:
                    await crud.update_video(db, video.id, status="ready")
                    stats["videos_processed"] += 1
                    continue

                # Step 4: Generate embeddings
                chunk_texts = [c["text"] for c in chunks_with_ts]
                embeddings = await asyncio.to_thread(
                    embed_texts, chunk_texts, 64, False
                )

                # Step 5: Prepare metadata and upsert to ChromaDB
                metadatas = []
                chunk_db_records = []

                for chunk_data in chunks_with_ts:
                    meta = {
                        "video_id": video.video_id,
                        "video_title": video.title,
                        "video_db_id": str(video.id),
                        "chunk_index": chunk_data["chunk_index"],
                        "timestamp_start": chunk_data["timestamp_start"],
                        "timestamp_end": chunk_data["timestamp_end"],
                        "playlist_id": str(playlist_id),
                    }
                    metadatas.append(meta)

                    chunk_db_records.append({
                        "video_id": video.id,
                        "chunk_text": chunk_data["text"],
                        "chunk_index": chunk_data["chunk_index"],
                        "embedding_id": "",  # Will be set by ChromaDB
                        "timestamp_start": chunk_data["timestamp_start"],
                        "timestamp_end": chunk_data["timestamp_end"],
                    })

                # Upsert to vector store
                num_upserted = await asyncio.to_thread(
                    upsert_chunks,
                    playlist_id,
                    chunk_texts,
                    embeddings,
                    metadatas,
                )

                # Save chunk records to SQLite
                await crud.create_chunks_batch(db, chunk_db_records)

                # Mark video as ready
                await crud.update_video(db, video.id, status="ready")

                stats["videos_processed"] += 1
                stats["total_chunks"] += num_upserted

                logger.info(
                    f"Video '{video.title}' processed: {num_upserted} chunks"
                )

            except Exception as e:
                logger.error(f"Error processing video {video.video_id}: {e}")
                await crud.update_video(
                    db, video.id,
                    status="error",
                    error_message=str(e)
                )
                stats["videos_failed"] += 1
                stats["errors"].append(f"{video.title}: {str(e)}")

        # Update playlist status
        if stats["videos_processed"] > 0:
            await crud.update_playlist_status(db, playlist_id, "ready")
        else:
            await crud.update_playlist_status(
                db, playlist_id, "error",
                "No videos could be processed"
            )

    except Exception as e:
        logger.error(f"Pipeline error for playlist {playlist_id}: {e}")
        await crud.update_playlist_status(db, playlist_id, "error", str(e))
        stats["errors"].append(str(e))

    stats["elapsed_seconds"] = round(time.time() - start_time, 2)

    logger.info(
        f"Ingestion complete for playlist {playlist_id}: "
        f"{stats['videos_processed']} processed, {stats['videos_failed']} failed, "
        f"{stats['total_chunks']} chunks, {stats['elapsed_seconds']}s"
    )

    return stats
