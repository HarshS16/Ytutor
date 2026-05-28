"""
Quiz generator — creates quiz questions from video transcripts.

Generates MCQ, True/False, and short answer questions
using the LLM with structured JSON output.
"""

import json
import logging
from api.services.groq_client import get_completion
from api.services.prompt_builder import build_quiz_prompt

logger = logging.getLogger(__name__)


def generate_quiz(
    transcript: str,
    video_title: str,
    count: int = 10,
) -> dict:
    """
    Generate quiz questions from a video transcript.

    Args:
        transcript: Cleaned transcript text
        video_title: Title of the video
        count: Number of questions to generate

    Returns:
        Dict with 'questions' (list of dicts) or 'error' key
    """
    if not transcript or not transcript.strip():
        return {"error": "No transcript content to generate quiz from"}

    logger.info(f"Generating {count} quiz questions for '{video_title}'")

    prompt = build_quiz_prompt(transcript, video_title, count)

    result = get_completion(
        system_prompt=prompt["system_prompt"],
        user_message=prompt["user_message"],
        max_tokens=3000,
    )

    if "error" in result:
        logger.error(f"Quiz generation error: {result['error']}")
        return result

    # Parse JSON response
    try:
        content = result["content"].strip()
        # Handle markdown code blocks
        if content.startswith("```"):
            lines = content.split("\n")
            content = "\n".join(lines[1:-1]) if lines[-1].strip() == "```" else "\n".join(lines[1:])
            content = content.strip()

        questions = json.loads(content)

        # Validate structure
        validated = []
        for q in questions:
            if isinstance(q, dict) and "question" in q and "correct_answer" in q:
                validated.append({
                    "question": q["question"],
                    "question_type": q.get("question_type", "mcq"),
                    "options": q.get("options"),
                    "correct_answer": q["correct_answer"],
                    "explanation": q.get("explanation", ""),
                })

        logger.info(f"Generated {len(validated)} valid quiz questions")
        return {"questions": validated}

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse quiz JSON: {e}")
        return {"error": "Failed to parse AI response. Please try again."}
