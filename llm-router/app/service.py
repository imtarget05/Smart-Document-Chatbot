import json
import logging
import time
import uuid
from collections.abc import AsyncIterator
from typing import Any

from .config import Settings
from .models import ChatRequest, RouteDecision
from .prompt_compressor import compress_messages
from .providers import CloudflareProvider, LocalOllamaProvider, ProviderLike
from .response_cache import ResponseCache
from .routing import choose_route


logger = logging.getLogger("llm_router")


class LLMRouter:
    """Local-first routing with NO mid-request fallback (Decision 2026-08-26).

    - LocalOllamaProvider enabled AND healthy → served locally (model the user
      pulled themselves, e.g. qwen3:8b via `ollama pull`).
    - Otherwise → Cloudflare. If Cloudflare then fails, the request fails —
      it is never silently retried on the other side, so latency/behaviour
      stays predictable and each provider's errors stay attributable.

    Cost optimization features:
    - Prompt compression reduces token usage for long prompts.
    - Response cache avoids redundant API calls for identical requests.
    """

    def __init__(
        self,
        settings: Settings,
        providers: ProviderLike | None = None,
        local: LocalOllamaProvider | None = None,
    ):
        self.settings = settings
        self.providers = providers or CloudflareProvider(settings)
        self.local = local or LocalOllamaProvider(settings)
        self.cache = ResponseCache(
            ttl_seconds=settings.response_cache_ttl_seconds,
            enabled=settings.response_cache_enabled,
        )

    async def close(self) -> None:
        await self.providers.close()
        await self.local.close()

    async def _active(self) -> ProviderLike:
        if await self.local.is_available():
            return self.local
        return self.providers

    def _prepare_request(self, request: ChatRequest) -> tuple[ChatRequest, dict[str, Any]]:
        """Apply prompt compression and build cache metadata.

        Returns the (possibly compressed) request and a dict with
        compression/cache observability fields for logging.
        """
        meta: dict[str, Any] = {}

        if self.settings.prompt_compression_enabled:
            result = compress_messages(
                request.messages,
                ratio=self.settings.prompt_compression_ratio,
                min_tokens=self.settings.prompt_compression_min_tokens,
            )
            if not result.skipped:
                request = ChatRequest(
                    model=request.model,
                    messages=result.messages,
                    stream=request.stream,
                    options=request.options,
                    routing=request.routing,
                )
                meta["compression"] = {
                    "original_tokens": result.original_tokens,
                    "compressed_tokens": result.compressed_tokens,
                    "ratio": result.ratio,
                }
                logger.info("prompt_compressed", extra=meta["compression"])

        return request, meta

    def _cache_key(self, request: ChatRequest, decision: RouteDecision) -> str:
        """Build the cache key for a non-streaming request."""
        messages = [
            {"role": m.role, "content": m.content}
            for m in request.messages
            if isinstance(m.content, str)
        ]
        temperature = request.options.get("temperature") if isinstance(request.options, dict) else None
        top_p = request.options.get("top_p") if isinstance(request.options, dict) else None
        return ResponseCache.make_key(
            model=decision.model,
            messages=messages,
            temperature=float(temperature) if temperature is not None else None,
            top_p=float(top_p) if top_p is not None else None,
        )

    async def chat(self, request: ChatRequest) -> dict[str, Any]:
        request_id = request.routing.request_id or str(uuid.uuid4())
        request, meta = self._prepare_request(request)
        decision = choose_route(request, self.settings)

        # Check cache for non-streaming requests.
        if self.cache.enabled and not request.stream:
            cache_key = self._cache_key(request, decision)
            cached = await self.cache.get(cache_key)
            if cached is not None:
                meta["cache_hit"] = True
                meta["cache_stats"] = self.cache.get_stats()
                self._log("cache_hit", request_id, decision, **meta)
                return cached

        active = await self._active()
        started = time.monotonic()
        self._log("route_decision", request_id, decision,
                  backend="local_ollama" if active is self.local else "cloudflare",
                  **meta)
        response = await active.chat(request, decision, request_id)

        # Cache the response.
        if self.cache.enabled and not request.stream:
            cache_key = self._cache_key(request, decision)
            await self.cache.set(cache_key, response)
            meta["cache_stats"] = self.cache.get_stats()

        self._log(
            "route_complete",
            request_id,
            decision,
            latency_ms=round((time.monotonic() - started) * 1000, 2),
            **meta,
        )
        return response

    async def stream_chat(self, request: ChatRequest) -> AsyncIterator[bytes]:
        request_id = request.routing.request_id or str(uuid.uuid4())
        request, meta = self._prepare_request(request)
        decision = choose_route(request, self.settings)
        active = await self._active()
        started = time.monotonic()
        self._log("route_decision", request_id, decision,
                  backend="local_ollama" if active is self.local else "cloudflare",
                  **meta)
        async for chunk in active.stream_chat(request, decision, request_id):
            yield chunk
        self._log(
            "route_complete",
            request_id,
            decision,
            latency_ms=round((time.monotonic() - started) * 1000, 2),
            **meta,
        )

    @staticmethod
    def _log(
        event: str, request_id: str, decision: RouteDecision, **fields: object
    ) -> None:
        logger.info(
            json.dumps(
                {
                    "event": event,
                    "request_id": request_id,
                    **decision.model_dump(),
                    **fields,
                },
                ensure_ascii=True,
                separators=(",", ":"),
            )
        )
