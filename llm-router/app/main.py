import logging
from contextlib import asynccontextmanager
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.responses import StreamingResponse

from .config import Settings, settings
from .models import ChatRequest
from .providers import ProviderError
from .service import LLMRouter


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")


def create_app(app_settings: Settings = settings, router: LLMRouter | None = None) -> FastAPI:
    service = router or LLMRouter(app_settings)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        yield
        await service.close()

    app = FastAPI(
        title="Smart Document Chatbot - LLM Router",
        version="1.0.0",
        description="Routes Ollama-compatible chat requests across local, Claude, and GPT-4o backends.",
        lifespan=lifespan,
    )
    app.state.router = service
    app.state.settings = app_settings

    def verify_internal_token(request: Request) -> None:
        expected = app_settings.internal_token
        if expected and request.headers.get("X-Internal-Token", "") != expected:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")

    @app.get("/health")
    async def health() -> dict[str, Any]:
        return {
            "status": "ok",
            "service": "llm-router",
            "providers": {
                "local": True,
                "anthropic": bool(app_settings.anthropic_api_key),
                "openai": bool(app_settings.openai_api_key),
                "nvidia": bool(app_settings.nvidia_api_key),
            },

        }

    @app.post("/api/chat", dependencies=[Depends(verify_internal_token)])
    async def chat(payload: ChatRequest):
        try:
            if payload.stream:
                return StreamingResponse(service.stream_chat(payload), media_type="application/x-ndjson")
            return await service.chat(payload)
        except ProviderError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

    @app.post("/api/embeddings", dependencies=[Depends(verify_internal_token)])
    async def embeddings(payload: dict[str, Any]):
        try:
            return await service.providers.embeddings(payload)
        except Exception as exc:
            raise HTTPException(status_code=503, detail="local_embedding_unavailable") from exc

    return app


app = create_app()
