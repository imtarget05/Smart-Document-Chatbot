import asyncio
import json
from collections.abc import AsyncIterator
from dataclasses import replace
from typing import Any

import pytest

from app.config import Settings
from app.models import ChatRequest, RouteDecision, RoutingContext
from app.providers import ProviderError
from app.service import LLMRouter

MODEL = "@cf/meta/llama-3.3-70b-instruct-fp8-fast"


class FakeProviders:
    def __init__(self, fail=False):
        self.fail = fail
        self.decisions = []

    async def close(self) -> None:
        pass

    async def chat(
        self, request: ChatRequest, decision: RouteDecision, request_id: str
    ) -> dict[str, Any]:
        self.decisions.append(decision)
        if self.fail:
            raise ProviderError("cloudflare_timeout")
        return {
            "model": decision.model,
            "message": {"role": "assistant", "content": "ok"},
            "done": True,
            "router": {
                "provider": decision.provider,
                "model": decision.model,
                "reason": decision.reason,
                "task_type": decision.task_type,
                "request_id": request_id,
            },
        }

    async def stream_chat(
        self, request: ChatRequest, decision: RouteDecision, request_id: str
    ) -> AsyncIterator[bytes]:
        self.decisions.append(decision)
        if self.fail:
            raise ProviderError("cloudflare_timeout")
        payload = {
            "model": decision.model,
            "message": {"content": "ok"},
            "done": True,
            "router": {
                "provider": decision.provider,
                "model": decision.model,
                "reason": decision.reason,
                "task_type": decision.task_type,
                "request_id": request_id,
            },
        }
        yield (json.dumps(payload) + "\n").encode()


@pytest.fixture
def settings():
    return Settings(
        cloudflare_chat_model=MODEL,
        cloudflare_timeout_seconds=3.0,
    )


class FakeLocalProviders:
    """Fake local provider whose is_available() is always True."""

    def __init__(self):
        self.decisions = []

    async def close(self) -> None:
        pass

    async def is_available(self) -> bool:
        return True

    async def chat(
        self, request: ChatRequest, decision: RouteDecision, request_id: str
    ) -> dict[str, Any]:
        self.decisions.append(decision)
        return {
            "model": decision.model,
            "message": {"role": "assistant", "content": "local answer"},
            "done": True,
            "router": {
                "provider": decision.provider,
                "model": decision.model,
                "reason": decision.reason,
                "task_type": decision.task_type,
                "request_id": request_id,
            },
        }

    async def stream_chat(
        self, request: ChatRequest, decision: RouteDecision, request_id: str
    ) -> AsyncIterator[bytes]:
        self.decisions.append(decision)
        payload = {
            "model": decision.model,
            "message": {"content": "local answer"},
            "done": True,
            "router": {
                "provider": decision.provider,
                "model": decision.model,
                "reason": decision.reason,
                "task_type": decision.task_type,
                "request_id": request_id,
            },
        }
        yield (json.dumps(payload) + "\n").encode()


def test_chat_relabels_decision_when_local_active(settings):
    """When a local provider is active, the response envelope must name the
    local provider and model — not Cloudflare (the fix for the mislabeled
    provider bug)."""

    local = FakeLocalProviders()

    async def run():
        # Pass the fake as the `local` provider. Local is always available, so
        # the cloudflare fake is never exercised.
        router = LLMRouter(
            settings,
            providers=FakeProviders(),
            local=local,
        )
        return await router.chat(simple_request())

    response = asyncio.run(run())

    assert response["router"]["provider"] == "local_ollama"
    assert response["router"]["model"] == settings.local_ollama_model
    assert response["model"] == settings.local_ollama_model


def test_stream_relabels_decision_when_local_active(settings):
    """Streaming responses must also carry the local provider label."""

    local = FakeLocalProviders()

    async def run():
        router = LLMRouter(settings, providers=FakeProviders(), local=local)
        chunks = [
            json.loads(c)
            async for c in router.stream_chat(simple_request(stream=True))
        ]
        return chunks

    chunks = asyncio.run(run())
    assert chunks
    env = chunks[0]["router"]
    assert env["provider"] == "local_ollama"
    assert env["model"] == settings.local_ollama_model


def simple_request(stream=False):
    return ChatRequest(
        messages=[{"role": "user", "content": "Extract invoice number"}],
        stream=stream,
        routing=RoutingContext(task_type="extract_field", request_id="req-1"),
    )


def test_chat_routes_through_cloudflare_provider(settings):
    async def run():
        providers = FakeProviders()
        response = await LLMRouter(settings, providers).chat(simple_request())
        return providers, response

    providers, response = asyncio.run(run())

    assert [item.provider for item in providers.decisions] == ["cloudflare"]
    assert response["router"]["provider"] == "cloudflare"
    assert response["router"]["model"] == MODEL
    assert response["router"]["request_id"] == "req-1"


def test_stream_yields_router_metadata(settings):
    async def run():
        providers = FakeProviders()
        chunks = [
            chunk
            async for chunk in LLMRouter(settings, providers).stream_chat(
                simple_request(stream=True)
            )
        ]
        return providers, chunks

    providers, chunks = asyncio.run(run())

    assert [item.provider for item in providers.decisions] == ["cloudflare"]
    payload = json.loads(chunks[0].decode())
    assert payload["message"]["content"] == "ok"
    assert payload["router"]["provider"] == "cloudflare"


def test_cloudflare_failure_propagates_as_provider_error(settings):
    async def run():
        # Disable the (module-level, shared) response cache: a prior success
        # test may have cached the same keyed messages and would mask the
        # provider failure as a cache hit.
        no_cache = replace(settings, response_cache_enabled=False)
        providers = FakeProviders(fail=True)
        await LLMRouter(no_cache, providers).chat(simple_request())

    with pytest.raises(ProviderError):
        asyncio.run(run())


def test_stream_failure_propagates_as_provider_error(settings):
    async def run():
        # Streaming path doesn't use the cache, but disable it anyway for
        # consistency/robustness against the shared module cache.
        no_cache = replace(settings, response_cache_enabled=False)
        providers = FakeProviders(fail=True)
        async for _ in LLMRouter(no_cache, providers).stream_chat(
            simple_request(stream=True)
        ):
            pass

    with pytest.raises(ProviderError):
        asyncio.run(run())