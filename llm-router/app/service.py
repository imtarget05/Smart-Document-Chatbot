import json
import logging
import time
import uuid
from collections.abc import AsyncIterator
from typing import Any

from .config import Settings
from .models import ChatRequest, RouteDecision
from .prompt_compressor import compress_messages
from .providers import (
    CloudflareProvider,
    LocalLMStudioProvider,
    LocalOllamaProvider,
    ProviderLike,
    ProviderError,
    LocalProviderBusyError,
)
from .response_cache import ResponseCache
from .routing import choose_route


logger = logging.getLogger("llm_router")


class LLMRouter:
    """Local-first routing with NO mid-request fallback (Decision 2026-08-26).

    - Local LM Studio (LOCAL_LMSTUDIO_URL) enabled AND healthy → served by
      the models the user downloaded in LM Studio (default
      qwen2.5-vl-3b-instruct).
    - Else LocalOllamaProvider enabled AND healthy → served locally (model
      the user pulled themselves, e.g. qwen3:8b via `ollama pull`).
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
        lmstudio: LocalLMStudioProvider | None = None,
    ):
        self.settings = settings
        self.providers = providers or CloudflareProvider(settings)
        self.local = local or LocalOllamaProvider(settings)
        self.lmstudio = lmstudio or LocalLMStudioProvider(settings)
        self.cache = ResponseCache(
            ttl_seconds=settings.response_cache_ttl_seconds,
            enabled=settings.response_cache_enabled,
        )

    async def close(self) -> None:
        await self.providers.close()
        await self.local.close()
        await self.lmstudio.close()

    @staticmethod
    def _backend_name(active: ProviderLike, local: object, lmstudio: object) -> str:
        if active is lmstudio:
            return "local_lmstudio"
        if active is local:
            return "local_ollama"
        return "cloudflare"

    def _is_local(self, active: ProviderLike) -> bool:
        return active is self.local or active is self.lmstudio

    async def _active(self, request: ChatRequest) -> ProviderLike:
        # Hybrid-by-Classification (DEPLOYMENT CHỐT Local-First): normalize
        # classification so "CONFIDENTIAL"/"Confidential" cannot bypass the
        # cloud block and leak to public Cloudflare Workers AI.
        classification = (request.routing.classification or "").strip().lower()
        # Local tier priority: LM Studio → Ollama → Cloudflare (predictable,
        # never mid-request fallback between tiers).
        if await self.lmstudio.is_available():
            return self.lmstudio
        local_available = await self.local.is_available()

        if local_available:
            return self.local

        if classification == "confidential":
            raise ProviderError("policy_violation: Cannot route CONFIDENTIAL documents to public Cloudflare Workers AI.")
            
        return self.providers

    def _relabel_decision(
        self, decision: RouteDecision, active: ProviderLike
    ) -> RouteDecision:
        """Make the decision reflect the provider actually serving the request.

        ``choose_route`` always labels ``provider=cloudflare`` with the
        Cloudflare model (it only decides *complexity/cache*, not transport).
        When local Ollama serves instead, the response envelope and logs must
        say so — otherwise observability would claim Cloudflare handled a
        request it never touched.
        """
        if active is self.local or active is self.lmstudio:
            route = getattr(active, "model_for_task", None)
            if active is self.lmstudio:
                default_model = self.settings.local_lmstudio_model
                provider_name = "local_lmstudio"
            else:
                default_model = self.settings.local_ollama_model
                provider_name = "local_ollama"
            model = (
                route(decision.task_type)
                if callable(route)
                else default_model
            )
            return RouteDecision(
                provider=provider_name,
                model=model,
                reason=decision.reason,
                task_type=decision.task_type,
            )
        return decision

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

        active = await self._active(request)
        if self._is_local(active):
            decision = self._relabel_decision(decision, active)
        started = time.monotonic()
        self._log("route_decision", request_id, decision,
                  backend=self._backend_name(active, self.local, self.lmstudio),
                  **meta)
        try:
            # Local provider holds a concurrency slot (Semaphore max 2) for the
            # whole call; providers without slot semantics keep plain chat().
            slot_call = getattr(active, "chat_with_slot", None)
            if slot_call is not None:
                response = await slot_call(request, decision, request_id)
            else:
                response = await active.chat(request, decision, request_id)
        except LocalProviderBusyError as exc:
            # WP3 chốt lại: local busy → CHỈ classification PUBLIC được fallback
            # cloud (đúng 1 lần, không retry loop). CONFIDENTIAL → policy_violation
            # (403). Các classification khác (internal/unknown/empty) → busy lộ ra
            # ngoài để main map 503 + Retry-After, không lén đẩy cloud.
            if self._is_local(active):
                classification = (request.routing.classification or "").strip().lower()
                if classification == "confidential":
                    raise ProviderError(
                        "policy_violation: Cannot route CONFIDENTIAL documents to public Cloudflare Workers AI."
                    ) from exc
                if classification == "public":
                    active = self.providers
                    decision = self._relabel_decision(decision, active)
                    self._log("fallback_on_busy", request_id, decision, **meta)
                    response = await active.chat(request, decision, request_id)
                else:
                    raise
            else:
                raise

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
        active = await self._active(request)
        if self._is_local(active):
            decision = self._relabel_decision(decision, active)
        started = time.monotonic()
        self._log("route_decision", request_id, decision,
                  backend=self._backend_name(active, self.local, self.lmstudio),
                  **meta)
        slot_stream = getattr(active, "stream_chat_with_slot", None)
        if slot_stream is not None:
            # Hold a local concurrency slot (Semaphore max 2) for the whole stream.
            stream = slot_stream(request, decision, request_id)
        else:
            stream = active.stream_chat(request, decision, request_id)
        async for chunk in stream:
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
