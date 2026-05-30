"""
Chat router — handles the /api/chat endpoint.

Orchestrates the full RAG pipeline: retrieve → build prompt → generate.
Scoped to a specific playlist's vector store.
"""

import logging
import re
import time
from fastapi import APIRouter, HTTPException

from api.models.schemas import ChatRequest, ChatResponse, SourceCitation
from api.services.retriever import retrieve
from api.services.prompt_builder import (
    build_chat_prompt, build_conversational_prompt, get_no_context_response,
)
from api.services.groq_client import get_completion
from ingestion.transcript import format_timestamp

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["chat"])

# ── Patterns for generic/conversational messages ───────────────────
GREETING_PATTERNS = [
    r"^(hi|hello|hey|hola|namaste|howdy|sup|yo|hii+|heyy+|helloo+)[\s!.,?]*$",
    r"^(good\s*(morning|afternoon|evening|night|day))[\s!.,?]*$",
    r"^(thanks|thank\s*you|thx|ty|thankyou)[\s!.,?]*$",
    r"^(bye|goodbye|see\s*you|take\s*care|cya)[\s!.,?]*$",
    r"^(how\s*are\s*you|how\s*do\s*you\s*do|what'?s\s*up|wassup|whats\s*up)[\s!?.,]*$",
    r"^(who\s*are\s*you|what\s*are\s*you|what\s*can\s*you\s*do)[\s!?.,]*$",
    r"^(help|help\s*me)[\s!?.,]*$",
    r"^(ok|okay|sure|great|cool|nice|awesome|got\s*it|understood|alright)[\s!.,?]*$",
]

COMPILED_PATTERNS = [re.compile(p, re.IGNORECASE) for p in GREETING_PATTERNS]


def is_conversational_message(message: str) -> bool:
    """Check if a message is a generic greeting or conversational message."""
    cleaned = message.strip()
    return any(p.match(cleaned) for p in COMPILED_PATTERNS)


@router.post("/chat/query", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Process a user chat message through the RAG pipeline.

    1. Check if message is conversational
    2. Retrieve relevant chunks from the playlist's vector store
    3. Build context-grounded prompt
    4. Generate response via Groq LLM
    5. Return answer with source citations
    """
    start_time = time.time()
    user_message = request.message.strip()

    logger.info(f"Chat: playlist={request.playlist_id}, msg='{user_message[:100]}'")

    # ── Step 1: Check for conversational messages ──────────────────
    if is_conversational_message(user_message):
        logger.info("Detected conversational message")
        prompt_data = build_conversational_prompt(user_message)

        try:
            result = get_completion(
                system_prompt=prompt_data["system_prompt"],
                user_message=prompt_data["user_message"],
            )
        except Exception as e:
            logger.error(f"Groq error (conversational): {type(e).__name__}: {e}", exc_info=True)
            raise HTTPException(status_code=502, detail=f"Error generating response: {str(e)}")

        elapsed = round(time.time() - start_time, 2)
        logger.info(f"Response time: {elapsed}s (conversational)")

        answer = result.get("content", result.get("error", "Something went wrong."))
        return ChatResponse(answer=answer, sources=[], found_context=False)

    # ── Step 2: Retrieve relevant chunks ───────────────────────────
    try:
        chunks = retrieve(request.playlist_id, user_message)
    except Exception as e:
        logger.error(f"Retrieval error for playlist {request.playlist_id}: {type(e).__name__}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error searching the knowledge base: {str(e)}")

    # ── Step 3: Handle no-context case ─────────────────────────────
    if not chunks:
        logger.info("No relevant context found — LLM conversational fallback")
        prompt_data = build_conversational_prompt(user_message)

        try:
            result = get_completion(
                system_prompt=prompt_data["system_prompt"],
                user_message=prompt_data["user_message"],
            )
        except Exception:
            return ChatResponse(
                answer=get_no_context_response(),
                sources=[],
                found_context=False,
            )

        answer = result.get("content", get_no_context_response())
        return ChatResponse(answer=answer, sources=[], found_context=False)

    # ── Step 4: Build RAG prompt ───────────────────────────────────
    prompt_data = build_chat_prompt(chunks, user_message)

    # ── Step 5: Generate response ──────────────────────────────────
    try:
        result = get_completion(
            system_prompt=prompt_data["system_prompt"],
            user_message=prompt_data["user_message"],
        )
    except Exception as e:
        logger.error(f"Groq error (RAG): {type(e).__name__}: {e}", exc_info=True)
        raise HTTPException(status_code=502, detail=f"Error generating response: {str(e)}")

    if "error" in result:
        return ChatResponse(answer=result["error"], sources=[], found_context=True)

    # ── Step 6: Build source citations ─────────────────────────────
    seen_videos = set()
    sources = []

    for chunk in chunks:
        video_key = f"{chunk['video_id']}:{chunk['chunk_index']}"
        if video_key not in seen_videos:
            seen_videos.add(video_key)
            ts_start = chunk.get("timestamp_start", 0)
            ts_end = chunk.get("timestamp_end", 0)
            sources.append(SourceCitation(
                video_title=chunk["video_title"],
                video_id=chunk.get("video_id", ""),
                timestamp_start=ts_start,
                timestamp_end=ts_end,
                timestamp_display=f"{format_timestamp(ts_start)} – {format_timestamp(ts_end)}",
                snippet=chunk["text"][:150] + "..." if len(chunk["text"]) > 150 else chunk["text"],
                score=chunk.get("score", 0),
            ))

    elapsed = round(time.time() - start_time, 2)
    logger.info(f"Response time: {elapsed}s | Sources: {len(sources)}")

    return ChatResponse(
        answer=result["content"],
        sources=sources,
        found_context=True,
    )
