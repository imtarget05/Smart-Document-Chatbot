import asyncio
import json

import httpx
import pytest

from app.config import Settings
from app.models import ChatRequest, RouteDecision, RoutingContext
from app.providers import CloudflareProvider, ProviderError

CF_SETTINGS = Settings(
    cloudflare_account_id="acct-1",
    cloudflare_api_token="token-1",
    cloudflare_chat_model="@cf/meta/llama-3.3-70b-instruct-fp8-fast",
    cloudflare_timeout_seconds=5.0,
)


def _request(stream: bool = False) -> ChatRequest:
    return ChatRequest(
        messages=[{"role": "user", "content": "Hello"}],
        stream=stream,
        routing=RoutingContext(task_type="general", request_id="req-x"),
    )


def _decision() -> RouteDecision:
    return RouteDecision(
        provider="cloudflare",
        model=CF_SETTINGS.cloudflare_chat_model,
        reason="test",
        task_type="general",
    )


def _fake_transport(factory):
    return httpx.MockTransport(lambda request: factory(request))


def test_cloudflare_chat_translates_to_ollama_shape():
    requests_seen = []

    def handler(request):
        requests_seen.append(json.loads(request.content))
        return httpx.Response(
            200,
            json={
                "success": True,
                "result": {"response": "hello from workers ai"},
            },
        )

    settings = CF_SETTINGS
    provider = CloudflareProvider(settings, httpx.AsyncClient(transport=_fake_transport(handler)))

    async def run():
        return await provider.chat(_request(), _decision(), "req-x")

    response = asyncio.run(run())
    assert requests_seen[0]["messages"][0]["content"] == "Hello"
    assert requests_seen[0]["stream"] is False
    assert response["message"]["role"] == "assistant"
    assert response["message"]["content"] == "hello from workers ai"
    assert response["done"] is True
    assert response["router"]["request_id"] == "req-x"


def test_cloudflare_stream_parses_sse():
    data = (
        'data: {"response":"Hel"}\n'
        'data: {"response":"lo\\nworld"}\n'
        "data: [DONE]\n"
    )

    def handler(request):
        return httpx.Response(200, text=data)

    provider = CloudflareProvider(
        CF_SETTINGS, httpx.AsyncClient(transport=_fake_transport(handler))
    )

    async def run():
        chunks = [
            c async for c in provider.stream_chat(_request(stream=True), _decision(), "req-x")
        ]
        return chunks

    chunks = asyncio.run(run())
    assert len(chunks) == 2
    first = json.loads(chunks[0])
    second = json.loads(chunks[1])
    assert first["message"]["content"] == "Hel"
    assert first["done"] is False
    assert second["message"]["content"] == "Lo\nworld" or second["message"]["content"] == "lo\nworld"


def test_cloudflare_stream_propagates_http_errors():
    def handler(request):
        return httpx.Response(500, text="bad gateway")

    provider = CloudflareProvider(
        CF_SETTINGS, httpx.AsyncClient(transport=_fake_transport(handler))
    )

    async def run():
        async for _ in provider.stream_chat(_request(stream=True), _decision(), "req-x"):
            pass

    with pytest.raises(ProviderError):
        asyncio.run(run())


def test_cloudflare_single_embedding():
    def handler(request):
        body = json.loads(request.content)
        assert body["text"] == "hello world"
        return httpx.Response(
            200,
            json={"success": True, "result": {"data": [[0.1, 0.2, 0.3]]}},
        )

    provider = CloudflareProvider(
        CF_SETTINGS, httpx.AsyncClient(transport=_fake_transport(handler))
    )

    async def run():
        return await provider.embeddings({"model": "x", "prompt": "hello world"})

    response = asyncio.run(run())
    assert response["embedding"] == [0.1, 0.2, 0.3]


def test_cloudflare_configured_flag():
    provider = CloudflareProvider(CF_SETTINGS)
    assert provider.configured is True

    unconfigured = CloudflareProvider(Settings(cloudflare_account_id="", cloudflare_api_token=""))
    assert unconfigured.configured is False


def test_cloudflare_empty_response_raises():
    def handler(request):
        return httpx.Response(200, json={"success": True, "result": {}})

    provider = CloudflareProvider(
        CF_SETTINGS, httpx.AsyncClient(transport=_fake_transport(handler))
    )

    async def run():
        return await provider.chat(_request(), _decision(), "req-x")

    with pytest.raises(ProviderError):
        asyncio.run(run())