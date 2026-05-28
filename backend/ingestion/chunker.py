"""
Token-aware text chunker with overlapping windows and timestamp mapping.

Adapted from WebBee-Chatbot's chunker with enhancements:
- Preserves timestamp boundaries from transcript segments
- Maps each chunk to approximate video start/end times
"""

import logging
import os
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# ── Configuration ──────────────────────────────────────────────────
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", 500))        # target tokens per chunk
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", 50))   # overlap tokens
SEPARATORS = ["\n\n", "\n", ". ", ", ", " "]           # split preference order


def _estimate_tokens(text: str) -> int:
    """Rough token estimation. ~1 token per 4 characters for English."""
    return max(1, len(text) // 4)


def _split_by_separator(text: str, separator: str) -> list[str]:
    """Split text by separator, keeping the separator at the end of each chunk."""
    if separator == " ":
        return text.split(" ")

    parts = text.split(separator)
    result = []
    for i, part in enumerate(parts):
        if i < len(parts) - 1:
            result.append(part + separator)
        else:
            result.append(part)
    return [p for p in result if p.strip()]


def _recursive_split(text: str, separators: list[str], chunk_size: int) -> list[str]:
    """
    Recursively split text using a hierarchy of separators.

    Tries the first separator; if resulting chunks are still too large,
    recursively applies the next separator.
    """
    if _estimate_tokens(text) <= chunk_size:
        return [text]

    if not separators:
        char_limit = chunk_size * 4
        chunks = []
        while text:
            chunks.append(text[:char_limit])
            text = text[char_limit:]
        return chunks

    current_sep = separators[0]
    remaining_seps = separators[1:]

    parts = _split_by_separator(text, current_sep)

    chunks = []
    current_chunk = ""

    for part in parts:
        test_chunk = current_chunk + part if current_chunk else part

        if _estimate_tokens(test_chunk) <= chunk_size:
            current_chunk = test_chunk
        else:
            if current_chunk:
                chunks.append(current_chunk)

            if _estimate_tokens(part) > chunk_size:
                sub_chunks = _recursive_split(part, remaining_seps, chunk_size)
                chunks.extend(sub_chunks[:-1])
                current_chunk = sub_chunks[-1] if sub_chunks else ""
            else:
                current_chunk = part

    if current_chunk:
        chunks.append(current_chunk)

    return chunks


def chunk_text(
    text: str,
    chunk_size: int = CHUNK_SIZE,
    chunk_overlap: int = CHUNK_OVERLAP,
) -> list[str]:
    """
    Split text into overlapping chunks.

    Args:
        text: Input text to chunk
        chunk_size: Target tokens per chunk (default 500)
        chunk_overlap: Overlap tokens between consecutive chunks (default 50)

    Returns:
        List of text chunk strings
    """
    if not text or not text.strip():
        return []

    raw_chunks = _recursive_split(text.strip(), SEPARATORS, chunk_size)

    if len(raw_chunks) <= 1:
        return raw_chunks

    # Apply overlap
    overlap_chars = chunk_overlap * 4
    overlapped_chunks = [raw_chunks[0]]

    for i in range(1, len(raw_chunks)):
        prev_chunk = raw_chunks[i - 1]
        current_chunk = raw_chunks[i]

        overlap_text = prev_chunk[-overlap_chars:] if len(prev_chunk) > overlap_chars else prev_chunk

        space_idx = overlap_text.find(" ")
        if space_idx > 0:
            overlap_text = overlap_text[space_idx + 1:]

        merged = overlap_text + " " + current_chunk
        overlapped_chunks.append(merged.strip())

    # Filter out very small chunks (< 20 tokens)
    final_chunks = [c for c in overlapped_chunks if _estimate_tokens(c) >= 20]

    return final_chunks


def chunk_with_timestamps(
    text: str,
    segments: list[dict],
    chunk_size: int = CHUNK_SIZE,
    chunk_overlap: int = CHUNK_OVERLAP,
) -> list[dict]:
    """
    Chunk text and map each chunk to approximate start/end timestamps.

    Uses the transcript segments to approximate which part of the video
    each chunk corresponds to.

    Args:
        text: Full transcript text
        segments: List of {text, start, end} dicts from transcript processing
        chunk_size: Target tokens per chunk
        chunk_overlap: Overlap tokens

    Returns:
        List of dicts: {text, chunk_index, timestamp_start, timestamp_end}
    """
    chunks = chunk_text(text, chunk_size, chunk_overlap)

    if not chunks:
        return []

    if not segments:
        # No timestamps available — return chunks with 0 timestamps
        return [
            {
                "text": chunk,
                "chunk_index": idx,
                "timestamp_start": 0.0,
                "timestamp_end": 0.0,
            }
            for idx, chunk in enumerate(chunks)
        ]

    total_text_len = len(text)
    total_duration = max(seg["end"] for seg in segments) if segments else 0

    result = []
    search_start = 0

    for idx, chunk in enumerate(chunks):
        # Find chunk position in the full text
        chunk_pos = text.find(chunk[:50], search_start)
        if chunk_pos == -1:
            chunk_pos = search_start

        chunk_end_pos = chunk_pos + len(chunk)
        search_start = max(search_start, chunk_pos + len(chunk) // 2)

        # Map text position to timestamp (linear interpolation)
        if total_text_len > 0:
            ts_start = (chunk_pos / total_text_len) * total_duration
            ts_end = (chunk_end_pos / total_text_len) * total_duration
        else:
            ts_start = 0.0
            ts_end = 0.0

        result.append({
            "text": chunk,
            "chunk_index": idx,
            "timestamp_start": round(ts_start, 1),
            "timestamp_end": round(ts_end, 1),
        })

    logger.info(f"Created {len(result)} chunks with timestamps from {total_duration:.0f}s video")
    return result
