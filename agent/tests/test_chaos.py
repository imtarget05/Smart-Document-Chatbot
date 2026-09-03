"""Chaos / fault injection tests (Phase3).

Verifies circuit breakers open and fallback to empty results without crash
when downstream dependencies (Qdrant, Tavily, LLM) are unavailable.
"""
import pytest

def test_qdrant_breaker_opens_and_fallback():
    from tools.qdrant_tool import _qdrant_breaker, _embed_breaker
    # reset
    _qdrant_breaker._failures = 0
    _qdrant_breaker._state = "closed"
    _qdrant_breaker._opened_at = None
    # record 5 failures -> open
    for _ in range(5):
        _qdrant_breaker.record_failure()
    assert _qdrant_breaker._state == "open"
    assert not _qdrant_breaker.can_execute()
    # half-open after timeout (fake time)
    import time
    _qdrant_breaker._opened_at = time.monotonic() - 31
    assert _qdrant_breaker.can_execute()  # half_open
    _qdrant_breaker.record_success()
    assert _qdrant_breaker._state == "closed"

@pytest.mark.asyncio
async def test_qdrant_search_fallback_on_circuit_open():
    from tools.qdrant_tool import QdrantHybridSearch, _qdrant_breaker
    import time
    # force open
    _qdrant_breaker._failures = 5
    _qdrant_breaker._state = "open"
    _qdrant_breaker._opened_at = time.monotonic()
    searcher = QdrantHybridSearch()
    result = await searcher._semantic_search("test", "docs", top_k=3)
    assert result == []  # fallback empty, no crash
    # cleanup
    _qdrant_breaker._state = "closed"
    _qdrant_breaker._failures = 0

def test_tavily_breaker_opens():
    from tools.web_search_tool import _tavily_breaker
    _tavily_breaker._failures = 0
    _tavily_breaker._state = "closed"
    for _ in range(5):
        _tavily_breaker.record_failure()
    assert _tavily_breaker._state == "open"
    _tavily_breaker._state = "closed"
    _tavily_breaker._failures = 0

@pytest.mark.asyncio
async def test_tavily_search_fallback_on_circuit_open():
    from tools.web_search_tool import TavilySearch, _tavily_breaker
    import time
    _tavily_breaker._state = "open"
    _tavily_breaker._opened_at = time.monotonic()
    # empty api key path also returns [] but we test circuit path
    # set a fake key to enter circuit check
    from settings import settings
    orig = settings.tavily_api_key
    settings.tavily_api_key = "fake-key-for-test"
    try:
        result = await TavilySearch().search("hello", max_results=2)
        assert result == []
    finally:
        settings.tavily_api_key = orig
        _tavily_breaker._state = "closed"
        _tavily_breaker._failures = 0
