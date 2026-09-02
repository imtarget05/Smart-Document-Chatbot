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


class CloudflareProvider:
    """Cloudflare Workers AI provider exposing an Ollama-compatible interface.

    The Spring Boot backend and agent service keep talking to the router as if
    it were Ollama; this class translates to the Workers AI REST API behind
    the scenes.

    A minimal circuit breaker guards every provider call: after
    ``circuit_failure_threshold`` consecutive failures the circuit opens and
    calls fail fast with ``cloudflare_circuit_open`` for ``circuit_open_seconds``
    before a trial call is allowed through again.
    """

    def __init__(self, settings: Settings, client: httpx.AsyncClient | None = None):
        self.settings = settings
        self.client = client or httpx.AsyncClient()
        self._owns_client = client is None
        self._consecutive_failures = 0
        self._open_until = 0.0

    # -- circuit breaker ---------------------------------------------------

    @property
    def circuit_open(self) -> bool:
        return time.monotonic() < self._open_until

    def _check_circuit(self) -> None:
        if self.circuit_open:
            raise ProviderError("cloudflare_circuit_open")

    def _record_success(self) -> None:
        self._consecutive_failures = 0
        self._open_until = 0.0

    def _record_failure(self) -> None:

        self._consecutive_failures += 1
        if (
            self.settings.circuit_failure_threshold > 0
            and self._consecutive_failures >= self.settings.circuit_failure_threshold
        ):
            self._open_until = time.monotonic() + self.settings.circuit_open_seconds

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
        self._check_circuit()
        body = {
            "messages": [
                {"role": m.role, "content": m.content}
                for m in request.messages
                if isinstance(m.content, str)
            ],
            "stream": False,
            **{k: request.options[k] for k in ("top_p", "temperature") if k in (request.options or {}) and isinstance(request.options[k], (int, float))},
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
        except ProviderError:
            self._record_failure()
            raise
        except TimeoutError as exc:
            self._record_failure()
            raise ProviderError("cloudflare_timeout") from exc
        except (httpx.HTTPError, ValueError) as exc:
            self._record_failure()
            raise ProviderError(f"cloudflare_error:{type(exc).__name__}") from exc

        result = payload.get("result") or {}
        content = result.get("response") or ""
        if not content:
            self._record_failure()
            raise ProviderError("cloudflare_empty_response")
        self._record_success()
        response = _ollama_response(content, decision, request_id)
        response["model"] = self.settings.cloudflare_chat_model
        return response

    async def stream_chat(
        self, request: ChatRequest, decision: RouteDecision, request_id: str
    ) -> AsyncIterator[bytes]:
        self._check_circuit()
        body = {
            "messages": [
                {"role": m.role, "content": m.content}
                for m in request.messages
                if isinstance(m.content, str)
            ],
            "stream": True,
            **{k: request.options[k] for k in ("top_p", "temperature") if k in (request.options or {}) and isinstance(request.options[k], (int, float))},
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
        except asyncio.CancelledError:
            raise
        except TimeoutError as exc:
            self._record_failure()
            raise ProviderError("cloudflare_timeout") from exc
        except httpx.HTTPError as exc:
            self._record_failure()
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
        self._check_circuit()
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
        except ProviderError:
            self._record_failure()
            raise
        except TimeoutError as exc:
            self._record_failure()
            raise ProviderError("cloudflare_timeout") from exc
        except (httpx.HTTPError, ValueError) as exc:
            self._record_failure()
            raise ProviderError(f"cloudflare_error:{type(exc).__name__}") from exc

        result = payload.get("result") or {}
        data = result.get("data") or []
        if not data:
            self._record_failure()
            raise ProviderError("cloudflare_empty_embedding")
        self._record_success()
        if isinstance(texts, str):
            return {"model": self.settings.cloudflare_embed_model, "embedding": list(data[0])}
        return {"model": self.settings.cloudflare_embed_model, "embeddings": [list(v) for v in data]}


class LocalOllamaProvider:
    """Opt-in local provider: talks to a user-run Ollama server (e.g.
    ``LOCAL_OLLAMA_URL=http://localhost:11434`` with a model pulled via
    ``ollama pull llama3.2`` (LOCAL_OLLAMA_MODEL default).

    Contract (Decision: local-first, NO mid-request auto-fallback):
    - when LOCAL_OLLAMA_URL is unset → ``available`` is False and the router
      serves everything from Cloudflare;
    - when set, availability is a cached health probe (TTL
      ``local_ollama_health_ttl_seconds``): if Ollama is not reachable the
      request goes to Cloudflare instead — never half-served by both;
    - embeddings stay on Cloudflare regardless (local embed models are out of
      scope; changing the embedding model invalidates stored vectors).

    Translates the Ollama /api/chat shape to the same Ollama-compatible
    response contract CloudflareProvider emits, so Spring Boot cannot tell
    them apart apart from the reported model name.
    """

    def __init__(self, settings: Settings, client: httpx.AsyncClient | None = None):
        self.settings = settings
        self.client = client or httpx.AsyncClient()
        self._owns_client = client is None
        self._healthy_until = 0.0

    @property
    def enabled(self) -> bool:
        return bool(self.settings.local_ollama_url)

    async def close(self) -> None:
        if self._owns_client:
            await self.client.aclose()

    async def _probe_health(self) -> bool:
        import time as _time

        now = _time.monotonic()
        if now < self._healthy_until:
            return True
        try:
            async with asyncio.timeout(2.0):
                response = await self.client.get(
                    f"{self.settings.local_ollama_url.rstrip('/')}/api/tags",
                    timeout=2.0,
                )
                healthy = response.status_code == 200
        except (httpx.HTTPError, TimeoutError):
            healthy = False
        if healthy:
            self._healthy_until = now + self.settings.local_ollama_health_ttl_seconds
        return healthy

    async def is_available(self) -> bool:
        return self.enabled and await self._probe_health()

    def _chat_body(self, request: ChatRequest, stream: bool) -> dict[str, Any]:
        messages = [
            {"role": m.role, "content": m.content}
            for m in request.messages
            if isinstance(m.content, str)
        ]
        body: dict[str, Any] = {
            "model": self.settings.local_ollama_model,
            "messages": messages,
            "stream": stream,
            "think": False,  # qwen3-style reasoning must never leak into answers
        }
        options = dict(request.options or {})
        options.setdefault("temperature", 0.3)
        options.setdefault("top_p", 0.95)
        body["options"] = options
        return body

    async def chat(
        self, request: ChatRequest, decision: RouteDecision, request_id: str
    ) -> dict[str, Any]:
        try:
            async with asyncio.timeout(self.settings.local_ollama_timeout_seconds):
                response = await self.client.post(
                    f"{self.settings.local_ollama_url.rstrip('/')}/api/chat",
                    json=self._chat_body(request, stream=False),
                    timeout=self.settings.local_ollama_timeout_seconds,
                )
                response.raise_for_status()
                payload = response.json()
        except TimeoutError as exc:
            raise ProviderError("ollama_timeout") from exc
        except (httpx.HTTPError, ValueError) as exc:
            raise ProviderError(f"ollama_error:{type(exc).__name__}") from exc

        content = ((payload.get("message") or {}).get("content")) or ""
        if not content.strip():
            raise ProviderError("ollama_empty_response")
        response = _ollama_response(content, decision, request_id)
        response["model"] = self.settings.local_ollama_model
        return response

    async def stream_chat(
        self, request: ChatRequest, decision: RouteDecision, request_id: str
    ) -> AsyncIterator[bytes]:
        try:
            async with self.client.stream(
                "POST",
                f"{self.settings.local_ollama_url.rstrip('/')}/api/chat",
                json=self._chat_body(request, stream=True),
                timeout=self.settings.local_ollama_timeout_seconds,
            ) as response:
                response.raise_for_status()
                collected_end = False
                async for raw in response.aiter_lines():
                    if not raw.strip():
                        continue
                    try:
                        chunk = json.loads(raw)
                    except ValueError:
                        continue
                    token = (chunk.get("message") or {}).get("content") or ""
                    payload = _ollama_response(token, decision, request_id)
                    payload["model"] = self.settings.local_ollama_model
                    payload["done"] = bool(chunk.get("done"))
                    if payload["done"]:
                        payload["done_reason"] = "stop"
                    else:
                        payload.pop("done_reason", None)
                    yield (json.dumps(payload, ensure_ascii=False) + "\n").encode()
                    collected_end = collected_end or bool(chunk.get("done"))
                if not collected_end:
                    raise ProviderError("ollama_stream_empty")
        except asyncio.CancelledError:
            raise
        except TimeoutError as exc:
            raise ProviderError("ollama_timeout") from exc
        except httpx.HTTPError as exc:
            raise ProviderError(f"ollama_error:{type(exc).__name__}") from exc