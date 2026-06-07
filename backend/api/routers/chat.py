"""
Chat router — handles the /api/chat endpoint.

Orchestrates the full RAG pipeline: retrieve → build prompt → generate.
Scoped to a specific playlist's vector store.

Supports both blocking and streaming (SSE) responses.
"""

import json
import logging
import os
import re
import time
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.schemas import ChatRequest, ChatResponse, SourceCitation
from api.auth import get_current_user
from db.database import get_db
from db import crud
from api.services.retriever import retrieve
from api.services.prompt_builder import (
    build_chat_prompt, build_conversational_prompt, get_no_context_response,
)
from api.services.groq_client import get_completion, get_completion_stream
from ingestion.transcript import format_timestamp

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["chat"])

# ── Light model for conversational messages ────────────────────────
GROQ_MODEL_LIGHT = os.getenv("GROQ_MODEL_LIGHT", "llama-3.1-8b-instant")

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


def _build_sources(chunks: list[dict]) -> list[SourceCitation]:
    """Build source citations from retrieved chunks."""
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

    return sources


@router.post("/chat/query", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Process a user chat message through the RAG pipeline (blocking).

    1. Check if message is conversational
    2. Retrieve relevant chunks from the playlist's vector store
    3. Build context-grounded prompt
    4. Generate response via Groq LLM
    5. Return answer with source citations
    """
    start_time = time.time()
    user_message = request.message.strip()

    logger.info(f"Chat: playlist={request.playlist_id}, msg='{user_message[:100]}'")

    # Verify playlist ownership
    playlist = await crud.get_playlist(db, request.playlist_id)
    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist not found")
    if playlist.user_id is not None and playlist.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this playlist")

    # Save user message to history
    await crud.save_chat_message(
        db, 
        user_id=current_user.id, 
        playlist_id=request.playlist_id, 
        role="user", 
        content=user_message
    )

    # ── Step 1: Check for conversational messages ──────────────────
    if is_conversational_message(user_message):
        logger.info("Detected conversational message — using light model")
        prompt_data = build_conversational_prompt(user_message)

        try:
            result = get_completion(
                system_prompt=prompt_data["system_prompt"],
                user_message=prompt_data["user_message"],
                model=GROQ_MODEL_LIGHT,
                max_tokens=300,
            )
        except Exception as e:
            logger.error(f"Groq error (conversational): {type(e).__name__}: {e}", exc_info=True)
            raise HTTPException(status_code=502, detail=f"Error generating response: {str(e)}")

        elapsed = round(time.time() - start_time, 2)
        logger.info(f"Response time: {elapsed}s (conversational, light model)")

        answer = result.get("content", result.get("error", "Something went wrong."))
        
        # Save assistant message to history
        await crud.save_chat_message(
            db, 
            user_id=current_user.id, 
            playlist_id=request.playlist_id, 
            role="assistant", 
            content=answer
        )
        
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
                model=GROQ_MODEL_LIGHT,
                max_tokens=500,
            )
        except Exception:
            return ChatResponse(
                answer=get_no_context_response(),
                sources=[],
                found_context=False,
            )

        answer = result.get("content", get_no_context_response())
        
        # Save assistant message
        await crud.save_chat_message(
            db, 
            user_id=current_user.id, 
            playlist_id=request.playlist_id, 
            role="assistant", 
            content=answer
        )
        
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
    sources = _build_sources(chunks)

    elapsed = round(time.time() - start_time, 2)
    logger.info(f"Response time: {elapsed}s | Sources: {len(sources)}")

    # Save assistant message with sources
    await crud.save_chat_message(
        db, 
        user_id=current_user.id, 
        playlist_id=request.playlist_id, 
        role="assistant", 
        content=result["content"],
        sources=[s.model_dump() for s in sources]
    )

    return ChatResponse(
        answer=result["content"],
        sources=sources,
        found_context=True,
    )


# ── SSE Streaming Endpoint ─────────────────────────────────────────

@router.post("/chat/query/stream")
async def chat_stream(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Stream a chat response via Server-Sent Events (SSE).

    The response is streamed token-by-token so the user sees output
    immediately instead of waiting for the full response.

    SSE event types:
    - {"token": "..."} — a content token
    - {"sources": [...], "done": true} — final event with citations
    - {"error": "..."} — error event
    """
    user_message = request.message.strip()

    logger.info(f"Chat stream: playlist={request.playlist_id}, msg='{user_message[:100]}'")

    # Verify playlist ownership
    playlist = await crud.get_playlist(db, request.playlist_id)
    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist not found")
    if playlist.user_id is not None and playlist.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this playlist")

    # Save user message
    await crud.save_chat_message(
        db, 
        user_id=current_user.id, 
        playlist_id=request.playlist_id, 
        role="user", 
        content=user_message
    )

    # ── Conversational messages — don't stream, just respond fast ──
    if is_conversational_message(user_message):
        logger.info("Streaming: conversational message — using light model")
        prompt_data = build_conversational_prompt(user_message)

        async def conv_stream():
            try:
                full_content = ""
                for token in get_completion_stream(
                    system_prompt=prompt_data["system_prompt"],
                    user_message=prompt_data["user_message"],
                    model=GROQ_MODEL_LIGHT,
                    max_tokens=300,
                ):
                    full_content += token
                    yield f"data: {json.dumps({'token': token})}\n\n"
                
                # Save assistant message when done
                await crud.save_chat_message(
                    db, 
                    user_id=current_user.id, 
                    playlist_id=request.playlist_id, 
                    role="assistant", 
                    content=full_content
                )
                
                yield f"data: {json.dumps({'done': True, 'sources': [], 'found_context': False})}\n\n"
            except Exception as e:
                logger.error(f"Stream error (conversational): {e}", exc_info=True)
                yield f"data: {json.dumps({'error': str(e)})}\n\n"

        return StreamingResponse(conv_stream(), media_type="text/event-stream")

    # ── Retrieve chunks ────────────────────────────────────────────
    try:
        chunks = retrieve(request.playlist_id, user_message)
    except Exception as e:
        logger.error(f"Retrieval error: {e}", exc_info=True)

        async def error_stream():
            yield f"data: {json.dumps({'error': f'Error searching knowledge base: {str(e)}'})}\n\n"

        return StreamingResponse(error_stream(), media_type="text/event-stream")

    # ── No context — stream fallback ───────────────────────────────
    if not chunks:
        logger.info("Streaming: no context — conversational fallback")
        prompt_data = build_conversational_prompt(user_message)

        async def no_ctx_stream():
            try:
                full_content = ""
                for token in get_completion_stream(
                    system_prompt=prompt_data["system_prompt"],
                    user_message=prompt_data["user_message"],
                    model=GROQ_MODEL_LIGHT,
                    max_tokens=500,
                ):
                    full_content += token
                    yield f"data: {json.dumps({'token': token})}\n\n"
                    
                # Save assistant message
                await crud.save_chat_message(
                    db, 
                    user_id=current_user.id, 
                    playlist_id=request.playlist_id, 
                    role="assistant", 
                    content=full_content
                )
                yield f"data: {json.dumps({'done': True, 'sources': [], 'found_context': False})}\n\n"
            except Exception as e:
                yield f"data: {json.dumps({'error': str(e)})}\n\n"

        return StreamingResponse(no_ctx_stream(), media_type="text/event-stream")

    # ── RAG streaming ──────────────────────────────────────────────
    prompt_data = build_chat_prompt(chunks, user_message)
    sources = _build_sources(chunks)

    # Serialize sources for the final SSE event
    sources_json = [
        {
            "video_title": s.video_title,
            "video_id": s.video_id,
            "timestamp_start": s.timestamp_start,
            "timestamp_end": s.timestamp_end,
            "timestamp_display": s.timestamp_display,
            "snippet": s.snippet,
            "score": s.score,
        }
        for s in sources
    ]

    async def rag_stream():
        try:
            full_content = ""
            for token in get_completion_stream(
                system_prompt=prompt_data["system_prompt"],
                user_message=prompt_data["user_message"],
            ):
                full_content += token
                yield f"data: {json.dumps({'token': token})}\n\n"

            # Save assistant message with sources
            await crud.save_chat_message(
                db, 
                user_id=current_user.id, 
                playlist_id=request.playlist_id, 
                role="assistant", 
                content=full_content,
                sources=sources_json
            )

            # Final event with sources
            yield f"data: {json.dumps({'done': True, 'sources': sources_json, 'found_context': True})}\n\n"

        except Exception as e:
            logger.error(f"Stream error (RAG): {e}", exc_info=True)
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(rag_stream(), media_type="text/event-stream")


@router.get("/chat/history/{playlist_id}")
async def get_history(
    playlist_id: int,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Retrieve chat history for a playlist."""
    # Verify playlist ownership
    playlist = await crud.get_playlist(db, playlist_id)
    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist not found")
    if playlist.user_id is not None and playlist.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this playlist")
        
    history = await crud.get_chat_history(db, user_id=current_user.id, playlist_id=playlist_id)
    
    return [
        {
            "id": msg.id,
            "role": msg.role,
            "content": msg.content,
            "sources": msg.sources or [],
            "created_at": msg.created_at
        }
        for msg in history
    ]
