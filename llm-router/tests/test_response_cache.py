"""Tests for app/response_cache.py — Redis-backed LLM response cache."""

import asyncio
import pytest

from app.response_cache import ResponseCache, _cache


@pytest.fixture(autouse=True)
def clear_cache():
    """Clear the in-memory cache before each test."""
    _cache.clear()
    yield
    _cache.clear()


class TestMakeKey:
    def test_same_input_same_key(self):
        key1 = ResponseCache.make_key(
            model="llama-3.3",
            messages=[{"role": "user", "content": "Hello"}],
        )
        key2 = ResponseCache.make_key(
            model="llama-3.3",
            messages=[{"role": "user", "content": "Hello"}],
        )
        assert key1 == key2

    def test_different_model_different_key(self):
        key1 = ResponseCache.make_key(
            model="llama-3.3",
            messages=[{"role": "user", "content": "Hello"}],
        )
        key2 = ResponseCache.make_key(
            model="llama-3.1",
            messages=[{"role": "user", "content": "Hello"}],
        )
        assert key1 != key2

    def test_different_messages_different_key(self):
        key1 = ResponseCache.make_key(
            model="llama-3.3",
            messages=[{"role": "user", "content": "Hello"}],
        )
        key2 = ResponseCache.make_key(
            model="llama-3.3",
            messages=[{"role": "user", "content": "World"}],
        )
        assert key1 != key2

    def test_temperature_affects_key(self):
        key1 = ResponseCache.make_key(
            model="llama-3.3",
            messages=[{"role": "user", "content": "Hello"}],
            temperature=0.7,
        )
        key2 = ResponseCache.make_key(
            model="llama-3.3",
            messages=[{"role": "user", "content": "Hello"}],
            temperature=0.9,
        )
        assert key1 != key2

    def test_top_p_affects_key(self):
        key1 = ResponseCache.make_key(
            model="llama-3.3",
            messages=[{"role": "user", "content": "Hello"}],
            top_p=0.9,
        )
        key2 = ResponseCache.make_key(
            model="llama-3.3",
            messages=[{"role": "user", "content": "Hello"}],
            top_p=0.5,
        )
        assert key1 != key2

    def test_key_has_prefix(self):
        key = ResponseCache.make_key(
            model="llama-3.3",
            messages=[{"role": "user", "content": "Hello"}],
        )
        assert key.startswith("sdc:llm:cache:")

    def test_order_independent_messages(self):
        """Messages in different order should produce different keys."""
        key1 = ResponseCache.make_key(
            model="llama-3.3",
            messages=[
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi!"},
            ],
        )
        key2 = ResponseCache.make_key(
            model="llama-3.3",
            messages=[
                {"role": "assistant", "content": "Hi!"},
                {"role": "user", "content": "Hello"},
            ],
        )
        assert key1 != key2


class TestCacheGetSet:
    @pytest.mark.asyncio
    async def test_get_returns_none_on_miss(self):
        cache = ResponseCache(ttl_seconds=300)
        result = await cache.get("nonexistent-key")
        assert result is None

    @pytest.mark.asyncio
    async def test_set_then_get(self):
        cache = ResponseCache(ttl_seconds=300)
        key = ResponseCache.make_key("model", [{"role": "user", "content": "Hi"}])
        response = {"content": "Hello!", "model": "llama-3.3"}
        await cache.set(key, response)
        result = await cache.get(key)
        assert result == response

    @pytest.mark.asyncio
    async def test_get_stats_initial(self):
        cache = ResponseCache(ttl_seconds=300)
        stats = cache.get_stats()
        assert stats["hits"] == 0
        assert stats["misses"] == 0
        assert stats["hit_rate"] == 0.0

    @pytest.mark.asyncio
    async def test_hit_tracking(self):
        cache = ResponseCache(ttl_seconds=300)
        key = ResponseCache.make_key("model", [{"role": "user", "content": "Hi"}])
        await cache.set(key, {"content": "response"})
        await cache.get(key)  # hit
        stats = cache.get_stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 0
        assert stats["hit_rate"] == 1.0

    @pytest.mark.asyncio
    async def test_miss_tracking(self):
        cache = ResponseCache(ttl_seconds=300)
        await cache.get("nonexistent")  # miss
        stats = cache.get_stats()
        assert stats["hits"] == 0
        assert stats["misses"] == 1
        assert stats["hit_rate"] == 0.0

    @pytest.mark.asyncio
    async def test_mixed_hit_miss(self):
        cache = ResponseCache(ttl_seconds=300)
        key = ResponseCache.make_key("model", [{"role": "user", "content": "Hi"}])
        await cache.set(key, {"content": "response"})
        await cache.get(key)  # hit
        await cache.get("other")  # miss
        await cache.get(key)  # hit
        stats = cache.get_stats()
        assert stats["hits"] == 2
        assert stats["misses"] == 1
        assert stats["hit_rate"] == 0.6667


class TestCacheDisabled:
    @pytest.mark.asyncio
    async def test_get_returns_none_when_disabled(self):
        cache = ResponseCache(ttl_seconds=300, enabled=False)
        await cache.set("key", {"content": "data"})
        result = await cache.get("key")
        assert result is None

    @pytest.mark.asyncio
    async def test_set_noop_when_disabled(self):
        cache = ResponseCache(ttl_seconds=300, enabled=False)
        await cache.set("key", {"content": "data"})
        assert "key" not in _cache

    def test_enabled_property(self):
        cache = ResponseCache(enabled=True)
        assert cache.enabled is True
        cache2 = ResponseCache(enabled=False)
        assert cache2.enabled is False


class TestCacheMultipleEntries:
    @pytest.mark.asyncio
    async def test_multiple_keys_isolated(self):
        cache = ResponseCache(ttl_seconds=300)
        key1 = ResponseCache.make_key("model", [{"role": "user", "content": "A"}])
        key2 = ResponseCache.make_key("model", [{"role": "user", "content": "B"}])
        await cache.set(key1, {"content": "Response A"})
        await cache.set(key2, {"content": "Response B"})
        assert (await cache.get(key1))["content"] == "Response A"
        assert (await cache.get(key2))["content"] == "Response B"

    @pytest.mark.asyncio
    async def test_overwrite_existing_key(self):
        cache = ResponseCache(ttl_seconds=300)
        key = ResponseCache.make_key("model", [{"role": "user", "content": "Hi"}])
        await cache.set(key, {"content": "v1"})
        await cache.set(key, {"content": "v2"})
        result = await cache.get(key)
        assert result["content"] == "v2"
