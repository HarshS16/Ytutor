"""
Notes generator — creates structured notes from video transcripts.

Uses the LLM to generate concise, detailed, or revision notes
from transcript content.
"""

import logging
from api.services.groq_client import get_completion
from api.services.prompt_builder import build_notes_prompt

logger = logging.getLogger(__name__)


def generate_notes(
    transcript: str,
    video_title: str,
    note_type: str = "detailed",
) -> dict:
    """
    Generate structured notes from a video transcript.

    Args:
        transcript: Cleaned transcript text
        video_title: Title of the video
        note_type: "concise", "detailed", or "revision"

    Returns:
        Dict with 'content' (markdown string) or 'error' key
    """
    if not transcript or not transcript.strip():
        return {"error": "No transcript content to generate notes from"}

    logger.info(f"Generating {note_type} notes for '{video_title}'")

    prompt = build_notes_prompt(transcript, video_title, note_type)

    result = get_completion(
        system_prompt=prompt["system_prompt"],
        user_message=prompt["user_message"],
        max_tokens=3000,
    )

    if "error" in result:
        logger.error(f"Notes generation error: {result['error']}")
        return result

    logger.info(f"Generated notes: {len(result['content'])} chars")
    return {"content": result["content"]}
