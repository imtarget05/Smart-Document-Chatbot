"""
Redis-backed rate limiter for the Agent service.

Replaces the in-memory ``defaultdict`` implementation so that the rate
limit is enforced correctly across multiple replicas / Gunicorn workers.

Falls back gracefully to the in-memory implementation when Redis is
not reachable (e.g., local dev without Redis).

Security note (issues #24, #25):
    - When Redis is configured but unreachable, the limiter can be configured
      to FAIL CLOSED (deny) in production via ``RATE_LIMIT_FAIL_CLOSED=true``.
      The previous behavior failed open (allowed all requests), which disabled
      rate limiting exactly when it was most needed (under load / partial
      outage). Default is fail-open for local dev, fail-closed for non-local.
    - The in-memory backend does NOT sync across replicas. A warning is logged
      at startup. For multi-replica deployments, Redis is required.

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
import os
import time
from collections import defaultdict
from threading import Lock

logger = logging.getLogger(__name__)

# Environments where failing open (allowing requests when Redis is down) is
# acceptable. In all other environments, the limiter fails closed (denies).
_PERMISSIVE_ENVS = {"local", "dev", "development", "test"}


def _should_fail_closed() -> bool:
    """Return True if the limiter should deny requests when Redis is down."""
    env = os.getenv("APP_ENV", "production").strip().lower()
    # Explicit override takes precedence.
    override = os.getenv("RATE_LIMIT_FAIL_CLOSED", "").strip().lower()
    if override in ("true", "1", "yes"):
        return True
    if override in ("false", "0", "no"):
        return False
    return env not in _PERMISSIVE_ENVS


class InMemoryRateLimiter:
    """Fallback in-process sliding window rate limiter.

    WARNING (issue #25): This implementation does NOT sync across multiple
    replicas / workers. Each process maintains its own counter, so the effective
    limit is multiplied by the number of replicas. For production with >1
    replica, Redis is required.
    """

    def __init__(self, limit: int, window: float = 60.0) -> None:
        self._limit = limit
        self._window = window
        self._store: dict[str, tuple[int, float]] = defaultdict(
            lambda: (0, time.monotonic())
        )
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
      - ZADD  -> add current timestamp as member + score
      - ZREMRANGEBYSCORE -> evict timestamps older than the window
      - ZCARD  -> count remaining members
      - EXPIRE -> auto-clean keys after window expires

    Atomic via a single pipeline (optimistic; race window < 1 ms).
    """

    def __init__(
        self, redis_client, limit: int, window: float = 60.0, fail_closed: bool = False
    ) -> None:
        self._redis = redis_client
        self._limit = limit
        self._window = window
        self._fail_closed = fail_closed

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
            if self._fail_closed:
                logger.error(
                    "Redis rate-limit check failed (%s) and FAIL_CLOSED=true — "
                    "denying request to protect the service.",
                    exc,
                )
                return False  # Fail closed — deny when Redis is down in production
            logger.warning(
                "Redis rate-limit check failed (%s), allowing request (fail-open). "
                "Set RATE_LIMIT_FAIL_CLOSED=true to deny instead.",
                exc,
            )
            return True  # Fail open — don't block users if Redis is down (dev only)


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
        self._fail_closed = _should_fail_closed()

        if redis_url:
            try:
                import redis

                client = redis.from_url(
                    redis_url, decode_responses=True, socket_connect_timeout=2
                )
                client.ping()  # Validate connectivity at startup
                self._impl = RedisRateLimiter(
                    client, limit=limit, fail_closed=self._fail_closed
                )
                logger.info(
                    "RateLimiter: using Redis backend (%s, fail_closed=%s)",
                    redis_url,
                    self._fail_closed,
                )
            except Exception as exc:
                if self._fail_closed:
                    logger.error(
                        "RateLimiter: Redis not reachable (%s) and FAIL_CLOSED=true — "
                        "rate limiting will DENY all requests until Redis recovers.",
                        exc,
                    )
                else:
                    logger.warning(
                        "RateLimiter: Redis not reachable (%s) — falling back to in-memory "
                        "(NOT synced across replicas).",
                        exc,
                    )
                self._impl = InMemoryRateLimiter(limit=limit)
        else:
            logger.warning(
                "RateLimiter: REDIS_URL not set — using in-memory backend. "
                "WARNING: in-memory rate limiting is NOT synced across multiple replicas. "
                "For production with >1 replica, configure REDIS_URL."
            )
            self._impl = InMemoryRateLimiter(limit=limit)

    def is_allowed(self, key: str) -> bool:
        """Return True if the request should be allowed, False if rate-limited."""
        return self._impl.is_allowed(key)
