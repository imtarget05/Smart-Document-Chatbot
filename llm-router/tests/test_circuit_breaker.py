import asyncio
import json

import httpx
import pytest

from app.config import Settings
from app.models import ChatRequest, RouteDecision, RoutingContext
from app.providers import CloudflareProvider, ProviderError

CB_SETTINGS = Settings(
    cloudflare_account_id="acct-1",
    cloudflare_api_token="token-1",
    circuit_failure_threshold=3,
    circuit_open_seconds=30.0,
    cloudflare_timeout_seconds=5.0,
)


def _request() -> ChatRequest:
    return ChatRequest(
        messages=[{"role": "user", "content": "Hello"}],
        stream=False,
        routing=RoutingContext(task_type="general", request_id="req-x"),
    )


def _decision() -> RouteDecision:
    return RouteDecision(
        provider="cloudflare",
        model=CB_SETTINGS.cloudflare_chat_model,
        reason="test",
        task_type="general",
    )


def _provider(handler) -> CloudflareProvider:
    transport = httpx.MockTransport(lambda request: handler(request))
    return CloudflareProvider(CB_SETTINGS, httpx.AsyncClient(transport=transport))


def _fail_handler(request) -> httpx.Response:
    return httpx.Response(503, json={"error": "overloaded"})


def _ok_handler(request) -> httpx.Response:
    return httpx.Response(
        200, json={"success": True, "result": {"response": "hello"}}
    )


def test_circuit_opens_after_threshold_and_fails_fast():
    calls = {"n": 0}

    def handler(request):
        calls["n"] += 1
        return httpx.Response(503, json={})

    provider = _provider(handler)

    async def run():
        for _ in range(CB_SETTINGS.circuit_failure_threshold):
            with pytest.raises(ProviderError):
                await provider.chat(_request(), _decision(), "req-x")

    asyncio.run(run())

    assert provider.circuit_open
    assert provider._consecutive_failures == CB_SETTINGS.circuit_failure_threshold

    # While open, no request reaches the provider at all.
    async def run_open():
        with pytest.raises(ProviderError, match="cloudflare_circuit_open"):
            await provider.chat(_request(), _decision(), "req-x")

    asyncio.run(run_open())
    assert calls["n"] == CB_SETTINGS.circuit_failure_threshold


def test_success_resets_failure_count():
    flip = {"fail": True}
    provider = _provider(lambda request: _fail_handler(request) if flip["fail"] else _ok_handler(request))

    async def run():
        with pytest.raises(ProviderError):
            await provider.chat(_request(), _decision(), "req-x")
        flip["fail"] = False
        await provider.chat(_request(), _decision(), "req-x")

    asyncio.run(run())
    assert provider._consecutive_failures == 0
    assert not provider.circuit_open


def test_embeddings_share_the_breaker_state():
    provider = _provider(_fail_handler)

    async def run():
        for _ in range(CB_SETTINGS.circuit_failure_threshold):
            with pytest.raises(ProviderError):
                await provider.embeddings({"prompt": "hello"})

    asyncio.run(run())
    assert provider.circuit_open


def test_half_open_trial_after_open_window(monkeypatch):
    provider = _provider(_fail_handler)

    async def run_failures():
        for _ in range(CB_SETTINGS.circuit_failure_threshold):
            with pytest.raises(ProviderError):
                await provider.chat(_request(), _decision(), "req-x")

    asyncio.run(run_failures())
    assert provider.circuit_open

    # Simulate the open window elapsing.
    provider._open_until -= CB_SETTINGS.circuit_open_seconds + 1.0
    assert not provider.circuit_open

    provider.client = httpx.AsyncClient(
        transport=httpx.MockTransport(lambda request: _ok_handler(request))
    )

    async def run_recover():
        response = await provider.chat(_request(), _decision(), "req-x")
        assert response["message"]["content"] == "hello"

    asyncio.run(run_recover())
    assert not provider.circuit_open
