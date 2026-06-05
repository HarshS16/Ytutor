"""
Prompt builder for Ytutor AI.

Constructs system prompts for different use cases:
- RAG-grounded chat (context from video transcripts)
- Conversational messages (greetings, meta-questions)
- Notes generation
- Flashcard generation
- Quiz generation

Optimized for minimal token usage without sacrificing output quality.
"""

import logging

from ingestion.transcript import format_timestamp

logger = logging.getLogger(__name__)

# ── Maximum transcript chars sent to generators ────────────────────
MAX_TRANSCRIPT_CHARS = 6000


def _smart_truncate(text: str, max_chars: int = MAX_TRANSCRIPT_CHARS) -> str:
    """
    Truncate transcript at a sentence boundary to avoid mid-thought cuts.

    Finds the last '. ' within the allowed window so the LLM always
    receives complete sentences.
    """
    if len(text) <= max_chars:
        return text
    truncated = text[:max_chars]
    # Find last sentence boundary
    last_period = truncated.rfind('. ')
    if last_period > max_chars * 0.7:
        return truncated[:last_period + 1]
    return truncated


def build_chat_prompt(chunks: list[dict], user_message: str) -> dict:
    """
    Build a RAG-grounded prompt for playlist chat.

    Args:
        chunks: Retrieved chunks with video_title, timestamp_start, timestamp_end, text
        user_message: User's question

    Returns:
        Dict with 'system_prompt' and 'user_message' keys.
    """
    # Format context with video citations
    context_parts = []
    for i, chunk in enumerate(chunks, 1):
        ts_start = format_timestamp(chunk.get("timestamp_start", 0))
        ts_end = format_timestamp(chunk.get("timestamp_end", 0))
        video_title = chunk.get("video_title", "Unknown Video")

        context_parts.append(
            f"[{i}] \"{video_title}\" ({ts_start}–{ts_end})\n"
            f"{chunk['text']}"
        )

    context_block = "\n\n---\n\n".join(context_parts)

    system_prompt = f"""You are Ytutor AI, a tutor for YouTube playlist content.
Answer ONLY from the context below. Cite video titles and timestamps (e.g. "In 'Video Title' at 5:30…").
Explain clearly with examples. Use markdown formatting. If the context is insufficient, say so. Never invent facts.

Context:

{context_block}"""

    return {
        "system_prompt": system_prompt,
        "user_message": user_message,
    }


def build_conversational_prompt(user_message: str) -> dict:
    """Build a prompt for conversational/meta messages (uses lighter model)."""
    system_prompt = """You are Ytutor AI, a friendly learning assistant for YouTube playlists.
You help students learn via chat, notes, flashcards, and quizzes from playlist content.
Be warm and concise. If no playlist is imported yet, suggest pasting a YouTube playlist URL."""

    return {
        "system_prompt": system_prompt,
        "user_message": user_message,
    }


def build_notes_prompt(transcript: str, video_title: str, note_type: str = "detailed") -> dict:
    """
    Build a prompt for generating structured notes from a transcript.

    Args:
        transcript: Video transcript text
        video_title: Title of the video
        note_type: "concise", "detailed", or "revision"
    """
    type_instructions = {
        "concise": "Create brief, bullet-point notes covering only the key takeaways. Keep it under 500 words.",
        "detailed": "Create comprehensive notes with full explanations, examples, and sub-topics. Include all important details.",
        "revision": "Create quick-revision notes with key terms, definitions, and essential formulas/concepts. Format for rapid review.",
    }

    instruction = type_instructions.get(note_type, type_instructions["detailed"])

    system_prompt = f"""You are an expert note-taker creating study notes from a video transcript.

## Instructions:
{instruction}

## Formatting Rules:
- ALWAYS write notes in English, even if the transcript is in another language
- Use markdown formatting (# headers, ## sub-headers, - bullet points)
- Bold **key terms** and important concepts
- Use numbered lists for sequential processes/steps
- Include relevant examples from the transcript
- Organize by topic/concept hierarchy
- Add a "Key Takeaways" section at the end

## Video: "{video_title}"
"""

    return {
        "system_prompt": system_prompt,
        "user_message": f"Generate {note_type} notes from this transcript:\n\n{_smart_truncate(transcript)}",
    }


def build_flashcards_prompt(transcript: str, video_title: str, count: int = 10) -> dict:
    """Build a prompt for generating flashcards from a transcript."""
    system_prompt = f"""You are an expert educator creating flashcards for students studying video content.

## Instructions:
- Generate exactly {count} flashcards from the transcript
- Each flashcard should test one specific concept
- Questions should be clear and unambiguous
- Answers should be concise but complete
- Tag each with difficulty: "easy", "medium", or "hard"
- Tag each with a topic/category
- ALWAYS write in English, even if the transcript is in another language

## Output Format (STRICT JSON):
Return a JSON array of objects with this exact structure:
[
  {{
    "question": "What is...?",
    "answer": "It is...",
    "difficulty": "medium",
    "topic": "Topic Name"
  }}
]

Return ONLY the JSON array, no other text.

## Video: "{video_title}"
"""

    return {
        "system_prompt": system_prompt,
        "user_message": f"Generate {count} flashcards from this transcript:\n\n{_smart_truncate(transcript)}",
    }


def build_quiz_prompt(transcript: str, video_title: str, count: int = 10) -> dict:
    """Build a prompt for generating quiz questions from a transcript."""
    system_prompt = f"""You are an expert educator creating quiz questions from video content.

## Instructions:
- Generate exactly {count} questions from the transcript
- Mix question types: MCQ (multiple choice), true_false, and short_answer
- MCQ questions should have exactly 4 options (A, B, C, D)
- Questions should test understanding, not just recall
- Include explanations for correct answers
- ALWAYS write in English, even if the transcript is in another language

## Output Format (STRICT JSON):
Return a JSON array of objects with this exact structure:
[
  {{
    "question": "What is...?",
    "question_type": "mcq",
    "options": ["A) Option 1", "B) Option 2", "C) Option 3", "D) Option 4"],
    "correct_answer": "A) Option 1",
    "explanation": "This is correct because..."
  }},
  {{
    "question": "True or False: ...",
    "question_type": "true_false",
    "options": ["True", "False"],
    "correct_answer": "True",
    "explanation": "This is true because..."
  }},
  {{
    "question": "Explain...",
    "question_type": "short_answer",
    "options": null,
    "correct_answer": "The answer is...",
    "explanation": "Key points to include..."
  }}
]

Return ONLY the JSON array, no other text.

## Video: "{video_title}"
"""

    return {
        "system_prompt": system_prompt,
        "user_message": f"Generate {count} quiz questions from this transcript:\n\n{_smart_truncate(transcript)}",
    }


def get_no_context_response() -> str:
    """Fallback response when no relevant context is found."""
    return (
        "I couldn't find relevant information in the playlist transcripts for that question. "
        "Try rephrasing your question, or make sure the topic is covered in one of the playlist videos. "
        "You can also ask me to generate notes or flashcards to explore the content!"
    )
