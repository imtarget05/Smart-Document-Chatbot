"""
Web search tool using Tavily API.
Falls back gracefully if TAVILY_API_KEY is not configured.
"""

import asyncio
import logging
import time
from typing import Any, Dict, List

from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type, before_sleep_log

from settings import settings

logger = logging.getLogger(__name__)

# Circuit breaker for Tavily — same pattern as qdrant_tool
class _TavilyBreaker:
    def __init__(self, fail_max: int = 5, reset_timeout: float = 30.0):
        self.fail_max = fail_max
        self.reset_timeout = reset_timeout
        self._failures = 0
        self._state = "closed"
        self._opened_at = None

    def can_execute(self) -> bool:
        if self._state == "closed":
            return True
        if self._state == "open":
            if time.monotonic() - (self._opened_at or 0) >= self.reset_timeout:
                self._state = "half_open"
                self._emit()
                return True
            return False
        return True

    def _emit(self):
        try:
            from metrics import circuit_breaker_state
            m = {"closed": 0, "half_open": 1, "open": 2}.get(self._state, 0)
            circuit_breaker_state.labels(agent_id="tavily").set(m)
        except Exception:
            pass

    def record_success(self):
        self._failures = 0
        if self._state != "closed":
            self._state = "closed"
            self._emit()

    def record_failure(self):
        self._failures += 1
        try:
            from metrics import circuit_breaker_failures
            circuit_breaker_failures.labels(agent_id="tavily").inc()
        except Exception:
            pass
        if self._state == "half_open" or self._failures >= self.fail_max:
            self._state = "open"
            self._opened_at = time.monotonic()
            self._emit()
            logger.warning("Tavily circuit OPEN after %d failures", self._failures)

_tavily_breaker = _TavilyBreaker()

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=0.5, min=0.5, max=4),
    retry=retry_if_exception_type((asyncio.TimeoutError, TimeoutError, ConnectionError)),
    before_sleep=before_sleep_log(logging.getLogger(__name__), logging.WARNING),
    reraise=True,
)
async def _tavily_call(client, query: str, max_results: int):
    loop = asyncio.get_event_loop()
    # 10s timeout for the threadpool call
    return await asyncio.wait_for(
        loop.run_in_executor(
            None,
            lambda: client.search(query=query, max_results=max_results, search_depth="advanced"),
        ),
        timeout=10.0,
    )


class TavilySearch:
    async def search(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        if not settings.tavily_api_key:
            logger.warning("TAVILY_API_KEY not configured – web search skipped")
            return []
        if not _tavily_breaker.can_execute():
            logger.warning("Tavily circuit OPEN — skipping search")
            return []

        try:
            from tavily import TavilyClient

            client = TavilyClient(api_key=settings.tavily_api_key)
            results = await _tavily_call(client, query, max_results)
            _tavily_breaker.record_success()
            return results.get("results", [])
        except Exception as exc:
            _tavily_breaker.record_failure()
            logger.warning("Tavily search error: %s", exc)
            return []
