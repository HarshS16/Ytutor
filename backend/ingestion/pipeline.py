"""
Full ingestion pipeline orchestrator.

Coordinates the complete playlist processing flow:
1. Extract playlist metadata via yt-dlp
2. Download audio and transcribe with Whisper
3. Clean and chunk transcripts
4. Generate embeddings
5. Store in ChromaDB (using temp collection for safe swap)
6. Update database records

Rate-limit handling:
- Configurable inter-video delay to avoid hammering YouTube
- Circuit breaker: pauses for a cooldown after consecutive 429 failures

Safe ingestion:
- Uses a temporary ChromaDB collection during ingestion
- Only swaps to live after all videos are processed successfully
- On failure, the old collection data is preserved
"""

import asyncio
import logging
import time

from sqlalchemy.ext.asyncio import AsyncSession

from db import crud
from ingestion.youtube import fetch_playlist_metadata
from ingestion.transcript import transcribe_video, process_transcript
from ingestion.chunker import chunk_with_timestamps
from ingestion.embedder import embed_texts
from ingestion.vector_store import (
    upsert_chunks,
    clear_collection,
    create_temp_collection,
    swap_collection,
    cleanup_temp_collection,
)

logger = logging.getLogger(__name__)

# ── Rate-limit configuration ──────────────────────────────────────
INTER_VIDEO_DELAY_SECONDS = 10     # Delay between each video's transcript fetch
RATE_LIMIT_COOLDOWN_SECONDS = 60   # Cooldown after consecutive rate-limit hits
CONSECUTIVE_FAIL_THRESHOLD = 3     # Number of consecutive failures before cooldown

# ── Live progress tracking ─────────────────────────────────────────
# In-memory dict keyed by playlist_id. Updated during processing so
# the /api/playlist/{id}/status endpoint can report current_video.
_ingestion_progress: dict[int, dict] = {}


def get_ingestion_progress(playlist_id: int) -> dict | None:
    """
    Get live ingestion progress for a playlist.

    Returns:
        Dict with current_video, current_video_title, videos_processed,
        videos_failed — or None if no ingestion is running.
    """
    return _ingestion_progress.get(playlist_id)


def _update_progress(
    playlist_id: int,
    *,
    current_video: int | None = None,
    current_video_title: str | None = None,
    videos_processed: int = 0,
    videos_failed: int = 0,
    total_videos: int = 0,
) -> None:
    """Update the live progress dict for a playlist."""
    _ingestion_progress[playlist_id] = {
        "current_video": current_video,
        "current_video_title": current_video_title,
        "videos_processed": videos_processed,
        "videos_failed": videos_failed,
        "total_videos": total_videos,
    }


def _clear_progress(playlist_id: int) -> None:
    """Remove progress tracking after ingestion completes."""
    _ingestion_progress.pop(playlist_id, None)


