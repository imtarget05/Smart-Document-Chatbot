"""Cloudflare Workers AI integration test (VCR cassette).

Unit coverage for the provider lives in ``test_cloudflare.py`` with
``httpx.MockTransport`` and is intentionally left untouched. This module adds
one record/replay integration test per the ai-testing-beyond-mock skill:

- ``record_mode="once"``: replays ``tests/cassettes/cloudflare_chat.yaml``
  offline; records a fresh cassette only when none exists (requires real
  ``CLOUDFLARE_ACCOUNT_ID`` / ``CLOUDFLARE_API_TOKEN``).
- ``filter_headers=["authorization"]``: the API token never lands in the
  cassette.
- Graceful skip when ``vcrpy`` is not installed.
"""

import asyncio
from pathlib import Path

import pytest

from app.config import Settings
from app.models import ChatRequest, RouteDecision, RoutingContext
from app.providers import CloudflareProvider

vcr = pytest.importorskip("vcr")

CASSETTE_DIR = str(Path(__file__).resolve().parent / "cassettes")

test_vcr = vcr.VCR(
    cassette_library_dir=CASSETTE_DIR,
    record_mode="once",
    filter_headers=["authorization"],
    match_on=["method", "scheme", "host", "port", "path", "query"],
)

MODEL = "@cf/meta/llama-3.3-70b-instruct-fp8-fast"


def _settings() -> Settings:
    return Settings(
        cloudflare_account_id="test-account",
        cloudflare_api_token="dummy-token-for-cassette",
        cloudflare_chat_model=MODEL,
        cloudflare_timeout_seconds=5.0,
    )


def _request() -> ChatRequest:
    return ChatRequest(
        messages=[{"role": "user", "content": "Hello"}],
        routing=RoutingContext(task_type="general", request_id="req-cassette"),
    )


def _decision() -> RouteDecision:
    return RouteDecision(
        provider="cloudflare",
        model=MODEL,
        reason="cassette replay",
        task_type="general",
    )


@test_vcr.use_cassette("cloudflare_chat.yaml")
def test_cloudflare_chat_cassette_replay():
    """Replay a recorded Workers AI chat call (no MockTransport)."""

    async def run():
        settings = _settings()
        provider = CloudflareProvider(settings)
        try:
            return await provider.chat(_request(), _decision(), "req-cassette")
        finally:
            await provider.close()

    response = asyncio.run(run())
    assert response["message"]["content"] == "hello from cassette"
    assert response["message"]["role"] == "assistant"
    assert response["done"] is True
    assert response["router"]["provider"] == "cloudflare"
    assert response["router"]["request_id"] == "req-cassette"
