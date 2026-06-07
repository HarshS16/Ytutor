"""
Retriever service — handles query embedding and vector search.

Encodes the user query and searches the playlist's ChromaDB collection
for semantically similar transcript chunks.

Fallback: if ChromaDB returns 0 results (empty collection), pulls
transcript text directly from the SQLite database so chat always
has context as long as transcripts have been ingested.
"""

import asyncio
import logging
import os
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

from ingestion.embedder import embed_query
from ingestion.vector_store import query_similar, get_collection_stats

# ── Configuration ──────────────────────────────────────────────────
TOP_K = int(os.getenv("TOP_K", 8))
SIMILARITY_THRESHOLD = float(os.getenv("SIMILARITY_THRESHOLD", 0.35))
DISTANCE_THRESHOLD = 1 - SIMILARITY_THRESHOLD

# Max chars per video to include in the DB fallback context
_FALLBACK_MAX_CHARS_PER_VIDEO = 2000
_FALLBACK_MAX_VIDEOS = 6


def retrieve(playlist_id: int, query: str, top_k: int = TOP_K) -> list[dict]:
    """
    Retrieve the most relevant transcript chunks for a query within a playlist.

    1. Try ChromaDB vector search first.
    2. If the collection is empty, fall back to raw transcript text from the DB.

    Args:
        playlist_id: ID of the playlist to search
        query: User's question
        top_k: Number of results to retrieve

    Returns:
        List of dicts: {text, video_id, video_title, score, chunk_index,
                        timestamp_start, timestamp_end}
    """
    logger.info(f"Retrieving for playlist {playlist_id}: '{query[:80]}...'")

    # Step 1: Embed the query
    query_embedding = embed_query(query)

    # Step 2: Search ChromaDB
    results = query_similar(
        playlist_id=playlist_id,
        query_embedding=query_embedding,
        n_results=top_k,
        distance_threshold=DISTANCE_THRESHOLD,
    )

    if results:
        logger.info(f"Found {len(results)} relevant chunks:")
        for r in results:
            logger.info(
                f"  Score: {r['score']:.4f} | {r['video_title'][:40]}"
            )
        return results

    # Step 3: Fallback — pull transcripts from the DB
    logger.info("No vector results — trying DB transcript fallback")
    fallback = _fallback_from_db(playlist_id)
    if fallback:
        logger.info(f"DB fallback returned {len(fallback)} transcript chunks")
    else:
        logger.info("No transcripts found in DB either")

    return fallback


def _fallback_from_db(playlist_id: int) -> list[dict]:
    """
    Pull transcript text directly from the database for videos in a playlist.

    This is the safety net: if ChromaDB has no data (ingestion partially
    failed, collection was wiped, etc.) but transcript_text was saved to
    SQLite, we use that raw text as chat context.

    Returns a list of pseudo-chunks in the same format as vector results.
    """
    import asyncio
    from db.database import async_session
    from db import crud

    async def _fetch():
        async with async_session() as db:
            videos = await crud.get_playlist_videos(db, playlist_id)
            return [
                {"video_id": v.video_id, "title": v.title, "transcript": v.transcript_text}
                for v in videos
                if v.transcript_text and v.status == "ready"
            ]

    # Run async DB query from sync context
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        # We're inside an async context — use a new thread
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as pool:
            videos_data = pool.submit(asyncio.run, _fetch()).result()
    else:
        videos_data = asyncio.run(_fetch())

    if not videos_data:
        return []

    # Build pseudo-chunks from transcript text
    chunks = []
    for v in videos_data[:_FALLBACK_MAX_VIDEOS]:
        text = v["transcript"][:_FALLBACK_MAX_CHARS_PER_VIDEO]
        chunks.append({
            "text": text,
            "video_id": v["video_id"],
            "video_title": v["title"],
            "score": 0.5,  # Synthetic score — not from vector search
            "chunk_index": 0,
            "timestamp_start": 0,
            "timestamp_end": 0,
            "distance": 0.5,
        })

    return chunks