async def run_ingestion(db: AsyncSession, playlist_id: int) -> dict:
    """
    Run the full ingestion pipeline for a playlist.

    Uses a temporary ChromaDB collection during processing:
    - On success: swaps temp → live (old data replaced)
    - On failure: deletes temp, old live data preserved

    Updates playlist and video statuses as processing progresses.
    Includes rate-limit protection: delays between videos and a circuit
    breaker that triggers a 60s cooldown after 3 consecutive failures.

    Args:
        db: Database session
        playlist_id: ID of the playlist to process

    Returns:
        Dict with processing stats:
        - videos_processed, videos_failed, total_chunks, elapsed_seconds
    """
    start_time = time.time()

    logger.info(f"{'='*60}")
    logger.info(f"INGESTION PIPELINE START -- playlist_id={playlist_id}")
    logger.info(f"{'='*60}")
    await crud.update_playlist_status(db, playlist_id, "processing")

    stats = {
        "videos_processed": 0,
        "videos_failed": 0,
        "total_chunks": 0,
        "elapsed_seconds": 0,
        "errors": [],
    }

    consecutive_failures = 0  # Track consecutive transcript-fetch failures

    # Create temp collection for safe ingestion
    try:
        temp_collection = await asyncio.to_thread(create_temp_collection, playlist_id)
    except Exception as e:
        logger.error(f"Failed to create temp collection: {e}", exc_info=True)
        await crud.update_playlist_status(db, playlist_id, "error", str(e))
        return stats

    try:
        # Get all videos for this playlist
        videos = await crud.get_playlist_videos(db, playlist_id)

        if not videos:
            await crud.update_playlist_status(db, playlist_id, "error", "No videos found")
            await asyncio.to_thread(cleanup_temp_collection, playlist_id)
            return stats

        _update_progress(
            playlist_id,
            total_videos=len(videos),
        )

        # Process each video
        for i, video in enumerate(videos):
            try:
                logger.info(f"Processing video {video.position + 1}/{len(videos)}: {video.title}")
                await crud.update_video(db, video.id, status="processing")

                _update_progress(
                    playlist_id,
                    current_video=i + 1,
                    current_video_title=video.title,
                    videos_processed=stats["videos_processed"],
                    videos_failed=stats["videos_failed"],
                    total_videos=len(videos),
                )

                # ── Rate-limit: inter-video delay ──────────────────────
                if i > 0:
                    logger.debug(f"Waiting {INTER_VIDEO_DELAY_SECONDS}s before next video...")
                    await asyncio.sleep(INTER_VIDEO_DELAY_SECONDS)

                # ── Rate-limit: circuit breaker cooldown ───────────────
                if consecutive_failures >= CONSECUTIVE_FAIL_THRESHOLD:
                    logger.warning(
                        f"Circuit breaker: {consecutive_failures} consecutive failures. "
                        f"Cooling down for {RATE_LIMIT_COOLDOWN_SECONDS}s..."
                    )
                    await asyncio.sleep(RATE_LIMIT_COOLDOWN_SECONDS)
                    consecutive_failures = 0  # Reset after cooldown

                # Step 1: Download audio + transcribe with Whisper
                raw_transcript = await asyncio.to_thread(
                    transcribe_video, video.video_id
                )

                if not raw_transcript:
                    consecutive_failures += 1
                    logger.warning(
                        f"  [!] Transcription failed for video {video.video_id} "
                        f"('{video.title}') [consecutive failures: {consecutive_failures}]"
                    )
                    await crud.update_video(
                        db, video.id,
                        status="no_transcript",
                        error_message="Whisper transcription failed"
                    )
                    stats["videos_failed"] += 1
                    stats["errors"].append(f"Transcription failed: {video.title}")
                    continue

                # Success — reset consecutive failure counter
                consecutive_failures = 0
                logger.info(f"  [OK] Transcript fetched: {len(raw_transcript)} segments")

                # Step 2: Process transcript (clean + merge)
                processed = process_transcript(raw_transcript)

                if not processed["full_text"]:
                    logger.warning(f"  [!] Transcript processing produced empty result for {video.video_id}")
                    await crud.update_video(
                        db, video.id,
                        status="error",
                        error_message="Transcript processing produced empty result"
                    )
                    stats["videos_failed"] += 1
                    continue

                logger.info(
                    f"  [OK] Transcript processed: {len(processed['full_text'])} chars, "
                    f"{len(processed['segments'])} merged segments"
                )

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
                    logger.info(f"  [OK] No chunks produced (short transcript), marking ready")
                    await crud.update_video(db, video.id, status="ready")
                    stats["videos_processed"] += 1
                    continue

                logger.info(f"  [OK] Chunked into {len(chunks_with_ts)} chunks")

                # Step 4: Generate embeddings
                chunk_texts = [c["text"] for c in chunks_with_ts]
                embeddings = await asyncio.to_thread(
                    embed_texts, chunk_texts, 64, False
                )

                # Step 5: Prepare metadata and upsert to TEMP ChromaDB collection
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

                # Upsert to TEMP collection (not the live one)
                num_upserted = await asyncio.to_thread(
                    upsert_chunks,
                    playlist_id,
                    chunk_texts,
                    embeddings,
                    metadatas,
                    temp_collection,
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
                logger.error(
                    f"  [FAIL] Error processing video {video.video_id} ('{video.title}'): "
                    f"{type(e).__name__}: {e}",
                    exc_info=True,
                )
                await crud.update_video(
                    db, video.id,
                    status="error",
                    error_message=str(e)
                )
                stats["videos_failed"] += 1
                stats["errors"].append(f"{video.title}: {str(e)}")

        # ── Collection swap decision ───────────────────────────────
        if stats["videos_processed"] > 0:
            # Success — swap temp → live
            try:
                await asyncio.to_thread(swap_collection, playlist_id)
                logger.info(f"Collection swap successful for playlist {playlist_id}")
            except Exception as e:
                logger.error(f"Collection swap failed: {e}", exc_info=True)
                # Data is in temp but swap failed — don't mark as error,
                # the temp data is still there for manual recovery
            await crud.update_playlist_status(db, playlist_id, "ready")
        else:
            # No videos processed — clean up temp, keep old data
            await asyncio.to_thread(cleanup_temp_collection, playlist_id)
            await crud.update_playlist_status(
                db, playlist_id, "error",
                "No videos could be processed"
            )

    except Exception as e:
        logger.error(
            f"Pipeline CRITICAL error for playlist {playlist_id}: "
            f"{type(e).__name__}: {e}",
            exc_info=True,
        )
        # Clean up temp on critical failure
        try:
            await asyncio.to_thread(cleanup_temp_collection, playlist_id)
        except Exception:
            pass
        await crud.update_playlist_status(db, playlist_id, "error", str(e))
        stats["errors"].append(str(e))

    stats["elapsed_seconds"] = round(time.time() - start_time, 2)
    _clear_progress(playlist_id)

    logger.info(f"{'='*60}")
    logger.info(
        f"INGESTION PIPELINE COMPLETE -- playlist {playlist_id}: "
        f"{stats['videos_processed']} processed, {stats['videos_failed']} failed, "
        f"{stats['total_chunks']} chunks, {stats['elapsed_seconds']}s"
    )
    if stats["errors"]:
        logger.warning(f"  Errors encountered: {stats['errors']}")
    logger.info(f"{'='*60}")

    return stats


async def run_ingestion_retry(db: AsyncSession, playlist_id: int) -> dict:
    """
    Retry ingestion for failed videos only.

    Only processes videos with status 'error', 'no_transcript', or 'pending'.
    Does NOT clear existing vector data — preserves already-processed videos.
    Upserts directly to the live collection (no temp swap needed since
    we're only adding, not replacing).

    Args:
        db: Database session
        playlist_id: ID of the playlist to retry

    Returns:
        Dict with processing stats
    """
    start_time = time.time()

    logger.info(f"{'='*60}")
    logger.info(f"INGESTION RETRY START -- playlist_id={playlist_id}")
    logger.info(f"{'='*60}")

    stats = {
        "videos_processed": 0,
        "videos_failed": 0,
        "total_chunks": 0,
        "elapsed_seconds": 0,
        "errors": [],
    }

    consecutive_failures = 0

    try:
        all_videos = await crud.get_playlist_videos(db, playlist_id)
        retryable = [v for v in all_videos if v.status in ("error", "no_transcript", "pending")]

        if not retryable:
            logger.info("No videos to retry")
            await crud.update_playlist_status(db, playlist_id, "ready")
            return stats

        logger.info(f"Retrying {len(retryable)}/{len(all_videos)} videos")

        _update_progress(
            playlist_id,
            total_videos=len(retryable),
        )

        for i, video in enumerate(retryable):
            try:
                logger.info(f"Retrying video {i + 1}/{len(retryable)}: {video.title}")
                await crud.update_video(db, video.id, status="processing")

                _update_progress(
                    playlist_id,
                    current_video=i + 1,
                    current_video_title=video.title,
                    videos_processed=stats["videos_processed"],
                    videos_failed=stats["videos_failed"],
                    total_videos=len(retryable),
                )

                # Rate-limit: inter-video delay
                if i > 0:
                    logger.debug(f"Waiting {INTER_VIDEO_DELAY_SECONDS}s before next video...")
                    await asyncio.sleep(INTER_VIDEO_DELAY_SECONDS)

                # Rate-limit: circuit breaker cooldown
                if consecutive_failures >= CONSECUTIVE_FAIL_THRESHOLD:
                    logger.warning(
                        f"Circuit breaker: {consecutive_failures} consecutive failures. "
                        f"Cooling down for {RATE_LIMIT_COOLDOWN_SECONDS}s..."
                    )
                    await asyncio.sleep(RATE_LIMIT_COOLDOWN_SECONDS)
                    consecutive_failures = 0

                # Step 1: Download audio + transcribe with Whisper
                raw_transcript = await asyncio.to_thread(
                    transcribe_video, video.video_id
                )

                if not raw_transcript:
                    consecutive_failures += 1
                    logger.warning(
                        f"  [!] Still no transcript for {video.video_id} "
                        f"('{video.title}') [consecutive failures: {consecutive_failures}]"
                    )
                    await crud.update_video(
                        db, video.id,
                        status="no_transcript",
                        error_message="Whisper transcription failed (retry)"
                    )
                    stats["videos_failed"] += 1
                    stats["errors"].append(f"Transcription failed: {video.title}")
                    continue

                consecutive_failures = 0
                logger.info(f"  [OK] Transcript fetched: {len(raw_transcript)} segments")

                # Step 2: Process transcript
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

                # Step 3: Chunk transcript
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

                # Step 5: Upsert to live collection (retry adds, doesn't replace)
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
                        "embedding_id": "",
                        "timestamp_start": chunk_data["timestamp_start"],
                        "timestamp_end": chunk_data["timestamp_end"],
                    })

                num_upserted = await asyncio.to_thread(
                    upsert_chunks,
                    playlist_id,
                    chunk_texts,
                    embeddings,
                    metadatas,
                )

                await crud.create_chunks_batch(db, chunk_db_records)
                await crud.update_video(db, video.id, status="ready")

                stats["videos_processed"] += 1
                stats["total_chunks"] += num_upserted

                logger.info(f"Video '{video.title}' retry succeeded: {num_upserted} chunks")

            except Exception as e:
                logger.error(
                    f"  [FAIL] Retry error for {video.video_id} ('{video.title}'): "
                    f"{type(e).__name__}: {e}",
                    exc_info=True,
                )
                await crud.update_video(
                    db, video.id,
                    status="error",
                    error_message=str(e)
                )
                stats["videos_failed"] += 1
                stats["errors"].append(f"{video.title}: {str(e)}")

        # Check overall status: if any video is ready, mark playlist ready
        all_videos_now = await crud.get_playlist_videos(db, playlist_id)
        ready_count = sum(1 for v in all_videos_now if v.status == "ready")

        if ready_count > 0:
            await crud.update_playlist_status(db, playlist_id, "ready")
        else:
            await crud.update_playlist_status(
                db, playlist_id, "error",
                "No videos could be processed after retry"
            )

    except Exception as e:
        logger.error(
            f"Retry CRITICAL error for playlist {playlist_id}: "
            f"{type(e).__name__}: {e}",
            exc_info=True,
        )
        await crud.update_playlist_status(db, playlist_id, "error", str(e))
        stats["errors"].append(str(e))

    stats["elapsed_seconds"] = round(time.time() - start_time, 2)
    _clear_progress(playlist_id)

    logger.info(f"{'='*60}")
    logger.info(
        f"INGESTION RETRY COMPLETE -- playlist {playlist_id}: "
        f"{stats['videos_processed']} processed, {stats['videos_failed']} failed, "
        f"{stats['total_chunks']} chunks, {stats['elapsed_seconds']}s"
    )
    if stats["errors"]:
        logger.warning(f"  Errors encountered: {stats['errors']}")
    logger.info(f"{'='*60}")

    return stats
