"""
Voice-note organization helpers.

Turns a raw speech transcript into structured notes while preserving the
speaker's original language mix.
"""

import os
import re

from api.services.groq_client import get_completion

VOICE_ORGANIZE_INPUT_CHARS = int(os.getenv("VOICE_ORGANIZE_INPUT_CHARS", "10000"))
VOICE_ORGANIZE_MAX_TOKENS = int(os.getenv("VOICE_ORGANIZE_MAX_TOKENS", "3000"))
VOICE_CLEANUP_MAX_TOKENS = int(os.getenv("VOICE_CLEANUP_MAX_TOKENS", "3000"))

LANGUAGE_MODE_INSTRUCTIONS = {
    "preserve": (
        "Preserve the exact language and script used by the speaker. If the "
        "speaker mixes Hindi and English, keep that natural mix."
    ),
    "hinglish": (
        "Write in natural Hinglish / Roman Hindi. Use Roman Hindi for Hindi "
        "sentences and preserve English technical terms as English."
    ),
    "hindi": (
        "Write Hindi content in Devanagari script and preserve English technical "
        "terms where learners commonly use them."
    ),
    "english": "Write in English, preserving technical terms and meaning.",
}


def _chunk_text(text: str, max_chars: int) -> list[str]:
    clean = re.sub(r"\n{3,}", "\n\n", (text or "").strip())
    if not clean:
        return []
    if len(clean) <= max_chars:
        return [clean]

    paragraphs = re.split(r"\n\s*\n", clean)
    chunks: list[str] = []
    current = ""
    for paragraph in paragraphs:
        paragraph = paragraph.strip()
        if not paragraph:
            continue

        if len(paragraph) > max_chars:
            sentences = re.split(r"(?<=[.!?।])\s+", paragraph)
            for sentence in sentences:
                sentence = sentence.strip()
                if not sentence:
                    continue
                if current and len(current) + len(sentence) + 1 > max_chars:
                    chunks.append(current.strip())
                    current = ""
                current = f"{current} {sentence}".strip()
            continue

        if current and len(current) + len(paragraph) + 2 > max_chars:
            chunks.append(current.strip())
            current = paragraph
        else:
            current = f"{current}\n\n{paragraph}".strip()

    if current:
        chunks.append(current.strip())
    return chunks


def _language_instruction(language_mode: str) -> str:
    return LANGUAGE_MODE_INSTRUCTIONS.get(language_mode or "hinglish", LANGUAGE_MODE_INSTRUCTIONS["hinglish"])


def clean_voice_transcript(raw_transcript: str, language_mode: str = "hinglish") -> str:
    """
    Repair punctuation and obvious speech-to-text issues without summarizing.
    """
    chunks = _chunk_text(raw_transcript, VOICE_ORGANIZE_INPUT_CHARS)
    if not chunks:
        return ""

    cleaned_chunks = []
    for index, chunk in enumerate(chunks, start=1):
        system_prompt = (
            "You clean speech-to-text transcripts for Indian students. Fix only "
            "obvious transcription mistakes, punctuation, sentence boundaries, "
            "and repeated filler. Do not summarize, do not add facts, do not "
            "remove meaningful details, and do not explain your changes."
        )
        user_message = f"""
Language/script mode: {language_mode}
Instruction: {_language_instruction(language_mode)}
Part: {index}/{len(chunks)}

Raw transcript:
{chunk}

Return only the cleaned transcript text.
"""
        response = get_completion(
            system_prompt=system_prompt,
            user_message=user_message,
            max_tokens=VOICE_CLEANUP_MAX_TOKENS,
        )
        if response.get("error"):
            raise RuntimeError(response["error"])
        cleaned_chunks.append(response.get("content", "").strip())

    return "\n\n".join(part for part in cleaned_chunks if part).strip()


def _organize_chunk(
    transcript: str,
    title: str,
    chunk_index: int,
    chunk_total: int,
    language_mode: str,
) -> str:
    system_prompt = (
        "You organize spoken student notes into clean study notes. Preserve the "
        "speaker's intended language/script mode. Do not add outside facts, do "
        "not invent details, and do not summarize away meaningful points. Remove "
        "filler words and repeated false starts only when they do not change meaning."
    )
    user_message = f"""
Voice note title: {title or "Voice Note"}
Part: {chunk_index}/{chunk_total}
Language/script mode: {language_mode}
Instruction: {_language_instruction(language_mode)}

Raw transcript:
{transcript}

Create structured markdown notes for this part.

Rules:
- Follow the selected language/script mode exactly.
- Preserve all concepts, examples, definitions, steps, doubts, and conclusions.
- Use clear headings, bullets, numbered steps, and short paragraphs.
- Mark unclear audio as "Unclear:" instead of guessing.
- Do not mention that this is an AI-generated organization.
"""

    response = get_completion(
        system_prompt=system_prompt,
        user_message=user_message,
        max_tokens=VOICE_ORGANIZE_MAX_TOKENS,
    )
    if response.get("error"):
        raise RuntimeError(response["error"])
    return response.get("content", "").strip()


def organize_voice_transcript(
    raw_transcript: str,
    title: str = "Voice Note",
    language_mode: str = "hinglish",
) -> str:
    """Organize a raw voice transcript into complete markdown notes."""
    chunks = _chunk_text(raw_transcript, VOICE_ORGANIZE_INPUT_CHARS)
    if not chunks:
        raise ValueError("Transcript is empty")

    organized_sections = []
    for index, chunk in enumerate(chunks, start=1):
        content = _organize_chunk(chunk, title, index, len(chunks), language_mode)
        if len(chunks) > 1:
            organized_sections.append(f"## Part {index}\n\n{content}")
        else:
            organized_sections.append(content)

    header = f"# {title or 'Voice Note'}\n\n"
    if len(chunks) > 1:
        header += f"> Organized from {len(chunks)} transcript parts. Language and meaning preserved.\n\n"

    return header + "\n\n---\n\n".join(organized_sections).strip()
