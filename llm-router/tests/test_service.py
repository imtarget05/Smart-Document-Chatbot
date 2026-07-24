import json
import asyncio

import pytest

from app.config import Settings
from app.models import ChatRequest
from app.providers import ProviderError, _openai_messages
from app.service import LLMRouter


class FakeProviders:
    def __init__(self, fail_local=False):
        self.fail_local = fail_local
        self.decisions = []

    async def close(self):
        pass

    async def chat(self, request, decision, request_id):
        self.decisions.append(decision)
        if decision.provider == "local" and self.fail_local:
            raise ProviderError("local_timeout")
        return {
            "message": {"role": "assistant", "content": "ok"},
            "router": {"provider": decision.provider, "reason": decision.reason},
        }

    async def stream_chat(self, request, decision, request_id):
        self.decisions.append(decision)
        if decision.provider == "local" and self.fail_local:
            raise ProviderError("local_timeout")
        yield (json.dumps({"message": {"content": "ok"}, "done": True}) + "\n").encode()


@pytest.fixture
def settings():
    return Settings(
        local_base_url="http://local",
        local_model="llama-test",
        local_timeout_seconds=3.0,
        anthropic_api_key="test",
        anthropic_model="claude-test",
        openai_api_key="test",
        vision_model="gpt-test",
    )


def simple_request(stream=False):
    return ChatRequest(
        messages=[{"role": "user", "content": "Extract invoice number"}],
        stream=stream,
        routing={"task_type": "extract_field", "request_id": "req-1"},
    )


def test_local_timeout_escalates_to_claude(settings):
    async def run():
        providers = FakeProviders(fail_local=True)
        response = await LLMRouter(settings, providers).chat(simple_request())
        return providers, response

    providers, response = asyncio.run(run())

    assert [item.provider for item in providers.decisions] == ["local", "anthropic"]
    assert providers.decisions[1].reason == "escalated:local_timeout"
    assert response["router"]["provider"] == "anthropic"


def test_stream_timeout_before_first_chunk_escalates(settings):
    async def run():
        providers = FakeProviders(fail_local=True)
        chunks = [
            chunk
            async for chunk in LLMRouter(settings, providers).stream_chat(
                simple_request(stream=True)
            )
        ]
        return providers, chunks

    providers, chunks = asyncio.run(run())

    assert [item.provider for item in providers.decisions] == ["local", "anthropic"]
    assert b'"content": "ok"' in chunks[0]


def test_openai_payload_includes_structured_attachment():
    request = ChatRequest(
        messages=[{"role": "user", "content": "Read the invoice"}],
        routing={
            "attachments": [
                {
                    "filename": "invoice.png",
                    "content_type": "image/png",
                    "data": "aW1hZ2U=",
                }
            ]
        },
    )

    messages = _openai_messages(request.messages, request.routing.attachments)

    assert messages[0]["content"][1] == {
        "type": "image_url",
        "image_url": {"url": "data:image/png;base64,aW1hZ2U="},
    }


def test_input_image_part_is_normalized_for_chat_completions():
    request = ChatRequest(
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_image",
                        "image_url": "https://example.test/scan.png",
                    }
                ],
            }
        ]
    )

    messages = _openai_messages(request.messages)

    assert messages[0]["content"] == [
        {
            "type": "image_url",
            "image_url": {"url": "https://example.test/scan.png"},
        }
    ]
