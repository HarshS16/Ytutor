"""
Flashcard generator — creates Q&A flashcards from video transcripts.

Uses the LLM to generate structured flashcards with
question, answer, difficulty, and topic tags.
"""

import json
import logging
from api.services.groq_client import get_completion
from api.services.prompt_builder import build_flashcards_prompt

logger = logging.getLogger(__name__)


def generate_flashcards(
    transcript: str,
    video_title: str,
    count: int = 10,
) -> dict:
    """
    Generate flashcards from a video transcript.

    Args:
        transcript: Cleaned transcript text
        video_title: Title of the video
        count: Number of flashcards to generate

    Returns:
        Dict with 'flashcards' (list of dicts) or 'error' key
    """
    if not transcript or not transcript.strip():
        return {"error": "No transcript content to generate flashcards from"}

    logger.info(f"Generating {count} flashcards for '{video_title}'")

    prompt = build_flashcards_prompt(transcript, video_title, count)

    result = get_completion(
        system_prompt=prompt["system_prompt"],
        user_message=prompt["user_message"],
        max_tokens=3000,
    )

    if "error" in result:
        logger.error(f"Flashcard generation error: {result['error']}")
        return result

    # Parse JSON response
    try:
        content = result["content"].strip()
        # Handle markdown code blocks wrapping the JSON
        if content.startswith("```"):
            lines = content.split("\n")
            content = "\n".join(lines[1:-1]) if lines[-1].strip() == "```" else "\n".join(lines[1:])
            content = content.strip()

        flashcards = json.loads(content)

        # Validate structure
        validated = []
        for card in flashcards:
            if isinstance(card, dict) and "question" in card and "answer" in card:
                validated.append({
                    "question": card["question"],
                    "answer": card["answer"],
                    "difficulty": card.get("difficulty", "medium"),
                    "topic": card.get("topic", "General"),
                })

        logger.info(f"Generated {len(validated)} valid flashcards")
        return {"flashcards": validated}

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse flashcard JSON: {e}")
        return {"error": "Failed to parse AI response. Please try again."}
