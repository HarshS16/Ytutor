"""
YouTube playlist and video metadata extraction using yt-dlp.

Extracts playlist info (title, description, channel, thumbnail)
and individual video metadata (title, duration, thumbnail, video_id)
without requiring a YouTube Data API key.
"""

import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)


def extract_playlist_id(url: str) -> Optional[str]:
    """
    Extract the playlist ID from a YouTube playlist URL.

    Supports formats:
    - https://www.youtube.com/playlist?list=PLxxxxxx
    - https://youtube.com/playlist?list=PLxxxxxx
    - https://www.youtube.com/watch?v=xxx&list=PLxxxxxx

    Returns:
        Playlist ID string, or None if not found.
    """
    patterns = [
        r"[?&]list=([a-zA-Z0-9_-]+)",
        r"youtube\.com/playlist\?list=([a-zA-Z0-9_-]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


def fetch_playlist_metadata(playlist_url: str) -> dict:
    """
    Fetch playlist metadata and all video entries using yt-dlp.

    Args:
        playlist_url: Full YouTube playlist URL.

    Returns:
        Dict with keys:
        - title, description, channel, thumbnail, playlist_id
        - videos: list of dicts with video_id, title, duration, thumbnail, position
    """
    import yt_dlp

    playlist_id = extract_playlist_id(playlist_url)
    if not playlist_id:
        raise ValueError(f"Invalid playlist URL: {playlist_url}")

    # Normalize URL to standard format
    normalized_url = f"https://www.youtube.com/playlist?list={playlist_id}"

    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": True,  # Don't download, just extract metadata
        "force_generic_extractor": False,
    }

    logger.info(f"Fetching playlist metadata: {normalized_url}")

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(normalized_url, download=False)
        except Exception as e:
            logger.error(f"yt-dlp error: {e}")
            raise ValueError(f"Could not fetch playlist: {str(e)}")

    if not info:
        raise ValueError("Could not extract playlist info")

    entries = info.get("entries", [])
    if not entries:
        raise ValueError("Playlist is empty or unavailable")

    videos = []
    for idx, entry in enumerate(entries):
        if entry is None:
            continue

        video_id = entry.get("id", entry.get("url", ""))
        # yt-dlp flat extraction gives url as video ID sometimes
        if "youtube.com" in video_id or "youtu.be" in video_id:
            vid_match = re.search(r"(?:v=|/)([a-zA-Z0-9_-]{11})", video_id)
            video_id = vid_match.group(1) if vid_match else video_id

        videos.append({
            "video_id": video_id,
            "title": entry.get("title", f"Video {idx + 1}"),
            "duration": entry.get("duration", 0) or 0,
            "thumbnail": (
                entry.get("thumbnail", "")
                or f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg"
            ),
            "position": idx,
        })

    result = {
        "playlist_id": playlist_id,
        "title": info.get("title", "Untitled Playlist"),
        "description": info.get("description", "") or "",
        "channel": info.get("uploader", info.get("channel", "Unknown")),
        "thumbnail": info.get("thumbnail", "") or (
            videos[0]["thumbnail"] if videos else ""
        ),
        "videos": videos,
    }

    logger.info(f"Extracted {len(videos)} videos from playlist '{result['title']}'")
    return result
