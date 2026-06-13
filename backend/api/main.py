"""
FastAPI application entrypoint for Ytutor AI.

Configures the app with CORS, rate limiting, routers, and
health/admin endpoints. Initializes the database on startup.
"""

import asyncio
import logging
import os
import sys
import time
import traceback
from collections import defaultdict
from datetime import datetime, timezone

from dotenv import load_dotenv
load_dotenv()

# Initialize structured logging BEFORE anything else
from api.logging_config import setup_logging
setup_logging()

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

# ── Configuration ──────────────────────────────────────────────────
ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS", "http://localhost:5173,http://localhost:3000"
).split(",")
MAX_REQUESTS_PER_MINUTE = int(os.getenv("MAX_REQUESTS_PER_MINUTE", 30))

# ── App setup ──────────────────────────────────────────────────────
app = FastAPI(
    title="Ytutor AI API",
    description="AI-powered learning assistant for YouTube playlists",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1):\d+",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Simple in-memory rate limiter ──────────────────────────────────
rate_limit_store: dict[str, list[float]] = defaultdict(list)


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    """
    Logs every incoming request and its response with timing.
    Also handles rate limiting for POST requests.
    """
    client_ip = request.client.host if request.client else "unknown"
    method = request.method
    path = request.url.path
    query = str(request.url.query) if request.url.query else ""
    request_id = f"{client_ip}-{time.time_ns()}"

    logger.info(
        f">> {method} {path}{'?' + query if query else ''} "
        f"[client={client_ip}] [req_id={request_id}]"
    )

    # ── Rate limit check for POST ──────────────────────────────
    if method == "POST":
        now = time.time()
        window = 60
        rate_limit_store[client_ip] = [
            t for t in rate_limit_store[client_ip] if now - t < window
        ]
        if len(rate_limit_store[client_ip]) >= MAX_REQUESTS_PER_MINUTE:
            logger.warning(f"[!] Rate limit exceeded for {client_ip} on {path}")
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Rate limit exceeded",
                    "detail": f"Maximum {MAX_REQUESTS_PER_MINUTE} requests per minute.",
                },
            )
        rate_limit_store[client_ip].append(now)

    # ── Execute request and log result ─────────────────────────
    start = time.time()
    try:
        response = await call_next(request)
    except Exception as exc:
        elapsed = round(time.time() - start, 3)
        logger.error(
            f"[X] {method} {path} -- UNHANDLED EXCEPTION after {elapsed}s "
            f"[req_id={request_id}]\n{traceback.format_exc()}"
        )
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error", "detail": str(exc)},
        )

    elapsed = round(time.time() - start, 3)
    status = response.status_code
    level = logging.WARNING if status >= 400 else logging.INFO
    symbol = "[OK]" if status < 400 else "[FAIL]"

    logger.log(
        level,
        f"<< {symbol} {method} {path} -- {status} in {elapsed}s "
        f"[req_id={request_id}]",
    )

    return response


# ── Global exception handler ──────────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Catch-all for any unhandled exceptions.
    Logs full traceback so errors are NEVER silent.
    """
    logger.error(
        f"[!!] Unhandled exception on {request.method} {request.url.path}:\n"
        f"  Type: {type(exc).__name__}\n"
        f"  Message: {exc}\n"
        f"  Traceback:\n{traceback.format_exc()}"
    )
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc),
            "type": type(exc).__name__,
        },
    )


# ── Import and include routers ─────────────────────────────────────
from api.routers.auth import router as auth_router
from api.routers.playlist import router as playlist_router
from api.routers.chat import router as chat_router
from api.routers.notes import router as notes_router
from api.routers.flashcards import router as flashcards_router
from api.routers.quiz import router as quiz_router
from api.routers.export import router as export_router

app.include_router(auth_router)
app.include_router(playlist_router)
app.include_router(chat_router)
app.include_router(notes_router)
app.include_router(flashcards_router)
app.include_router(quiz_router)
app.include_router(export_router)


# ── Prerequisite status (populated at startup) ────────────────────
_prerequisites: dict[str, bool] = {}


@app.on_event("startup")
async def startup_event():
    """Initialize database, check prerequisites, and pre-load models."""
    global _prerequisites
    logger.info("Starting Ytutor AI...")

    # Initialize database tables
    from db.database import init_db
    await init_db()
    logger.info("Database initialized")

    # Check FFmpeg + Node.js prerequisites
    from ingestion.audio_downloader import check_prerequisites
    _prerequisites = await asyncio.to_thread(check_prerequisites)
    if not _prerequisites.get("ffmpeg"):
        logger.warning("⚠️  FFmpeg not found — Whisper transcription will fail!")
    if not _prerequisites.get("node"):
        logger.warning("⚠️  Node.js not found — yt-dlp may fail on modern YouTube pages!")

    # Pre-load embedding model in background
    logger.info("Scheduling model pre-load...")

    def preload():
        try:
            from ingestion.embedder import get_model
            get_model()
            logger.info("Embedding model pre-loaded!")
        except Exception as e:
            logger.error(f"Failed to pre-load model: {e}")

    asyncio.create_task(asyncio.to_thread(preload))


# ── Health endpoint ────────────────────────────────────────────────
@app.get("/api/health")
async def health():
    """Health check endpoint with prerequisite status."""
    try:
        model_loaded = False
        try:
            from ingestion.embedder import get_model
            get_model()
            model_loaded = True
        except Exception:
            pass

        # Determine overall health
        ffmpeg_ok = _prerequisites.get("ffmpeg", False)
        node_ok = _prerequisites.get("node", False)
        overall = "ok" if (model_loaded and ffmpeg_ok) else "degraded"

        return {
            "status": overall,
            "service": "Ytutor AI",
            "model_loaded": model_loaded,
            "prerequisites": {
                "ffmpeg": ffmpeg_ok,
                "node": node_ok,
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        return {
            "status": "degraded",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


# ── Root endpoint ─────────────────────────────────────────────────
@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Ytutor AI API",
        "docs": "/docs",
        "health": "/api/health",
        "version": "1.0.0",
    }
