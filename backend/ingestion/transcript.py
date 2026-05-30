"""
YouTube transcript extraction and cleaning pipeline.

Fetches subtitles via youtube-transcript-api, then cleans them:
- Removes [Music]/[Applause] markers
- Merges broken sentence fragments
- Removes filler words
- Preserves timestamp mapping

Rate-limit handling:
- Exponential backoff with jitter on HTTP 429
- Early-exit on rate-limit in yt-dlp fallback
- Max 3 language attempts in fallback
"""

import logging
import random
import re
import time
from typing import Optional

logger = logging.getLogger(__name__)

# ── Rate-limit configuration ──────────────────────────────────────
MAX_RETRIES = 3                # Number of retries on 429
INITIAL_BACKOFF_SECONDS = 5    # First retry waits 5s
MAX_BACKOFF_SECONDS = 60       # Cap backoff at 60s
MAX_FALLBACK_LANGUAGES = 3    # Max languages to try in yt-dlp fallback

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


def _is_rate_limited(exc: Exception) -> bool:
    """Check if an exception is a 429 rate-limit error."""
    err_str = str(exc)
    return "429" in err_str or "Too Many Requests" in err_str


def _backoff_sleep(attempt: int) -> None:
    """Sleep with exponential backoff + jitter."""
    base = min(INITIAL_BACKOFF_SECONDS * (2 ** attempt), MAX_BACKOFF_SECONDS)
    jitter = random.uniform(0, base * 0.5)
    wait = base + jitter
    logger.info(f"Rate-limited — backing off {wait:.1f}s (attempt {attempt + 1}/{MAX_RETRIES})")
    time.sleep(wait)


def fetch_transcript_ytdlp(video_id: str) -> Optional[list[dict]]:
    import yt_dlp
    import requests
    
    ydl_opts = {'quiet': True, 'skip_download': True}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=False)
        except Exception as e:
            logger.warning(f"yt-dlp extract_info failed for {video_id}: {type(e).__name__}: {e}", exc_info=True)
            return None
            
    caps = info.get('subtitles', {})
    if not caps:
        caps = info.get('automatic_captions', {})
        
    if not caps:
        return None
        
    # Try preferred languages first, then any available — but cap at MAX_FALLBACK_LANGUAGES
    langs_to_try = []
    for l in ['en', 'hi'] + list(caps.keys()):
        if l in caps and l not in langs_to_try:
            langs_to_try.append(l)
            if len(langs_to_try) >= MAX_FALLBACK_LANGUAGES:
                break
            
    for lang in langs_to_try:
        url = next((c['url'] for c in caps[lang] if c.get('ext') == 'json3'), None)
        if not url:
            continue
            
        try:
            resp = requests.get(url)
            resp.raise_for_status()
            data = resp.json()
            segments = []
            for ev in data.get('events', []):
                if 'segs' not in ev:
                    continue
                text = "".join(s.get('utf8', '') for s in ev['segs']).strip()
                if not text:
                    continue
                segments.append({
                    'text': text,
                    'start': ev['tStartMs'] / 1000.0,
                    'duration': ev.get('dDurationMs', 0) / 1000.0
                })
            
            if segments:
                return segments
        except Exception as e:
            if _is_rate_limited(e):
                # Stop trying more languages — all will fail with 429
                logger.warning(
                    f"yt-dlp fallback rate-limited for {video_id} (lang={lang}). "
                    f"Stopping further language attempts."
                )
                return None
            logger.warning(f"yt-dlp fallback request for {lang} failed: {type(e).__name__}: {e}", exc_info=True)
            continue
            
    return None

def fetch_transcript(video_id: str, languages: list[str] = None) -> Optional[list[dict]]:
    """
    Fetch transcript for a YouTube video with retry + backoff on rate limits.

    Tries manual captions first, then auto-generated.
    Falls back to any available language and translates if necessary.
    Uses yt-dlp as a bulletproof fallback if youtube-transcript-api is blocked.

    On HTTP 429 (Too Many Requests), retries up to MAX_RETRIES times with
    exponential backoff before falling back to yt-dlp.

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

    last_exception = None

    for attempt in range(MAX_RETRIES):
        try:
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
            
            try:
                t = transcript_list.find_transcript(languages)
            except Exception:
                t = next(iter(transcript_list))
                if languages and t.is_translatable:
                    try:
                        translated_t = t.translate(languages[0])
                        transcript = translated_t.fetch()
                        logger.info(f"Fetched translated transcript for {video_id} to {languages[0]}: {len(transcript)} segments")
                        return transcript
                    except Exception as trans_e:
                        if _is_rate_limited(trans_e):
                            last_exception = trans_e
                            _backoff_sleep(attempt)
                            continue
                        logger.warning(
                            f"Could not translate transcript for {video_id}: "
                            f"{type(trans_e).__name__}: {trans_e}",
                            exc_info=True,
                        )
                        
            transcript = t.fetch()
            logger.info(f"Fetched transcript for {video_id} (language: {t.language_code}): {len(transcript)} segments")
            return transcript

        except Exception as e:
            last_exception = e
            if _is_rate_limited(e):
                if attempt < MAX_RETRIES - 1:
                    _backoff_sleep(attempt)
                    continue
                else:
                    logger.warning(
                        f"youtube-transcript-api rate-limited for {video_id} after "
                        f"{MAX_RETRIES} attempts. Falling back to yt-dlp..."
                    )
            else:
                logger.warning(
                    f"youtube-transcript-api failed for {video_id}: {type(e).__name__}: {e}. "
                    f"Falling back to yt-dlp...",
                    exc_info=True,
                )
                break  # Non-rate-limit errors go straight to fallback

    # yt-dlp fallback
    fallback = fetch_transcript_ytdlp(video_id)
    if fallback:
        logger.info(f"Successfully fetched transcript for {video_id} using yt-dlp: {len(fallback)} segments")
        return fallback

    if last_exception and _is_rate_limited(last_exception):
        logger.error(
            f"All transcript methods rate-limited for {video_id}. "
            f"YouTube is throttling requests from this IP."
        )
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
