"""Redis-based LLM response cache.

Caches non-streaming LLM responses to avoid redundant API calls.
Uses the same Redis pattern as jobs.py (REDIS_URL env var, in-memory
fallback when Redis is unavailable).
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
from typing import Any

logger = logging.getLogger("llm_router")

REDIS_URL = os.getenv("REDIS_URL", "")
_redis = None
if REDIS_URL:
    try:
        import redis.asyncio as aioredis

        _redis = aioredis.from_url(REDIS_URL, decode_responses=True)
    except Exception:
        _redis = None

_cache: dict[str, dict[str, Any]] = {}

CACHE_KEY_PREFIX = "sdc:llm:cache:"


class ResponseCache:
    """Cache for LLM responses with hit/miss tracking."""

    def __init__(self, ttl_seconds: int = 300, enabled: bool = True) -> None:
        self._ttl = ttl_seconds
        self._enabled = enabled
        self._hits = 0
        self._misses = 0

    @staticmethod
    def make_key(
        model: str,
        messages: list[dict[str, Any]],
        temperature: float | None = None,
        top_p: float | None = None,
    ) -> str:
        """Build a deterministic cache key from request parameters."""
        key_data = json.dumps(
            {
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "top_p": top_p,
            },
            sort_keys=True,
            ensure_ascii=True,
        )
        digest = hashlib.sha256(key_data.encode()).hexdigest()
        return f"{CACHE_KEY_PREFIX}{digest}"

    async def get(self, key: str) -> dict[str, Any] | None:
        """Retrieve a cached response, or None on miss."""
        if not self._enabled:
            return None

        if _redis is not None:
            try:
                raw = await _redis.get(key)
                if raw:
                    self._hits += 1
                    return json.loads(raw)
            except Exception:
                pass

        entry = _cache.get(key)
        if entry is not None:
            self._hits += 1
            return entry

        self._misses += 1
        return None

    async def set(self, key: str, response: dict[str, Any], ttl: int | None = None) -> None:
        """Store a response in the cache."""
        if not self._enabled:
            return

        ttl = ttl or self._ttl

        if _redis is not None:
            try:
                await _redis.set(key, json.dumps(response, ensure_ascii=False), ex=ttl)
                return
            except Exception:
                pass

        _cache[key] = response

    def get_stats(self) -> dict[str, Any]:
        """Return cache hit/miss statistics."""
        total = self._hits + self._misses
        return {
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": round(self._hits / total, 4) if total > 0 else 0.0,
        }

    @property
    def enabled(self) -> bool:
        return self._enabled
