import asyncio
import json
from collections.abc import AsyncIterator
from datetime import datetime, timezone
from typing import Any

import httpx

from .config import Settings
from .models import ChatRequest, RouteDecision
from .routing import route_metadata


class ProviderError(RuntimeError):
    pass


def _ollama_response(
    content: str, decision: RouteDecision, request_id: str
) -> dict[str, Any]:
    return {
        "model": decision.model,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "message": {"role": "assistant", "content": content},
        "done": True,
        "done_reason": "stop",
        "router": route_metadata(decision, request_id),
    }


class ProviderClient:
    def __init__(self, settings: Settings, client: httpx.AsyncClient | None = None):
        self.settings = settings
        self.client = client or httpx.AsyncClient()
        self._owns_client = client is None

    async def close(self) -> None:
        if self._owns_client:
            await self.client.aclose()

    async def chat(
        self, request: ChatRequest, decision: RouteDecision, request_id: str
    ) -> dict[str, Any]:
        return await self._local_chat(request, decision, request_id)

    async def stream_chat(
        self, request: ChatRequest, decision: RouteDecision, request_id: str
    ) -> AsyncIterator[bytes]:
        async for chunk in self._local_stream(request, decision, request_id):
            yield chunk

    async def embeddings(self, body: dict[str, Any]) -> dict[str, Any]:
        response = await self.client.post(
            f"{self.settings.local_base_url.rstrip('/')}/api/embeddings",
            json=body,
            timeout=self.settings.local_timeout_seconds,
        )
        response.raise_for_status()
        return response.json()

    async def _local_chat(
        self, request: ChatRequest, decision: RouteDecision, request_id: str
    ) -> dict[str, Any]:
        body = request.model_dump(exclude={"routing"}, exclude_none=True)
        body.update({"model": decision.model, "stream": False})
        try:
            async with asyncio.timeout(self.settings.local_timeout_seconds):
                response = await self.client.post(
                    f"{self.settings.local_base_url.rstrip('/')}/api/chat",
                    json=body,
                    timeout=self.settings.local_timeout_seconds,
                )
                response.raise_for_status()
                payload = response.json()
        except TimeoutError as exc:
            raise ProviderError("local_timeout") from exc
        except (httpx.HTTPError, ValueError) as exc:
            raise ProviderError(f"local_error:{type(exc).__name__}") from exc
        payload["router"] = route_metadata(decision, request_id)
        return payload

    async def _local_stream(
        self, request: ChatRequest, decision: RouteDecision, request_id: str
    ) -> AsyncIterator[bytes]:
        body = request.model_dump(exclude={"routing"}, exclude_none=True)
        body.update({"model": decision.model, "stream": True})
        try:
            async with self.client.stream(
                "POST",
                f"{self.settings.local_base_url.rstrip('/')}/api/chat",
                json=body,
                timeout=self.settings.local_timeout_seconds,
            ) as response:
                response.raise_for_status()
                lines = response.aiter_lines()
                try:
                    first = await asyncio.wait_for(
                        anext(lines), self.settings.local_timeout_seconds
                    )
                except (TimeoutError, StopAsyncIteration) as exc:
                    raise ProviderError("local_timeout") from exc
                if first:
                    yield self._decorate_ollama_line(first, decision, request_id)
                async for line in lines:
                    if line:
                        yield self._decorate_ollama_line(line, decision, request_id)
        except ProviderError:
            raise
        except httpx.HTTPError as exc:
            raise ProviderError(f"local_error:{type(exc).__name__}") from exc

    @staticmethod
    def _decorate_ollama_line(
        line: str, decision: RouteDecision, request_id: str
    ) -> bytes:
        payload = json.loads(line)
        payload["router"] = route_metadata(decision, request_id)
        return (json.dumps(payload, ensure_ascii=False) + "\n").encode()

    @staticmethod
    def _ollama_chunk(
        content: str, done: bool, decision: RouteDecision, request_id: str
    ) -> bytes:
        payload = _ollama_response(content, decision, request_id)
        payload["done"] = done
        if not done:
            payload.pop("done_reason", None)
        return (json.dumps(payload, ensure_ascii=False) + "\n").encode()
