import logging
from contextlib import asynccontextmanager
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.responses import StreamingResponse

from .config import Settings, settings
from .models import ChatRequest
from .observability import (
    enabled as langfuse_enabled,
    flush as langfuse_flush,
    generation as langfuse_generation,
    trace_id_from_headers,
    update_generation as langfuse_update_generation,
)
from .providers import CloudflareProvider, ProviderError
from .service import LLMRouter


logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s"
)


def create_app(
    app_settings: Settings = settings, router: LLMRouter | None = None
) -> FastAPI:
    service = router or LLMRouter(app_settings, CloudflareProvider(app_settings))

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        yield
        await service.close()

    app = FastAPI(
        title="Smart Document Chatbot - LLM Router",
        version="3.0.0",
        description="Routes Ollama-compatible chat requests to Cloudflare Workers AI.",
        lifespan=lifespan,
    )
    app.state.router = service
    app.state.settings = app_settings

    def verify_internal_token(request: Request) -> None:
        expected = app_settings.internal_token
        if expected and request.headers.get("X-Internal-Token", "") != expected:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized"
            )

    @app.get("/health")
    async def health() -> dict[str, Any]:
        return {
            "status": "ok",
            "service": "llm-router",
            "providers": {
                "cloudflare": getattr(
                    service.providers, "configured", False
                ),
            },
        }

    @app.post("/api/chat", dependencies=[Depends(verify_internal_token)])
    async def chat(request: Request, payload: ChatRequest):
        trace_id = trace_id_from_headers(dict(request.headers))
        try:
            if payload.stream:
                return StreamingResponse(
                    service.stream_chat(payload), media_type="application/x-ndjson"
                )
            result = await service.chat(payload)
            # Join to the backend-originated trace (Phase 2 glue).
            if langfuse_enabled() and trace_id is not None:
                model = result.get("model", app_settings.cloudflare_chat_model)
                langfuse_generation(
                    trace_id, "router_generate", model,
                    input={"message_count": len(payload.messages)},
                    metadata={"stream": False},
                )
                langfuse_update_generation(
                    trace_id, "router_generate",
                    output=result.get("message", {}).get("content"),
                    metadata={"backend": "cloudflare"},
                )
                langfuse_flush()
            return result
        except ProviderError as exc:
            if langfuse_enabled() and trace_id is not None:
                langfuse_update_generation(
                    trace_id, "router_generate",
                    output=None, metadata={"error": str(exc)},
                )
                langfuse_flush()
            raise HTTPException(status_code=503, detail=str(exc)) from exc

    @app.post("/api/embeddings", dependencies=[Depends(verify_internal_token)])
    async def embeddings(request: Request, payload: dict[str, Any]):
        trace_id = trace_id_from_headers(dict(request.headers))
        try:
            result = await service.providers.embeddings(payload)
            if langfuse_enabled() and trace_id is not None:
                langfuse_generation(
                    trace_id, "router_embeddings",
                    model=app_settings.cloudflare_embed_model,
                    metadata={"stream": False},
                )
                langfuse_flush()
            return result
        except Exception as exc:
            if langfuse_enabled() and trace_id is not None:
                langfuse_update_generation(
                    trace_id, "router_embeddings",
                    output=None, metadata={"error": str(exc)},
                )
                langfuse_flush()
            raise HTTPException(
                status_code=503, detail="embedding_unavailable"
            ) from exc

    return app


app = create_app()