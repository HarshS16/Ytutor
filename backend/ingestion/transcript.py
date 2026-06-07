"""
Whisper-based transcript extraction and cleaning pipeline.

Downloads audio via yt-dlp, then transcribes locally using OpenAI Whisper.
Replaces the old youtube-transcript-api / yt-dlp caption fetching approach
to eliminate YouTube transcript rate-limiting issues.

Pipeline:
1. Download audio (yt-dlp + FFmpeg)
2. Transcribe with Whisper (local, no API)
3. Clean transcript segments
4. Merge short fragments into sentences
5. Preserve timestamp mapping for chunking

Performance metrics are logged for each transcription.
"""

import logging
import os
import re
import time
from functools import lru_cache
from typing import Optional

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# ── Whisper configuration ─────────────────────────────────────────
WHISPER_MODEL_NAME = os.getenv("WHISPER_MODEL", "base")

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


# ── Whisper model singleton ──────────────────────────────────────

@lru_cache(maxsize=1)
def get_whisper_model():
    """
    Load and cache the Whisper model (singleton).

    Model is loaded once and reused for all transcriptions.
    Uses the WHISPER_MODEL env var (default: 'base').
    """
    import whisper

    logger.info(f"Loading Whisper model: '{WHISPER_MODEL_NAME}'...")
    start = time.time()
    model = whisper.load_model(WHISPER_MODEL_NAME)
    elapsed = time.time() - start
    logger.info(f"Whisper model '{WHISPER_MODEL_NAME}' loaded in {elapsed:.1f}s")
    return model


# ── Core transcription ───────────────────────────────────────────

def transcribe_video(video_id: str) -> Optional[list[dict]]:
    """
    Download audio and transcribe a YouTube video using Whisper.

    Downloads audio via yt-dlp (with cache), runs Whisper locally,
    and returns transcript segments in the same format as the old
    youtube-transcript-api: [{text, start, duration}, ...]

    Logs detailed performance metrics after each transcription.

    Args:
        video_id: YouTube video ID (e.g., "dQw4w9WgXcQ")

    Returns:
        List of dicts: {text, start, duration}
        Or None if transcription fails.
    """
    from ingestion.audio_downloader import download_audio, cleanup_audio

    # Step 1: Download audio
    try:
        audio_path = download_audio(video_id)
    except RuntimeError as e:
        logger.error(f"Audio download failed for {video_id}: {e}")
        return None

    # Step 2: Transcribe with Whisper
    try:
        model = get_whisper_model()

        logger.info(f"Transcribing {video_id} with Whisper ({WHISPER_MODEL_NAME})...")
        transcribe_start = time.time()

        result = model.transcribe(
            audio_path,
            language=None,  # Auto-detect language
            verbose=False,
        )

        transcribe_elapsed = time.time() - transcribe_start

        # Extract segments in the standard format
        segments = []
        for seg in result.get("segments", []):
            text = seg.get("text", "").strip()
            if not text:
                continue
            segments.append({
                "text": text,
                "start": seg.get("start", 0.0),
                "duration": seg.get("end", 0.0) - seg.get("start", 0.0),
            })

        # Log performance metrics
        full_text = result.get("text", "")
        detected_lang = result.get("language", "unknown")

        # Estimate audio duration from last segment
        audio_duration = 0.0
        if segments:
            last = segments[-1]
            audio_duration = last["start"] + last["duration"]

        _log_whisper_metrics(
            video_id=video_id,
            audio_duration=audio_duration,
            transcribe_time=transcribe_elapsed,
            model_name=WHISPER_MODEL_NAME,
            transcript_length=len(full_text),
            segment_count=len(segments),
            detected_language=detected_lang,
        )

        if not segments:
            logger.warning(f"Whisper produced no segments for {video_id}")
            return None

        # Step 3: Clean up audio cache after successful transcription
        try:
            cleanup_audio(video_id)
        except Exception as e:
            logger.warning(f"Audio cleanup failed for {video_id}: {e}")

        return segments

    except Exception as e:
        logger.error(
            f"Whisper transcription failed for {video_id}: "
            f"{type(e).__name__}: {e}",
            exc_info=True,
        )
        return None


def _log_whisper_metrics(
    video_id: str,
    audio_duration: float,
    transcribe_time: float,
    model_name: str,
    transcript_length: int,
    segment_count: int,
    detected_language: str,
) -> None:
    """Log detailed Whisper performance metrics."""
    audio_mins = int(audio_duration // 60)
    audio_secs = int(audio_duration % 60)
    speed_ratio = audio_duration / transcribe_time if transcribe_time > 0 else 0

    logger.info(
        f"┌─ Whisper Metrics: {video_id} ────────────────────\n"
        f"│  Audio Duration  : {audio_mins}m {audio_secs}s\n"
        f"│  Whisper Model   : {model_name}\n"
        f"│  Transcription   : {transcribe_time:.1f}s ({speed_ratio:.1f}x realtime)\n"
        f"│  Transcript Size : {transcript_length:,} chars, {segment_count} segments\n"
        f"│  Language        : {detected_language}\n"
        f"└──────────────────────────────────────────────────"
    )


# ── Transcript cleaning (unchanged from original) ────────────────

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
        raw_segments: List of {text, start, duration} dicts from Whisper

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
