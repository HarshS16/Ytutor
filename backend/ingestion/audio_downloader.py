"""
Audio downloader for Ytutor — downloads YouTube audio via yt-dlp.

Downloads audio to a local cache directory so Whisper can transcribe it.
Checks cache first to avoid redundant downloads.

Prerequisites:
- FFmpeg must be installed and on PATH
- Node.js must be installed and on PATH (for yt-dlp JS extraction)
"""

import logging
import os
import shutil
import subprocess

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# ── Configuration ──────────────────────────────────────────────────
AUDIO_CACHE_DIR = os.getenv(
    "AUDIO_CACHE_DIR",
    os.path.join(os.path.dirname(__file__), "..", "cache", "audio"),
)


def check_prerequisites() -> dict[str, bool]:
    """
    Check that FFmpeg and Node.js are available on PATH.

    Returns:
        Dict with 'ffmpeg' and 'node' keys, True if found.
    """
    results = {}

    # Check FFmpeg
    ffmpeg_path = shutil.which("ffmpeg")
    if ffmpeg_path:
        try:
            out = subprocess.run(
                ["ffmpeg", "-version"],
                capture_output=True, text=True, timeout=10,
            )
            version_line = out.stdout.split("\n")[0] if out.stdout else "unknown"
            logger.info(f"FFmpeg found: {version_line}")
            results["ffmpeg"] = True
        except Exception as e:
            logger.warning(f"FFmpeg found at {ffmpeg_path} but failed to run: {e}")
            results["ffmpeg"] = False
    else:
        logger.warning(
            "FFmpeg NOT found on PATH. Audio download and Whisper transcription "
            "will fail. Install FFmpeg and add it to PATH."
        )
        results["ffmpeg"] = False

    # Check Node.js
    node_path = shutil.which("node")
    if node_path:
        try:
            out = subprocess.run(
                ["node", "-v"],
                capture_output=True, text=True, timeout=10,
            )
            version = out.stdout.strip() if out.stdout else "unknown"
            logger.info(f"Node.js found: {version}")
            results["node"] = True
        except Exception as e:
            logger.warning(f"Node.js found at {node_path} but failed to run: {e}")
            results["node"] = False
    else:
        logger.warning(
            "Node.js NOT found on PATH. yt-dlp may fail on modern YouTube pages. "
            "Install Node.js and add it to PATH."
        )
        results["node"] = False

    return results


def _ensure_cache_dir() -> str:
    """Create the audio cache directory if it doesn't exist."""
    abs_path = os.path.abspath(AUDIO_CACHE_DIR)
    os.makedirs(abs_path, exist_ok=True)
    return abs_path


def get_cached_audio_path(video_id: str) -> str | None:
    """
    Check if audio for this video is already cached.

    Returns:
        Absolute path to cached audio file, or None if not cached.
    """
    cache_dir = _ensure_cache_dir()
    # Check common extensions
    for ext in (".mp3", ".m4a", ".webm", ".opus"):
        path = os.path.join(cache_dir, f"{video_id}{ext}")
        if os.path.isfile(path) and os.path.getsize(path) > 0:
            logger.info(f"Audio cache HIT for {video_id}: {path}")
            return path
    return None


def download_audio(video_id: str) -> str:
    """
    Download audio for a YouTube video using yt-dlp.

    Checks cache first. Downloads as MP3 (192kbps) using FFmpeg for conversion.

    Args:
        video_id: YouTube video ID (e.g., "dQw4w9WgXcQ")

    Returns:
        Absolute path to the downloaded audio file.

    Raises:
        RuntimeError: If download fails.
    """
    import yt_dlp

    # Check cache first
    cached = get_cached_audio_path(video_id)
    if cached:
        return cached

    cache_dir = _ensure_cache_dir()
    output_template = os.path.join(cache_dir, f"{video_id}.%(ext)s")
    expected_path = os.path.join(cache_dir, f"{video_id}.mp3")

    url = f"https://www.youtube.com/watch?v={video_id}"

    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": output_template,
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }
        ],
        "quiet": True,
        "no_warnings": False,
        "socket_timeout": 30,
        "retries": 3,
    }

    logger.info(f"Downloading audio for {video_id}...")

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
    except Exception as e:
        logger.error(
            f"Audio download failed for {video_id}: {type(e).__name__}: {e}",
            exc_info=True,
        )
        raise RuntimeError(f"Failed to download audio for {video_id}: {e}") from e

    # Verify file exists
    if os.path.isfile(expected_path) and os.path.getsize(expected_path) > 0:
        size_mb = os.path.getsize(expected_path) / (1024 * 1024)
        logger.info(f"Audio downloaded: {expected_path} ({size_mb:.1f} MB)")
        return expected_path

    # yt-dlp might have saved with a different extension — check cache
    fallback = get_cached_audio_path(video_id)
    if fallback:
        return fallback

    raise RuntimeError(
        f"Audio download completed but file not found at {expected_path}"
    )


def cleanup_audio(video_id: str) -> None:
    """
    Delete cached audio file for a video after successful transcription.

    Args:
        video_id: YouTube video ID
    """
    cache_dir = _ensure_cache_dir()
    for ext in (".mp3", ".m4a", ".webm", ".opus"):
        path = os.path.join(cache_dir, f"{video_id}{ext}")
        if os.path.isfile(path):
            try:
                os.remove(path)
                logger.debug(f"Cleaned up audio: {path}")
            except OSError as e:
                logger.warning(f"Failed to clean up {path}: {e}")


def get_cache_stats() -> dict:
    """Get stats about the audio cache directory."""
    cache_dir = _ensure_cache_dir()
    files = [
        f for f in os.listdir(cache_dir)
        if os.path.isfile(os.path.join(cache_dir, f))
    ]
    total_bytes = sum(
        os.path.getsize(os.path.join(cache_dir, f)) for f in files
    )
    return {
        "cache_dir": cache_dir,
        "file_count": len(files),
        "total_size_mb": round(total_bytes / (1024 * 1024), 2),
    }
