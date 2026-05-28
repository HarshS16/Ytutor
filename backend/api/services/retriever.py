"""
Retriever service — handles query embedding and vector search.

Encodes the user query and searches the playlist's ChromaDB collection
for semantically similar transcript chunks.
"""

import logging
import os
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

from ingestion.embedder import embed_query
from ingestion.vector_store import query_similar

# ── Configuration ──────────────────────────────────────────────────
TOP_K = int(os.getenv("TOP_K", 8))
SIMILARITY_THRESHOLD = float(os.getenv("SIMILARITY_THRESHOLD", 0.35))
DISTANCE_THRESHOLD = 1 - SIMILARITY_THRESHOLD


def retrieve(playlist_id: int, query: str, top_k: int = TOP_K) -> list[dict]:
    """
    Retrieve the most relevant transcript chunks for a query within a playlist.

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
    else:
        logger.info("No chunks found above similarity threshold")

    return results
