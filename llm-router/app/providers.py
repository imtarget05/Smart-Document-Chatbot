import asyncio
import json
import time
from collections.abc import AsyncIterator
from datetime import datetime, timezone
from typing import Any, Protocol

import httpx

from .config import Settings
from .models import ChatRequest, RouteDecision
from .routing import route_metadata


class ProviderError(RuntimeError):
    pass


class ProviderLike(Protocol):
    """Duck-typed client contract used by LLMRouter."""

    async def close(self) -> None: ...

    async def chat(
        self, request: ChatRequest, decision: RouteDecision, request_id: str
    ) -> dict[str, Any]: ...

    def stream_chat(
        self, request: ChatRequest, decision: RouteDecision, request_id: str
    ) -> AsyncIterator[bytes]: ...


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


class CloudflareProvider:
    """Cloudflare Workers AI provider exposing an Ollama-compatible interface.

    The Spring Boot backend and agent service keep talking to the router as if
    it were Ollama; this class translates to the Workers AI REST API behind the
    scenes.
    """

    def __init__(self, settings: Settings, client: httpx.AsyncClient | None = None):
        self.settings = settings
        self.client = client or httpx.AsyncClient()
        self._owns_client = client is None

    @property
    def _run_url(self) -> str:
        base = self.settings.cloudflare_api_base.rstrip("/")
        return f"{base}/accounts/{self.settings.cloudflare_account_id}/ai/run"

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.settings.cloudflare_api_token}",
            "Content-Type": "application/json",
        }

    async def close(self) -> None:
        if self._owns_client:
            await self.client.aclose()

    async def chat(
        self, request: ChatRequest, decision: RouteDecision, request_id: str
    ) -> dict[str, Any]:
        body = {
            "messages": [
                {"role": m.role, "content": m.content}
                for m in request.messages
                if isinstance(m.content, str)
            ],
            "stream": False,
        }
        try:
            async with asyncio.timeout(self.settings.cloudflare_timeout_seconds):
                response = await self.client.post(
                    f"{self._run_url}/{self.settings.cloudflare_chat_model}",
                    headers=self._headers(),
                    json=body,
                    timeout=self.settings.cloudflare_timeout_seconds,
                )
                response.raise_for_status()
                payload = response.json()
        except TimeoutError as exc:
            raise ProviderError("cloudflare_timeout") from exc
        except (httpx.HTTPError, ValueError) as exc:
            raise ProviderError(f"cloudflare_error:{type(exc).__name__}") from exc

        result = payload.get("result") or {}
        content = result.get("response") or ""
        if not content:
            raise ProviderError("cloudflare_empty_response")
        response = _ollama_response(content, decision, request_id)
        response["model"] = self.settings.cloudflare_chat_model
        return response

    async def stream_chat(
        self, request: ChatRequest, decision: RouteDecision, request_id: str
    ) -> AsyncIterator[bytes]:
        body = {
            "messages": [
                {"role": m.role, "content": m.content}
                for m in request.messages
                if isinstance(m.content, str)
            ],
            "stream": True,
        }
        try:
            async with self.client.stream(
                "POST",
                f"{self._run_url}/{self.settings.cloudflare_chat_model}",
                headers=self._headers(),
                json=body,
                timeout=self.settings.cloudflare_timeout_seconds,
            ) as response:
                response.raise_for_status()
                collected_end = False
                async for raw in response.aiter_lines():
                    if not raw.startswith("data:"):
                        continue
                    data = raw[len("data:"):].strip()
                    if data == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data)
                    except ValueError:
                        continue
                    token = (chunk.get("response") or "").replace("\\n", "\n")
                    payload = _ollama_response(token, decision, request_id)
                    payload["model"] = self.settings.cloudflare_chat_model
                    payload["done"] = False
                    payload.pop("done_reason", None)
                    yield (json.dumps(payload, ensure_ascii=False) + "\n").encode()
                    collected_end = True
                if not collected_end:
                    raise ProviderError("cloudflare_stream_empty")
        except TimeoutError as exc:
            raise ProviderError("cloudflare_timeout") from exc
        except asyncio.CancelledError:
            raise
        except httpx.HTTPError as exc:
            raise ProviderError(f"cloudflare_error:{type(exc).__name__}") from exc

    async def embeddings(self, body: dict[str, Any]) -> dict[str, Any]:
        """Translate Ollama-style embeddings request to Workers AI.

        Supports both single prompt ({'prompt': '...'}) and batch
        ({'input': [...]}) request shapes.
        """
        texts: list[str] | str
        if "input" in body:
            texts = [str(t) for t in body["input"]]
        else:
            texts = str(body.get("prompt", ""))
        try:
            async with asyncio.timeout(self.settings.cloudflare_timeout_seconds):
                response = await self.client.post(
                    f"{self._run_url}/{self.settings.cloudflare_embed_model}",
                    headers=self._headers(),
                    json={"text": texts},
                    timeout=self.settings.cloudflare_timeout_seconds,
                )
                response.raise_for_status()
                payload = response.json()
        except TimeoutError as exc:
            raise ProviderError("cloudflare_timeout") from exc
        except (httpx.HTTPError, ValueError) as exc:
            raise ProviderError(f"cloudflare_error:{type(exc).__name__}") from exc

        result = payload.get("result") or {}
        data = result.get("data") or []
        if not data:
            raise ProviderError("cloudflare_empty_embedding")
        if isinstance(texts, str):
            return {"model": self.settings.cloudflare_embed_model, "embedding": list(data[0])}
        return {"model": self.settings.cloudflare_embed_model, "embeddings": [list(v) for v in data]}


