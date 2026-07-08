from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.started = True
    yield
    app.state.started = False


app = FastAPI(
    title="Engineering Intelligence Copilot API",
    version="0.1.0",
    description="FastAPI backend for engineering knowledge, document analysis, test report summarization, and 8D problem solving.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["system"])
async def health() -> dict:
    return {"status": "ok", "service": "engineering-intelligence-copilot-api"}


@app.get("/ready", tags=["system"])
async def ready() -> dict:
    return {
        "status": "ready",
        "service": "engineering-intelligence-copilot-api",
        "version": app.version,
    }


@app.get("/metrics", tags=["system"])
async def metrics() -> dict:
    return {
        "requests_total": 0,
        "documents_indexed_total": 0,
        "agent_runs_total": 0,
        "note": "placeholder metrics; replace with Prometheus exporter",
    }


app.include_router(api_router, prefix="/api/v1")