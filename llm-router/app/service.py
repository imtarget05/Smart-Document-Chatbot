import json
import logging
import time
import uuid
from collections.abc import AsyncIterator

from .config import Settings
from .models import ChatRequest, RouteDecision
from .providers import ProviderClient, ProviderError
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
        try:
            response = await self.providers.chat(request, decision, request_id)
        except ProviderError as exc:
            if decision.provider != "local":
                self._log("provider_failure", request_id, decision, error=str(exc))
                raise
            decision = self._escalation(decision, str(exc))
            self._log("route_escalation", request_id, decision)
            response = await self.providers.chat(request, decision, request_id)
        self._log(
            "route_complete", request_id, decision,
            latency_ms=round((time.monotonic() - started) * 1000, 2),
        )
        return response

    async def stream_chat(self, request: ChatRequest) -> AsyncIterator[bytes]:
        request_id = request.routing.request_id or str(uuid.uuid4())
        decision = choose_route(request, self.settings)
        started = time.monotonic()
        self._log("route_decision", request_id, decision)
        emitted = False
        try:
            async for chunk in self.providers.stream_chat(request, decision, request_id):
                emitted = True
                yield chunk
        except ProviderError as exc:
            if decision.provider != "local" or emitted:
                self._log("provider_failure", request_id, decision, error=str(exc), partial=emitted)
                raise
            decision = self._escalation(decision, str(exc))
            self._log("route_escalation", request_id, decision)
            async for chunk in self.providers.stream_chat(request, decision, request_id):
                yield chunk
        self._log(
            "route_complete", request_id, decision,
            latency_ms=round((time.monotonic() - started) * 1000, 2),
        )

    def _escalation(self, previous: RouteDecision, reason: str) -> RouteDecision:
        return RouteDecision(
            provider="anthropic",
            model=self.settings.anthropic_model,
            reason=f"escalated:{reason}",
            task_type=previous.task_type,
            escalated=True,
        )

    @staticmethod
    def _log(event: str, request_id: str, decision: RouteDecision, **fields: object) -> None:
        logger.info(json.dumps({
            "event": event,
            "request_id": request_id,
            **decision.model_dump(),
            **fields,
        }, ensure_ascii=True, separators=(",", ":")))
