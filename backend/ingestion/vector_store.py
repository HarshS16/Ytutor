"""
ChromaDB vector store interface for Ytutor AI.

Each playlist gets its own ChromaDB collection (playlist_{id}).
Supports ingestion (upsert) and retrieval (query) with video metadata.

Optimized with cached client and collection objects to avoid
repeated disk reads on every query.
"""

import hashlib
import logging
import os
import threading
from datetime import datetime, timezone

import chromadb
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# ── Configuration ──────────────────────────────────────────────────
CHROMA_DB_PATH = os.getenv("CHROMA_DB_PATH", os.path.join(os.path.dirname(__file__), "..", "chroma_db"))

# ── Cached client and collections ──────────────────────────────────
_client: chromadb.PersistentClient = None
_client_lock = threading.Lock()
_collection_cache: dict[str, object] = {}
_collection_lock = threading.Lock()


def get_client() -> chromadb.PersistentClient:
    """Get a persistent ChromaDB client (singleton, cached)."""
    global _client
    if _client is not None:
        return _client

    with _client_lock:
        # Double-check after acquiring lock
        if _client is not None:
            return _client
        abs_path = os.path.abspath(CHROMA_DB_PATH)
        os.makedirs(abs_path, exist_ok=True)
        logger.info(f"ChromaDB client initialized: {abs_path}")
        _client = chromadb.PersistentClient(path=abs_path)
        return _client


def get_collection(playlist_id: int, client: chromadb.PersistentClient = None):
    """
    Get or create a collection for a specific playlist.

    Collections are cached in memory after first access, so repeated
    queries to the same playlist avoid disk reads.
    """
    collection_name = f"playlist_{playlist_id}"

    # Check cache first (fast path, no lock)
    cached = _collection_cache.get(collection_name)
    if cached is not None:
        return cached

    with _collection_lock:
        # Double-check after acquiring lock
        cached = _collection_cache.get(collection_name)
        if cached is not None:
            return cached

        if client is None:
            client = get_client()

        collection = client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )
        logger.info(f"Collection '{collection_name}' loaded — {collection.count()} documents")
        _collection_cache[collection_name] = collection
        return collection


def _invalidate_collection_cache(collection_name: str):
    """Remove a collection from the cache (e.g. after clearing it)."""
    with _collection_lock:
        _collection_cache.pop(collection_name, None)


def generate_chunk_id(video_id: str, chunk_index: int) -> str:
    """Generate a deterministic ID for a chunk (for deduplication)."""
    raw = f"{video_id}::chunk_{chunk_index}"
    return hashlib.md5(raw.encode()).hexdigest()


def upsert_chunks(
    playlist_id: int,
    chunks: list[str],
    embeddings: list[list[float]],
    metadatas: list[dict],
    collection=None,
) -> int:
    """
    Upsert chunks with embeddings and metadata into ChromaDB.

    Args:
        playlist_id: ID of the playlist (determines collection)
        chunks: List of text chunk strings
        embeddings: List of embedding vectors
        metadatas: List of metadata dicts (video_id, video_title, timestamp_start, etc.)
        collection: ChromaDB collection (auto-created if None)

    Returns:
        Number of chunks upserted
    """
    if collection is None:
        collection = get_collection(playlist_id)

    if not chunks:
        logger.warning("No chunks to upsert")
        return 0

    # Generate deterministic IDs
    ids = [
        generate_chunk_id(meta["video_id"], meta["chunk_index"])
        for meta in metadatas
    ]

    # Upsert in batches (ChromaDB batch limit)
    batch_size = 100
    total_upserted = 0

    for i in range(0, len(chunks), batch_size):
        batch_end = min(i + batch_size, len(chunks))

        collection.upsert(
            ids=ids[i:batch_end],
            documents=chunks[i:batch_end],
            embeddings=embeddings[i:batch_end],
            metadatas=metadatas[i:batch_end],
        )

        total_upserted += batch_end - i
        logger.info(f"  Upserted batch {i // batch_size + 1}: {batch_end - i} chunks")

    logger.info(f"Total upserted: {total_upserted} chunks. Collection has {collection.count()} documents.")
    return total_upserted


def query_similar(
    playlist_id: int,
    query_embedding: list[float],
    n_results: int = 8,
    distance_threshold: float = 0.65,
    collection=None,
) -> list[dict]:
    """
    Query the vector store for similar chunks within a playlist.

    Args:
        playlist_id: ID of the playlist to search
        query_embedding: Query embedding vector
        n_results: Number of results to return
        distance_threshold: Maximum distance (lower = more similar)
        collection: ChromaDB collection

    Returns:
        List of dicts: {text, video_id, video_title, score, chunk_index,
                        timestamp_start, timestamp_end}
    """
    if collection is None:
        collection = get_collection(playlist_id)

    if collection.count() == 0:
        logger.warning("Collection is empty — no results")
        return []

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results,
        include=["documents", "metadatas", "distances"],
    )

    matches = []

    if results and results["documents"] and results["documents"][0]:
        for doc, meta, dist in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        ):
            if dist <= distance_threshold:
                similarity = 1 - dist
                matches.append({
                    "text": doc,
                    "video_id": meta.get("video_id", ""),
                    "video_title": meta.get("video_title", ""),
                    "score": round(similarity, 4),
                    "chunk_index": meta.get("chunk_index", 0),
                    "timestamp_start": meta.get("timestamp_start", 0),
                    "timestamp_end": meta.get("timestamp_end", 0),
                    "distance": round(dist, 4),
                })

    logger.info(f"Query returned {len(matches)} results above threshold")
    return matches


def get_collection_stats(playlist_id: int) -> dict:
    """Get stats about a playlist's ChromaDB collection."""
    try:
        collection = get_collection(playlist_id)
        return {
            "collection_name": f"playlist_{playlist_id}",
            "total_chunks": collection.count(),
            "db_path": os.path.abspath(CHROMA_DB_PATH),
        }
    except Exception as e:
        logger.error(f"Error getting collection stats: {e}")
        return {
            "collection_name": f"playlist_{playlist_id}",
            "total_chunks": 0,
            "error": str(e),
        }


def clear_collection(playlist_id: int) -> None:
    """Clear all data for a playlist collection."""
    client = get_client()
    collection_name = f"playlist_{playlist_id}"

    # Invalidate cache first
    _invalidate_collection_cache(collection_name)

    try:
        client.delete_collection(collection_name)
        logger.info(f"Deleted collection '{collection_name}'")
    except Exception:
        logger.info(f"Collection '{collection_name}' doesn't exist")

    # Re-create and cache
    collection = get_collection(playlist_id, client)
    logger.info(f"Recreated empty collection '{collection_name}'")
