"""
top_p sampling propagation tests (feature: LLM_TOP_P).

Covers the two provider paths of the llm-router:
  - LocalOllamaProvider: applies a 0.95 default when the caller omits top_p
    and keeps a caller-supplied value untouched.
  - CloudflareProvider: forwards top_p/temperature to Workers AI when the
    request supplies them and invents nothing when it does not.
"""
import asyncio
import json

import httpx
import pytest

from app.config import Settings
from app.models import ChatRequest, RouteDecision, RoutingContext
from app.providers import CloudflareProvider, LocalOllamaProvider

CF_SETTINGS = Settings(
    cloudflare_account_id="acct-1",
    cloudflare_api_token="token-1",
    cloudflare_chat_model="@cf/meta/llama-3.3-70b-instruct-fp8-fast",
    cloudflare_timeout_seconds=5.0,
)
LOCAL_SETTINGS = Settings(
    local_ollama_url="http://127.0.0.1:11434", local_ollama_model="mock-model"
)


def _request(options=None, stream=False):
    return ChatRequest(
        messages=[{"role": "user", "content": "Hello"}],
        stream=stream,
        options=options or {},
        routing=RoutingContext(task_type="general", request_id="req-x"),
    )


def _decision():
    return RouteDecision(
        provider="cloudflare",
        model=CF_SETTINGS.cloudflare_chat_model,
        reason="test",
        task_type="general",
    )


def test_local_provider_defaults_top_p_when_omitted():
    provider = LocalOllamaProvider(LOCAL_SETTINGS)
    body = provider._chat_body(_request(), stream=False)
    assert body["options"]["top_p"] == 0.95
    assert body["options"]["temperature"] == 0.3


def test_local_provider_keeps_supplied_top_p():
    provider = LocalOllamaProvider(LOCAL_SETTINGS)
    body = provider._chat_body(_request(options={"top_p": 0.8, "temperature": 0.5}), stream=False)
    assert body["options"]["top_p"] == 0.8
    assert body["options"]["temperature"] == 0.5


def test_cloudflare_forwards_top_p_when_supplied():
    seen = []

    def handler(request):
        seen.append(json.loads(request.content))
        return httpx.Response(200, json={"success": True, "result": {"response": "hello"}})

    provider = CloudflareProvider(CF_SETTINGS, httpx.AsyncClient(transport=httpx.MockTransport(handler)))

    async def run():
        return await provider.chat(_request(options={"top_p": 0.9, "temperature": 0.4}), _decision(), "req-x")

    asyncio.run(run())
    assert seen[0]["top_p"] == 0.9
    assert seen[0]["temperature"] == 0.4


def test_cloudflare_does_not_invent_top_p_when_absent():
    seen = []

    def handler(request):
        seen.append(json.loads(request.content))
        return httpx.Response(200, json={"success": True, "result": {"response": "hello"}})

    provider = CloudflareProvider(CF_SETTINGS, httpx.AsyncClient(transport=httpx.MockTransport(handler)))

    async def run():
        return await provider.chat(_request(), _decision(), "req-x")

    asyncio.run(run())
    assert "top_p" not in seen[0]
    assert "temperature" not in seen[0]
