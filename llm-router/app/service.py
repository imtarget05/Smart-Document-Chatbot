import json
import logging
import time
import uuid
from collections.abc import AsyncIterator

from .config import Settings
from .models import ChatRequest, RouteDecision
from .providers import ProviderClient
from .routing import choose_route


logger = logging.getLogger("llm_router")


class LLMRouter:
    def __init__(self, settings: Settings, providers: ProviderClient | None = None):
        self.settings = settings
        self.providers = providers or ProviderClient(settings)

    async def close(self) -> None:
        await self.providers.close()

    async def chat(self, request: ChatRequest) -> dict:
        request_id = request.routing.request_id or str(uuid.uuid4())
        decision = choose_route(request, self.settings)
        started = time.monotonic()
        self._log("route_decision", request_id, decision)
        response = await self.providers.chat(request, decision, request_id)
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
        started = time.monotonic()
        self._log("route_decision", request_id, decision)
        async for chunk in self.providers.stream_chat(request, decision, request_id):
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
