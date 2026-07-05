"""
Hierarchical notes generator.

Creates complete notes from all transcript chunks instead of truncating the
transcript into a single LLM call.
"""

import logging
import os
import re
from dataclasses import dataclass
from typing import Callable, Optional

from api.services.groq_client import get_completion
from api.services.prompt_builder import (
    build_notes_section_prompt,
    build_notes_takeaways_prompt,
)
from ingestion.transcript import format_timestamp

logger = logging.getLogger(__name__)

NOTES_SECTION_INPUT_CHARS = int(os.getenv("NOTES_SECTION_INPUT_CHARS", 12000))
NOTES_SECTION_MAX_TOKENS = int(os.getenv("NOTES_SECTION_MAX_TOKENS", 3000))
NOTES_TAKEAWAYS_MAX_TOKENS = int(os.getenv("NOTES_TAKEAWAYS_MAX_TOKENS", 1200))
NOTES_SECTION_RETRIES = int(os.getenv("NOTES_SECTION_RETRIES", 1))
NOTES_GENERATION_CONCURRENCY = int(os.getenv("NOTES_GENERATION_CONCURRENCY", 1))


@dataclass
class NoteSection:
    index: int
    start: float
    end: float
    text: str

    @property
    def timestamp_range(self) -> str:
        return f"{format_timestamp(self.start)}-{format_timestamp(self.end)}"


ProgressCallback = Callable[[dict], None]


def _normalize_chunk(chunk) -> dict:
    if isinstance(chunk, dict):
        return {
            "text": chunk.get("text") or chunk.get("chunk_text") or "",
            "timestamp_start": float(chunk.get("timestamp_start") or 0.0),
            "timestamp_end": float(chunk.get("timestamp_end") or 0.0),
        }

    return {
        "text": getattr(chunk, "chunk_text", "") or getattr(chunk, "text", "") or "",
        "timestamp_start": float(getattr(chunk, "timestamp_start", 0.0) or 0.0),
        "timestamp_end": float(getattr(chunk, "timestamp_end", 0.0) or 0.0),
    }


def build_note_sections(chunks: list, max_chars: int = NOTES_SECTION_INPUT_CHARS) -> list[NoteSection]:
    """Group ordered transcript chunks into larger section windows."""
    normalized = [_normalize_chunk(chunk) for chunk in chunks]
    normalized = [chunk for chunk in normalized if chunk["text"].strip()]
    if not normalized:
        return []

    sections: list[NoteSection] = []
    current_parts: list[str] = []
    current_start = normalized[0]["timestamp_start"]
    current_end = normalized[0]["timestamp_end"]
    current_len = 0

    for chunk in normalized:
        text = chunk["text"].strip()
        proposed_len = current_len + len(text) + 2
        if current_parts and proposed_len > max_chars:
            sections.append(NoteSection(
                index=len(sections) + 1,
                start=current_start,
                end=current_end,
                text="\n\n".join(current_parts),
            ))
            current_parts = []
            current_start = chunk["timestamp_start"]
            current_len = 0

        current_parts.append(text)
        current_len += len(text) + 2
        current_end = chunk["timestamp_end"]

    if current_parts:
        sections.append(NoteSection(
            index=len(sections) + 1,
            start=current_start,
            end=current_end,
            text="\n\n".join(current_parts),
        ))

    return sections


def _section_placeholder(section: NoteSection, error: str) -> str:
    return (
        f"## {section.timestamp_range}\n\n"
        f"> Notes generation failed for this section. The transcript range was not omitted.\n\n"
        f"**Error:** {error}\n"
    )


def _summarize_section_note(section: NoteSection, content: str) -> str:
    heading_lines = [
        line.strip("# ").strip()
        for line in content.splitlines()
        if line.startswith("#")
    ][:8]
    bullets = [
        line.strip()
        for line in content.splitlines()
        if line.lstrip().startswith(("-", "*", "1."))
    ][:8]
    summary_parts = heading_lines + bullets
    summary = " | ".join(part for part in summary_parts if part)
    summary = re.sub(r"\s+", " ", summary).strip()
    if len(summary) > 1200:
        summary = summary[:1200].rsplit(" ", 1)[0]
    return f"{section.index}. {section.timestamp_range}: {summary or 'Section notes generated.'}"


