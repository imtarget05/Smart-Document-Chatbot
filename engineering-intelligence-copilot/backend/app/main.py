from contextlib import asynccontextmanager
import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from app.api.v1.router import api_router
from app.core.config import settings

logger = logging.getLogger(__name__)

# Prometheus metrics (issue #37 - replace placeholder with real exporter)
try:
    from prometheus_client import (
        Counter,
        Histogram,
        generate_latest,
        CONTENT_TYPE_LATEST,
    )

    REQUESTS_TOTAL = Counter(
        "eic_requests_total",
        "Total HTTP requests",
        ["method", "endpoint", "status"],
    )
    DOCUMENTS_INDEXED = Counter(
        "eic_documents_indexed_total",
        "Total documents indexed",
    )
    AGENT_RUNS = Counter(
        "eic_agent_runs_total",
        "Total agent runs",
        ["agent_type"],
    )
    REQUEST_LATENCY = Histogram(
        "eic_request_latency_seconds",
        "HTTP request latency in seconds",
        ["method", "endpoint"],
    )
    HAS_PROMETHEUS = True
    logger.info("Prometheus metrics enabled for Engineering Copilot")
except ImportError:
    HAS_PROMETHEUS = False
    logger.warning("prometheus_client not installed - /metrics endpoint disabled")


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


# Middleware to record metrics
@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    if not HAS_PROMETHEUS:
        return await call_next(request)
    import time

    start = time.time()
    response = await call_next(request)
    elapsed = time.time() - start
    REQUESTS_TOTAL.labels(
        method=request.method,
        endpoint=request.url.path,
        status=str(response.status_code),
    ).inc()
    REQUEST_LATENCY.labels(
        method=request.method,
        endpoint=request.url.path,
    ).observe(elapsed)
    return response


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
async def metrics() -> Response:
    """Prometheus metrics endpoint (issue #37 - real exporter, not placeholder)."""
    if not HAS_PROMETHEUS:
        return Response(
            content="# prometheus_client not installed",
            media_type="text/plain",
            status_code=503,
        )
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )


app.include_router(api_router, prefix="/api/v1")
