import json
import logging
import time
import uuid
from collections.abc import AsyncIterator

from .config import Settings
from .models import ChatRequest, RouteDecision
from .providers import CloudflareProvider, LocalOllamaProvider, ProviderLike
from .routing import choose_route


logger = logging.getLogger("llm_router")


class LLMRouter:
    """Local-first routing with NO mid-request fallback (Decision 2026-08-26).

    - LocalOllamaProvider enabled AND healthy → served locally (model the user
      pulled themselves, e.g. qwen3:8b via `ollama pull`).
    - Otherwise → Cloudflare. If Cloudflare then fails, the request fails —
      it is never silently retried on the other side, so latency/behaviour
      stays predictable and each provider's errors stay attributable.
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

    async def close(self) -> None:
        await self.providers.close()
        await self.local.close()

    async def _active(self) -> ProviderLike:
        if await self.local.is_available():
            return self.local
        return self.providers

    async def chat(self, request: ChatRequest) -> dict:
        request_id = request.routing.request_id or str(uuid.uuid4())
        decision = choose_route(request, self.settings)
        active = await self._active()
        started = time.monotonic()
        self._log("route_decision", request_id, decision,
                  backend="local_ollama" if active is self.local else "cloudflare")
        response = await active.chat(request, decision, request_id)
        self._log(
            "route_complete",
            request_id,
            decision,
            latency_ms=round((time.monotonic() - started) * 1000, 2),
        )
        return response

    async def stream_chat(self, request: ChatRequest) -> AsyncIterator[bytes]:
        request_id = request.routing.request_id or str(uuid.uuid4())
        decision = choose_route(request, self.settings)
        active = await self._active()
        started = time.monotonic()
        self._log("route_decision", request_id, decision,
                  backend="local_ollama" if active is self.local else "cloudflare")
        async for chunk in active.stream_chat(request, decision, request_id):
            yield chunk
        self._log(
            "route_complete",
            request_id,
            decision,
            latency_ms=round((time.monotonic() - started) * 1000, 2),
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