def _generate_section_note(
    section: NoteSection,
    video_title: str,
    note_type: str,
    section_total: int,
) -> tuple[str, Optional[str]]:
    prompt = build_notes_section_prompt(
        section_text=section.text,
        video_title=video_title,
        note_type=note_type,
        section_index=section.index,
        section_total=section_total,
        timestamp_range=section.timestamp_range,
    )

    last_error = None
    for attempt in range(NOTES_SECTION_RETRIES + 1):
        result = get_completion(
            system_prompt=prompt["system_prompt"],
            user_message=prompt["user_message"],
            max_tokens=NOTES_SECTION_MAX_TOKENS,
        )
        if "error" not in result:
            return result["content"], None

        last_error = result["error"]
        logger.warning(
            "Notes section %s/%s failed on attempt %s: %s",
            section.index,
            section_total,
            attempt + 1,
            last_error,
        )

    return _section_placeholder(section, last_error or "Unknown error"), last_error


def _generate_takeaways(video_title: str, note_type: str, summaries: list[str]) -> str:
    if not summaries:
        return "## Key Takeaways\n\n- No section summaries were available."

    prompt = build_notes_takeaways_prompt(
        section_summaries="\n".join(summaries),
        video_title=video_title,
        note_type=note_type,
    )
    result = get_completion(
        system_prompt=prompt["system_prompt"],
        user_message=prompt["user_message"],
        max_tokens=NOTES_TAKEAWAYS_MAX_TOKENS,
    )
    if "error" in result:
        logger.warning("Key takeaways generation failed: %s", result["error"])
        return "## Key Takeaways\n\n- Review the timestamped sections above for the complete topic coverage."
    return result["content"]


def generate_hierarchical_notes(
    chunks: list,
    video_title: str,
    note_type: str = "detailed",
    progress_callback: Optional[ProgressCallback] = None,
) -> dict:
    """
    Generate complete notes from ordered transcript chunks.

    Returns:
        Dict with content, sections_total, sections_failed, or error.
    """
    sections = build_note_sections(chunks)
    if not sections:
        return {"error": "No transcript chunks available to generate notes from"}

    if NOTES_GENERATION_CONCURRENCY != 1:
        logger.info(
            "NOTES_GENERATION_CONCURRENCY=%s configured; section generation remains ordered in v1",
            NOTES_GENERATION_CONCURRENCY,
        )

    logger.info(
        "Generating hierarchical %s notes for '%s' across %s sections",
        note_type,
        video_title,
        len(sections),
    )

    section_notes: list[str] = []
    section_summaries: list[str] = []
    failed_sections = 0

    for section in sections:
        if progress_callback:
            progress_callback({
                "section_index": section.index,
                "sections_total": len(sections),
                "timestamp_range": section.timestamp_range,
            })

        content, error = _generate_section_note(
            section=section,
            video_title=video_title,
            note_type=note_type,
            section_total=len(sections),
        )
        if error:
            failed_sections += 1

        section_notes.append(content)
        section_summaries.append(_summarize_section_note(section, content))

    takeaways = _generate_takeaways(video_title, note_type, section_summaries)

    coverage_lines = [
        f"| {section.index} | {section.timestamp_range} |"
        for section in sections
    ]

    content = "\n\n".join([
        f"# Complete {note_type.title()} Notes: {video_title}",
        "## Coverage",
        (
            f"- Sections covered: {len(sections)}\n"
            f"- Timestamp range: {sections[0].timestamp_range.split('-')[0]}-"
            f"{sections[-1].timestamp_range.split('-')[-1]}\n"
            f"- Failed sections: {failed_sections}"
        ),
        "## Section Index\n\n| Section | Timestamp Range |\n| --- | --- |\n" + "\n".join(coverage_lines),
        "## Complete Timestamped Notes",
        "\n\n".join(section_notes),
        takeaways,
    ])

    logger.info(
        "Generated hierarchical notes for '%s': %s chars, %s sections, %s failed",
        video_title,
        len(content),
        len(sections),
        failed_sections,
    )

    return {
        "content": content,
        "sections_total": len(sections),
        "sections_failed": failed_sections,
    }


def generate_notes(transcript: str, video_title: str, note_type: str = "detailed") -> dict:
    """Compatibility wrapper for callers that still pass a full transcript."""
    if not transcript or not transcript.strip():
        return {"error": "No transcript content to generate notes from"}
    return generate_hierarchical_notes(
        chunks=[{
            "text": transcript,
            "timestamp_start": 0.0,
            "timestamp_end": 0.0,
        }],
        video_title=video_title,
        note_type=note_type,
    )
