"""WP3-T1 (TDD RED): local LLM concurrency limit.

RED tests — they MUST FAIL until WP3-T2+ implements:
  - app.providers.LocalProviderBusyError
  - LocalOllamaProvider._sem / chat_with_slot (Semaphore max 2)
  - app.service fallback to cloudflare on busy (non-CONFIDENTIAL)

Do NOT touch app/ in this task.
"""

import asyncio
from typing import Any

from app.config import Settings
from app.models import ChatRequest, RouteDecision, RoutingContext
from app.providers import LocalOllamaProvider, LocalProviderBusyError
from app.service import LLMRouter

MODEL = "@cf/meta/llama-3.3-70b-instruct-fp8-fast"


def _settings() -> Settings:
    return Settings(
        cloudflare_chat_model=MODEL,
        cloudflare_timeout_seconds=3.0,
    )


def _request(classification: str = "internal") -> ChatRequest:
    return ChatRequest(
        messages=[{"role": "user", "content": "hello local"}],
        routing=RoutingContext(classification=classification, request_id="req-busy-1"),
    )


def _decision() -> RouteDecision:
    return RouteDecision(
        provider="local_ollama",
        model="qwen2.5:3b",
        reason="test",
        task_type="chat",
    )


def test_5_concurrent_max_2_running():
    """5 concurrent chat_with_slot calls: at most 2 run at the same time."""
    settings = _settings()
    provider = LocalOllamaProvider(settings)
    running = 0
    max_running = 0

    async def fake_chat(
        request: ChatRequest, decision: RouteDecision, request_id: str
    ) -> dict[str, Any]:
        nonlocal running, max_running
        running += 1
        max_running = max(max_running, running)
        await asyncio.sleep(0.05)
        running -= 1
        return {
            "model": decision.model,
            "message": {"role": "assistant", "content": "ok"},
            "done": True,
        }

    async def run() -> list[dict[str, Any]]:
        provider.chat = fake_chat  # type: ignore[method-assign]
        return await asyncio.gather(
            *[provider.chat_with_slot(_request(), _decision(), f"r{i}") for i in range(5)]
        )

    results = asyncio.run(run())
    assert len(results) == 5
    assert all(r["done"] for r in results)
    assert max_running <= 2, f"expected max 2 concurrent, saw {max_running}"


def test_busy_timeout_raises_LocalProviderBusyError():
    """With both slots occupied, the next call raises LocalProviderBusyError fast."""
    settings = _settings()
    provider = LocalOllamaProvider(settings)
    entered = 0
    entered_evt = asyncio.Event()
    release_evt = asyncio.Event()

    async def blocking_chat(
        request: ChatRequest, decision: RouteDecision, request_id: str
    ) -> dict[str, Any]:
        nonlocal entered
        entered += 1
        if entered >= 2:
            entered_evt.set()
        await release_evt.wait()
        return {
            "model": decision.model,
            "message": {"role": "assistant", "content": "ok"},
            "done": True,
        }

    async def run() -> None:
        provider.chat = blocking_chat  # type: ignore[method-assign]
        t1 = asyncio.create_task(provider.chat_with_slot(_request(), _decision(), "r1"))
        t2 = asyncio.create_task(provider.chat_with_slot(_request(), _decision(), "r2"))
        await asyncio.wait_for(entered_evt.wait(), timeout=5)
        try:
            await asyncio.wait_for(
                provider.chat_with_slot(_request(), _decision(), "busy"), timeout=5
            )
            raise AssertionError("expected LocalProviderBusyError")
        except LocalProviderBusyError:
            pass
        finally:
            release_evt.set()
            await asyncio.gather(t1, t2)

    asyncio.run(run())


def test_busy_fallback_to_cloudflare_for_nonconfidential():
    """Local busy + non-CONFIDENTIAL doc -> service falls back to cloudflare."""

    class BusyLocal:
        async def close(self) -> None:
            pass

        async def is_available(self) -> bool:
            return True

        async def chat_with_slot(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
            raise LocalProviderBusyError("local busy")

        async def chat(
            self, request: ChatRequest, decision: RouteDecision, request_id: str
        ) -> dict[str, Any]:
            return {
                "model": "local-should-not-win",
                "message": {"role": "assistant", "content": "local"},
                "done": True,
            }

        async def stream_chat(self, *args: Any, **kwargs: Any):  # pragma: no cover
            raise NotImplementedError
            yield b""

    class CloudFake:
        def __init__(self) -> None:
            self.calls = 0

        async def close(self) -> None:
            pass

        async def chat(
            self, request: ChatRequest, decision: RouteDecision, request_id: str
        ) -> dict[str, Any]:
            self.calls += 1
            return {
                "model": decision.model,
                "message": {"role": "assistant", "content": "cloud fallback"},
                "done": True,
                "router": {
                    "provider": "cloudflare",
                    "model": decision.model,
                    "reason": decision.reason,
                    "task_type": decision.task_type,
                    "request_id": request_id,
                },
            }

        async def stream_chat(self, *args: Any, **kwargs: Any):  # pragma: no cover
            raise NotImplementedError
            yield b""

    async def run() -> tuple[CloudFake, dict[str, Any]]:
        cloud = CloudFake()
        router = LLMRouter(_settings(), providers=cloud, local=BusyLocal())  # type: ignore[arg-type]
        return cloud, await router.chat(_request(classification="internal"))

    cloud, response = asyncio.run(run())
    assert cloud.calls == 1, "expected exactly one cloudflare fallback call"
    assert response["message"]["content"] == "cloud fallback"
