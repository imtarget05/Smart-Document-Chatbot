import asyncio
import json
from collections.abc import AsyncIterator
from typing import Any

import pytest

from app.config import Settings
from app.models import ChatRequest, RouteDecision, RoutingContext
from app.providers import ProviderError
from app.service import LLMRouter


class FakeProviders:
    def __init__(self, fail_local=False):
        self.fail_local = fail_local
        self.decisions = []

    async def close(self) -> None:
        pass

    async def chat(
        self, request: ChatRequest, decision: RouteDecision, request_id: str
    ) -> dict[str, Any]:
        self.decisions.append(decision)
        if self.fail_local:
            raise ProviderError("local_timeout")
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
        if self.fail_local:
            raise ProviderError("local_timeout")
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
        local_base_url="http://local",
        chat_model_simple="qwen2.5:7b",
        chat_model_complex="qwen2.5:7b",
        local_timeout_seconds=3.0,
    )


def simple_request(stream=False):
    return ChatRequest(
        messages=[{"role": "user", "content": "Extract invoice number"}],
        stream=stream,
        routing=RoutingContext(task_type="extract_field", request_id="req-1"),
    )


def test_chat_routes_through_local_provider(settings):
    async def run():
        providers = FakeProviders()
        response = await LLMRouter(settings, providers).chat(simple_request())
        return providers, response

    providers, response = asyncio.run(run())

    assert [item.provider for item in providers.decisions] == ["local"]
    assert response["router"]["provider"] == "local"
    assert response["router"]["model"] == settings.chat_model_simple
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

    assert [item.provider for item in providers.decisions] == ["local"]
    payload = json.loads(chunks[0].decode())
    assert payload["message"]["content"] == "ok"
    assert payload["router"]["provider"] == "local"


def test_local_failure_propagates_as_provider_error(settings):
    async def run():
        providers = FakeProviders(fail_local=True)
        await LLMRouter(settings, providers).chat(simple_request())

    with pytest.raises(ProviderError):
        asyncio.run(run())


def test_stream_failure_propagates_as_provider_error(settings):
    async def run():
        providers = FakeProviders(fail_local=True)
        async for _ in LLMRouter(settings, providers).stream_chat(
            simple_request(stream=True)
        ):
            pass

    with pytest.raises(ProviderError):
        asyncio.run(run())
