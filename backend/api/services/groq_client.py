"""
Groq API client wrapper for Ytutor AI.

Handles communication with the Groq inference API with multi-key
failover: supports up to 4 API keys and automatically rotates to
the next key when one hits a rate limit or fails.

Key rotation strategy:
- Keys are loaded from GROQ_API_KEY, GROQ_API_KEY_2, GROQ_API_KEY_3, GROQ_API_KEY_4
- On rate limit or API error, the failing key is temporarily cooled down
- The next available key is tried automatically
- If ALL keys are exhausted, returns a user-friendly error
"""

import logging
import os
import time
import threading

from dotenv import load_dotenv
from groq import Groq, RateLimitError, APIError, APIConnectionError

load_dotenv()

logger = logging.getLogger(__name__)

# ── Configuration ──────────────────────────────────────────────────
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
MAX_TOKENS = int(os.getenv("MAX_TOKENS", 2000))
TEMPERATURE = float(os.getenv("TEMPERATURE", 0.2))

# Cooldown duration for a key after it fails (seconds)
KEY_COOLDOWN_SECONDS = int(os.getenv("KEY_COOLDOWN_SECONDS", 60))


# ── Multi-key pool ─────────────────────────────────────────────────
class GroqKeyPool:
    """
    Manages multiple Groq API keys with automatic failover.

    When a key hits a rate limit, it's cooled down for KEY_COOLDOWN_SECONDS
    and the next healthy key is used. Round-robin rotation distributes
    load across keys even when all are healthy.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._keys: list[str] = []
        self._cooldowns: dict[int, float] = {}  # key_index -> cooldown_until timestamp
        self._current_index: int = 0
        self._load_keys()

    def _load_keys(self):
        """Load API keys from environment variables."""
        key_vars = ["GROQ_API_KEY", "GROQ_API_KEY_2", "GROQ_API_KEY_3", "GROQ_API_KEY_4"]
        for var in key_vars:
            key = os.getenv(var, "").strip()
            if key and key != "your_groq_api_key_here":
                self._keys.append(key)

        if self._keys:
            logger.info(f"Groq key pool initialized with {len(self._keys)} API key(s)")
        else:
            logger.warning("No Groq API keys configured!")

    @property
    def total_keys(self) -> int:
        return len(self._keys)

    def _is_cooled_down(self, index: int) -> bool:
        """Check if a key is currently in cooldown."""
        cooldown_until = self._cooldowns.get(index, 0)
        return time.time() < cooldown_until

    def mark_failed(self, index: int):
        """Mark a key as failed — puts it in cooldown."""
        with self._lock:
            until = time.time() + KEY_COOLDOWN_SECONDS
            self._cooldowns[index] = until
            # Mask key for logging (show first 8 chars + last 4)
            key = self._keys[index]
            masked = f"{key[:8]}...{key[-4:]}" if len(key) > 12 else "***"
            logger.warning(
                f"Groq key #{index + 1} ({masked}) cooled down for "
                f"{KEY_COOLDOWN_SECONDS}s"
            )

    def get_next_client(self) -> tuple[Groq, int]:
        """
        Get the next available Groq client.

        Returns:
            Tuple of (Groq client, key_index)

        Raises:
            ValueError: If no keys are configured or all keys are in cooldown
        """
        if not self._keys:
            raise ValueError(
                "No Groq API keys configured. "
                "Please set GROQ_API_KEY in the .env file. "
                "Get a key at https://console.groq.com/"
            )

        with self._lock:
            # Try each key starting from current index
            for _ in range(len(self._keys)):
                idx = self._current_index % len(self._keys)
                self._current_index = (self._current_index + 1) % len(self._keys)

                if not self._is_cooled_down(idx):
                    return Groq(api_key=self._keys[idx]), idx

            # All keys are in cooldown — find the one that recovers soonest
            soonest_idx = min(self._cooldowns, key=self._cooldowns.get)
            wait_time = self._cooldowns[soonest_idx] - time.time()

            if wait_time > 0:
                logger.warning(
                    f"All {len(self._keys)} Groq keys are rate-limited. "
                    f"Nearest recovery in {wait_time:.0f}s"
                )

            raise ValueError(
                f"All {len(self._keys)} API keys are currently rate-limited. "
                f"Please try again in about {max(1, int(wait_time))} seconds."
            )

    def status(self) -> dict:
        """Get the current status of all keys."""
        now = time.time()
        statuses = []
        for i, key in enumerate(self._keys):
            masked = f"{key[:8]}...{key[-4:]}" if len(key) > 12 else "***"
            cooldown_until = self._cooldowns.get(i, 0)
            is_available = now >= cooldown_until
            statuses.append({
                "key": masked,
                "index": i + 1,
                "available": is_available,
                "cooldown_remaining": max(0, int(cooldown_until - now)) if not is_available else 0,
            })
        return {
            "total_keys": len(self._keys),
            "available_keys": sum(1 for s in statuses if s["available"]),
            "keys": statuses,
        }


# ── Global key pool instance ──────────────────────────────────────
_key_pool = GroqKeyPool()


def get_key_pool_status() -> dict:
    """Get the current status of the Groq API key pool."""
    return _key_pool.status()


def get_completion(system_prompt: str, user_message: str, max_tokens: int = None) -> dict:
    """
    Get a chat completion from Groq with automatic key failover.

    Tries each available API key. If a key hits a rate limit, it's
    cooled down and the next key is tried automatically.

    Args:
        system_prompt: System prompt with context
        user_message: User's question
        max_tokens: Override default max tokens

    Returns:
        Dict with 'content' (str) and 'usage' (dict) keys.
        On error, returns dict with 'error' (str) key.
    """
    tokens = max_tokens or MAX_TOKENS
    last_error = None

    # Try up to total_keys times (one attempt per key)
    for attempt in range(_key_pool.total_keys):
        try:
            client, key_idx = _key_pool.get_next_client()

            logger.info(
                f"Calling Groq ({GROQ_MODEL}) with key #{key_idx + 1} — "
                f"temp={TEMPERATURE}, max_tokens={tokens}"
            )

            response = client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                max_tokens=tokens,
                temperature=TEMPERATURE,
            )

            content = response.choices[0].message.content
            usage = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            }

            logger.info(
                f"Groq response (key #{key_idx + 1}): "
                f"{len(content)} chars, {usage['total_tokens']} tokens"
            )

            return {
                "content": content,
                "usage": usage,
            }

        except RateLimitError as e:
            logger.warning(f"Groq rate limit on key #{key_idx + 1}: {e}")
            _key_pool.mark_failed(key_idx)
            last_error = e
            continue  # Try next key

        except APIConnectionError as e:
            logger.error(f"Groq connection error on key #{key_idx + 1}: {e}")
            last_error = e
            # Connection errors aren't key-specific, don't rotate
            return {
                "error": (
                    "I'm having trouble connecting to the AI service. "
                    "Please try again in a few moments."
                )
            }

        except APIError as e:
            logger.error(f"Groq API error on key #{key_idx + 1}: {e}")
            # For 5xx server errors, try next key; for 4xx (except 429), don't
            if hasattr(e, 'status_code') and e.status_code and e.status_code >= 500:
                _key_pool.mark_failed(key_idx)
                last_error = e
                continue
            return {"error": f"An error occurred with the AI service: {str(e)}"}

        except ValueError as e:
            # All keys exhausted
            logger.error(f"Key pool exhausted: {e}")
            return {"error": str(e)}

        except Exception as e:
            logger.error(f"Unexpected error calling Groq: {e}")
            return {"error": "An unexpected error occurred. Please try again."}

    # All keys tried and failed
    logger.error(f"All {_key_pool.total_keys} Groq keys failed. Last error: {last_error}")
    return {
        "error": (
            "All API keys are currently rate-limited. "
            "Please wait a minute and try again."
        )
    }
