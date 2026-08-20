import asyncio
import json
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
        self._consecutive_failures = 0
        self._open_until = 0.0

    @property
    def configured(self) -> bool:
        return bool(
            self.settings.cloudflare_account_id and self.settings.cloudflare_api_token
        )

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