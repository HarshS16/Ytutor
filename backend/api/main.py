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
from collections import defaultdict
from datetime import datetime, timezone

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
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
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Simple in-memory rate limiter ──────────────────────────────────
rate_limit_store: dict[str, list[float]] = defaultdict(list)


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    """Token-bucket rate limiter per IP address."""
    if request.method == "POST":
        client_ip = request.client.host if request.client else "unknown"
        now = time.time()
        window = 60

        rate_limit_store[client_ip] = [
            t for t in rate_limit_store[client_ip] if now - t < window
        ]

        if len(rate_limit_store[client_ip]) >= MAX_REQUESTS_PER_MINUTE:
            logger.warning(f"Rate limit exceeded for {client_ip}")
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Rate limit exceeded",
                    "detail": f"Maximum {MAX_REQUESTS_PER_MINUTE} requests per minute.",
                },
            )

        rate_limit_store[client_ip].append(now)

    response = await call_next(request)
    return response


# ── Import and include routers ─────────────────────────────────────
from api.routers.playlist import router as playlist_router
from api.routers.chat import router as chat_router
from api.routers.notes import router as notes_router
from api.routers.flashcards import router as flashcards_router
from api.routers.quiz import router as quiz_router
from api.routers.export import router as export_router

app.include_router(playlist_router)
app.include_router(chat_router)
app.include_router(notes_router)
app.include_router(flashcards_router)
app.include_router(quiz_router)
app.include_router(export_router)


@app.on_event("startup")
async def startup_event():
    """Initialize database and pre-load embedding model."""
    logger.info("Starting Ytutor AI...")

    # Initialize database tables
    from db.database import init_db
    await init_db()
    logger.info("Database initialized")

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
    """Health check endpoint."""
    try:
        model_loaded = False
        try:
            from ingestion.embedder import get_model
            get_model()
            model_loaded = True
        except Exception:
            pass

        return {
            "status": "ok",
            "service": "Ytutor AI",
            "model_loaded": model_loaded,
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
