"""
Centralized logging configuration for Ytutor AI backend.

Provides:
- Console output with timestamps, module, and level
- Rotating file log (backend/logs/ytutor.log) for persistent debug trails
- Separate error-only file log (backend/logs/errors.log)
- Configurable log level via LOG_LEVEL env var
"""

import logging
import os
import sys
from logging.handlers import RotatingFileHandler


def setup_logging():
    """
    Configure root logger with console + file handlers.

    Call this once at application startup (before any other imports that log).
    """
    log_level = os.getenv("LOG_LEVEL", "DEBUG").upper()
    log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
    os.makedirs(log_dir, exist_ok=True)

    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level, logging.DEBUG))

    # Clear any existing handlers (uvicorn reload can cause duplicates)
    root_logger.handlers.clear()

    # ── Format (ASCII-safe for Windows cp1252 consoles) ────────────
    console_fmt = (
        "%(asctime)s | %(levelname)-8s | %(name)-30s | %(message)s"
    )
    file_fmt = (
        "%(asctime)s | %(levelname)-8s | %(name)s | %(funcName)s:%(lineno)d | %(message)s"
    )

    # ── Console Handler ────────────────────────────────────────────
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, log_level, logging.DEBUG))
    console_handler.setFormatter(logging.Formatter(console_fmt))
    root_logger.addHandler(console_handler)

    # ── File Handler (all logs, rotating 5MB x 3 files) ───────────
    all_log_path = os.path.join(log_dir, "ytutor.log")
    file_handler = RotatingFileHandler(
        all_log_path, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(file_fmt))
    root_logger.addHandler(file_handler)

    # ── Error-only File Handler ────────────────────────────────────
    error_log_path = os.path.join(log_dir, "errors.log")
    error_handler = RotatingFileHandler(
        error_log_path, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(logging.Formatter(file_fmt))
    root_logger.addHandler(error_handler)

    # ── Reduce noise from chatty libraries ─────────────────────────
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("chromadb").setLevel(logging.WARNING)
    logging.getLogger("sentence_transformers").setLevel(logging.INFO)
    logging.getLogger("huggingface_hub").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("yt_dlp").setLevel(logging.WARNING)
    logging.getLogger("aiosqlite").setLevel(logging.WARNING)

    root_logger.info(
        "Logging initialized -- level=%s, console=stdout, file=%s, errors=%s",
        log_level, all_log_path, error_log_path,
    )