class FailoverProvider:
    """Routes to Cloudflare Workers AI first, falling back to local Ollama.

    Implements a simple circuit breaker: after N consecutive Cloudflare
    failures the provider stops trying Cloudflare for a cooldown window, then
    re-arms automatically.
    """

    def __init__(
        self,
        settings: Settings,
        cloudflare: CloudflareProvider | None = None,
        local: ProviderClient | None = None,
    ):
        self.settings = settings
        self.cloudflare = cloudflare or CloudflareProvider(settings)
        self.local = local or ProviderClient(settings)
        self._consecutive_failures = 0
        self._open_until = 0.0

    @property
    def uses_cloudflare(self) -> bool:
        return bool(
            self.settings.cloudflare_account_id and self.settings.cloudflare_api_token
        )

    def _cloudflare_allowed(self) -> bool:
        return self.uses_cloudflare and time.monotonic() >= self._open_until

    def _register_failure(self) -> None:
        self._consecutive_failures += 1
        if self._consecutive_failures >= self.settings.circuit_breaker_threshold:
            self._open_until = time.monotonic() + 60.0
            self._consecutive_failures = 0

    def _register_success(self) -> None:
        self._consecutive_failures = 0

    async def close(self) -> None:
        await self.cloudflare.close()
        await self.local.close()

    async def chat(
        self, request: ChatRequest, decision: RouteDecision, request_id: str
    ) -> dict[str, Any]:
        if self._cloudflare_allowed():
            try:
                result = await self.cloudflare.chat(request, decision, request_id)
                self._register_success()
                return result
            except ProviderError:
                self._register_failure()
        return await self.local.chat(request, decision, request_id)

    async def stream_chat(
        self, request: ChatRequest, decision: RouteDecision, request_id: str
    ) -> AsyncIterator[bytes]:
        if self._cloudflare_allowed():
            gen = self.cloudflare.stream_chat(request, decision, request_id)
            try:
                first = await anext(gen)
            except StopAsyncIteration:
                self._register_failure()
            except ProviderError:
                self._register_failure()
            else:
                self._register_success()
                yield first
                async for chunk in gen:
                    yield chunk
                return
        async for chunk in self.local.stream_chat(request, decision, request_id):
            yield chunk

    async def embeddings(self, body: dict[str, Any]) -> dict[str, Any]:
        if self._cloudflare_allowed():
            try:
                result = await self.cloudflare.embeddings(body)
                self._register_success()
                return result
            except ProviderError:
                self._register_failure()
        return await self.local.embeddings(body)
