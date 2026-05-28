"""
YouTube transcript extraction and cleaning pipeline.

Fetches subtitles via youtube-transcript-api, then cleans them:
- Removes [Music]/[Applause] markers
- Merges broken sentence fragments
- Removes filler words
- Preserves timestamp mapping
"""

import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)

# Filler words/phrases to remove
FILLER_PATTERNS = [
    r"\b(um|uh|hmm|hm|ah|oh|er|erm)\b",
    r"\b(you know|i mean|like,?\s*you know|basically|actually|literally)\b",
]

# Markers to strip entirely
MARKER_PATTERN = re.compile(
    r"\[(?:Music|Applause|Laughter|Cheering|Silence|Inaudible)\]",
    re.IGNORECASE,
)


def fetch_transcript(video_id: str, languages: list[str] = None) -> Optional[list[dict]]:
    """
    Fetch transcript for a YouTube video.

    Tries manual captions first, then auto-generated.

    Args:
        video_id: YouTube video ID (e.g., "dQw4w9WgXcQ")
        languages: Preferred languages (default: ["en"])

    Returns:
        List of dicts: {text, start, duration}
        Or None if no transcript available.
    """
    from youtube_transcript_api import YouTubeTranscriptApi

    if languages is None:
        languages = ["en"]

    try:
        # Try fetching transcript — the library auto-handles manual vs auto-generated
        transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=languages)
        logger.info(f"Fetched transcript for {video_id}: {len(transcript)} segments")
        return transcript

    except Exception as e:
        logger.warning(f"No transcript for {video_id}: {e}")
        return None


def clean_transcript_text(text: str) -> str:
    """
    Clean a single transcript text segment.

    - Remove [Music] etc. markers
    - Remove filler words
    - Clean extra whitespace
    """
    # Remove markers
    text = MARKER_PATTERN.sub("", text)

    # Remove filler words (case-insensitive)
    for pattern in FILLER_PATTERNS:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE)

    # Clean whitespace
    text = re.sub(r"\s+", " ", text).strip()

    return text


def process_transcript(raw_segments: list[dict]) -> dict:
    """
    Process raw transcript segments into clean, merged text with timestamps.

    Steps:
    1. Clean each segment
    2. Merge short fragments into complete sentences
    3. Build a full transcript text
    4. Maintain a timestamp map for chunks

    Args:
        raw_segments: List of {text, start, duration} dicts from youtube-transcript-api

    Returns:
        Dict with:
        - full_text: The complete cleaned transcript
        - segments: List of {text, start, end} with cleaned, merged segments
        - duration: Total video duration in seconds
    """
    if not raw_segments:
        return {"full_text": "", "segments": [], "duration": 0}

    # Step 1: Clean each segment
    cleaned_segments = []
    for seg in raw_segments:
        cleaned_text = clean_transcript_text(seg.get("text", ""))
        if cleaned_text:
            cleaned_segments.append({
                "text": cleaned_text,
                "start": seg.get("start", 0),
                "duration": seg.get("duration", 0),
                "end": seg.get("start", 0) + seg.get("duration", 0),
            })

    if not cleaned_segments:
        return {"full_text": "", "segments": [], "duration": 0}

    # Step 2: Merge short fragments (< 5 words) with their neighbors
    merged_segments = []
    buffer_text = ""
    buffer_start = cleaned_segments[0]["start"]
    buffer_end = 0

    for seg in cleaned_segments:
        buffer_text += (" " if buffer_text else "") + seg["text"]
        buffer_end = seg["end"]

        # Flush buffer when we have a reasonable sentence length
        word_count = len(buffer_text.split())
        ends_with_punct = buffer_text.rstrip()[-1] in ".!?:;" if buffer_text.rstrip() else False

        if word_count >= 10 or ends_with_punct:
            merged_segments.append({
                "text": buffer_text.strip(),
                "start": buffer_start,
                "end": buffer_end,
            })
            buffer_text = ""
            buffer_start = buffer_end

    # Don't forget the remaining buffer
    if buffer_text.strip():
        merged_segments.append({
            "text": buffer_text.strip(),
            "start": buffer_start,
            "end": buffer_end,
        })

    # Step 3: Build full text
    full_text = " ".join(seg["text"] for seg in merged_segments)

    # Fix capitalization at sentence boundaries
    full_text = re.sub(r"(?<=\. )([a-z])", lambda m: m.group(1).upper(), full_text)
    if full_text:
        full_text = full_text[0].upper() + full_text[1:]

    total_duration = max(seg["end"] for seg in merged_segments) if merged_segments else 0

    logger.info(
        f"Processed transcript: {len(merged_segments)} segments, "
        f"{len(full_text)} chars, {total_duration:.0f}s duration"
    )

    return {
        "full_text": full_text,
        "segments": merged_segments,
        "duration": total_duration,
    }


def format_timestamp(seconds: float) -> str:
    """Convert seconds to HH:MM:SS or MM:SS format."""
    seconds = int(seconds)
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60

    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"
