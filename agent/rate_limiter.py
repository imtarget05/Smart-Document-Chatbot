"""
Redis-backed rate limiter for the Agent service.

Replaces the in-memory ``defaultdict`` implementation so that the rate
limit is enforced correctly across multiple replicas / Gunicorn workers.

Falls back gracefully to the in-memory implementation when Redis is
not reachable (e.g., local dev without Redis).

Usage
-----
Replace the ``_check_rate_limit`` call in ``main.py`` with:

    from rate_limiter import RateLimiter
    _rate_limiter = RateLimiter(settings)
    ...
    if not await _rate_limiter.is_allowed(key):
        raise HTTPException(429, ...)
"""

import logging
import time
from collections import defaultdict
from threading import Lock

logger = logging.getLogger(__name__)


class InMemoryRateLimiter:
    """Fallback in-process sliding window rate limiter."""

    def __init__(self, limit: int, window: float = 60.0) -> None:
        self._limit = limit
        self._window = window
        self._store: dict[str, tuple[int, float]] = defaultdict(lambda: (0, time.monotonic()))
        self._lock = Lock()

    def is_allowed(self, key: str) -> bool:
        now = time.monotonic()
        with self._lock:
            count, window_start = self._store[key]
            if now - window_start >= self._window:
                self._store[key] = (1, now)
                return True
            if count >= self._limit:
                return False
            self._store[key] = (count + 1, window_start)
            return True


class RedisRateLimiter:
    """
    Sliding window rate limiter backed by Redis.

    Uses a Redis sorted-set per key:
      - ZADD  → add current timestamp as member + score
      - ZREMRANGEBYSCORE → evict timestamps older than the window
      - ZCARD  → count remaining members
      - EXPIRE → auto-clean keys after window expires

    Atomic via a single pipeline (optimistic; race window < 1 ms).
    """

    def __init__(self, redis_client, limit: int, window: float = 60.0) -> None:
        self._redis = redis_client
        self._limit = limit
        self._window = window

    def is_allowed(self, key: str) -> bool:
        now = time.time()
        window_start = now - self._window
        redis_key = f"rate:{key}"

        try:
            pipe = self._redis.pipeline()
            # Remove old timestamps outside the window
            pipe.zremrangebyscore(redis_key, "-inf", window_start)
            # Add current request timestamp (unique member = timestamp:random suffix)
            pipe.zadd(redis_key, {f"{now}:{id(object())}": now})
            # Count requests in window
            pipe.zcard(redis_key)
            # Expire the key after window so Redis auto-cleans
            pipe.expire(redis_key, int(self._window) + 5)
            _, _, count, _ = pipe.execute()
            return count <= self._limit
        except Exception as exc:
            logger.warning("Redis rate-limit check failed (%s), allowing request.", exc)
            return True  # Fail open — don't block users if Redis is down


class RateLimiter:
    """
    Public interface — auto-selects Redis or in-memory backend.

    Instantiate once at startup::

        limiter = RateLimiter(settings)

    Then call::

        if not limiter.is_allowed(client_ip):
            raise HTTPException(429, ...)
    """

    def __init__(self, settings) -> None:  # settings: agent Settings pydantic model
        self._impl: RedisRateLimiter | InMemoryRateLimiter

        redis_url = getattr(settings, "redis_url", "") or ""
        limit = getattr(settings, "agent_rate_limit_rpm", 20)

        if redis_url:
            try:
                import redis

                client = redis.from_url(redis_url, decode_responses=True, socket_connect_timeout=2)
                client.ping()  # Validate connectivity at startup
                self._impl = RedisRateLimiter(client, limit=limit)
                logger.info("RateLimiter: using Redis backend (%s)", redis_url)
            except Exception as exc:
                logger.warning(
                    "RateLimiter: Redis not reachable (%s) — falling back to in-memory.", exc
                )
                self._impl = InMemoryRateLimiter(limit=limit)
        else:
            logger.info("RateLimiter: REDIS_URL not set — using in-memory backend (single-replica only).")
            self._impl = InMemoryRateLimiter(limit=limit)

    def is_allowed(self, key: str) -> bool:
        """Return True if the request should be allowed, False if rate-limited."""
        return self._impl.is_allowed(key)
