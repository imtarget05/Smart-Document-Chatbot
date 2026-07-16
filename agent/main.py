"""
Smart Document Chatbot - Agent Service
FastAPI entrypoint for the multi-agent LangGraph orchestration layer.
Accepts requests from the Spring Boot backend (verified via INTERNAL_SERVICE_TOKEN).
"""

import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from adk_runtime import run_demo_workflow
from memory.long_term import LongTermMemory
from models import (
    AgentRequest,
    AgentResponse,
    ConnectorIngestRequest,
    ActionRequest,
    ReportRequest,
)
from settings import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# App lifespan – initialise shared resources once at startup
# ---------------------------------------------------------------------------
_workflow = None
_long_term_memory = None  # type: LongTermMemory | None
_rate_limiter = None  # Initialized in lifespan; type: rate_limiter.RateLimiter


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _workflow, _long_term_memory, _rate_limiter
    logger.info("Starting agent service …")
    try:
        from graph.workflow import build_workflow
        _workflow = build_workflow()
    except Exception as exc:
        logger.warning("LangGraph workflow unavailable, continuing without it: %s", exc)
        _workflow = None
    _long_term_memory = LongTermMemory()
    await _long_term_memory.init()
    # Initialize Redis-backed rate limiter (falls back to in-memory if Redis unavailable)
    from rate_limiter import RateLimiter
    _rate_limiter = RateLimiter(settings)
    logger.info("Agent service ready.")
    yield
    logger.info("Shutting down agent service …")


app = FastAPI(
    title="Smart Document Chatbot - Agent Service",
    version="2.0.0",
    description="LangGraph multi-agent orchestration layer",
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# CORS – explicit whitelist, NOT wildcard
# ---------------------------------------------------------------------------
# This service is an internal backend-to-backend service.
# CORS is only required for direct browser access (dev/debugging).
# Production browser traffic goes through the Spring Boot backend, which
# handles its own CORS — so this list intentionally excludes prod domains
# unless AGENT_ALLOWED_ORIGINS is explicitly set.
_allowed_origins = [o.strip() for o in settings.agent_allowed_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["POST", "GET", "OPTIONS"],   # no DELETE / PUT — not needed here
    allow_headers=["Authorization", "Content-Type", "X-Internal-Token"],
)


# ---------------------------------------------------------------------------
# Middleware: request body size limit
# ---------------------------------------------------------------------------
@app.middleware("http")
async def limit_request_size(request: Request, call_next):
    """
    Reject payloads exceeding AGENT_MAX_REQUEST_BYTES (default 512 KB).
    Prevents prompt-injection via artificially large request bodies.
    """
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > settings.agent_max_request_bytes:
        logger.warning(
            "Request body too large: %s bytes from %s",
            content_length,
            request.client.host if request.client else "unknown",
        )
        return JSONResponse(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            content={"error": "Request body exceeds the maximum allowed size."},
        )
    return await call_next(request)


# ---------------------------------------------------------------------------
# Per-user rate limiter (token-bucket, in-memory)
# ---------------------------------------------------------------------------
# Keyed by user_id extracted from the verified internal token payload.
# Falls back to client IP when user_id is not available (e.g. /health).
#
# Design: sliding window — track (count, window_start) per key.
# Simple and dependency-free; replace with Redis-based slowapi for multi-replica.



def _check_rate_limit(key: str) -> bool:
    """
    Delegates to the RateLimiter instance (Redis or in-memory).
    Returns True if the request should proceed, False if rate-limited.
    """
    if _rate_limiter is None:
        return True  # Service still starting up
    return _rate_limiter.is_allowed(key)


# ---------------------------------------------------------------------------
# Security – shared secret injected by Spring Boot
# ---------------------------------------------------------------------------
def verify_internal_token(request: Request):
    token = request.headers.get("X-Internal-Token", "")
    if token != settings.internal_service_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")


def verify_and_rate_limit(request: Request):
    """
    Combined dependency: verify internal token, then enforce per-IP rate limit.
    Applied to all LLM-backed endpoints (expensive operations).
    """
    verify_internal_token(request)
    # Use forwarded IP if behind a trusted proxy, else direct client IP
    client_ip = (
        request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
        or (request.client.host if request.client else "unknown")
    )
    if not _check_rate_limit(client_ip):
        logger.warning("Agent rate limit exceeded for IP: %s path: %s", client_ip, request.url.path)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Maximum {settings.agent_rate_limit_rpm} requests per minute.",
            headers={"Retry-After": "60"},
        )


# ---------------------------------------------------------------------------
# Health (no auth required — used by Docker healthcheck + LB probes)
# ---------------------------------------------------------------------------
@app.get("/health")
async def health():
    return {"status": "ok", "service": "agent"}


# ---------------------------------------------------------------------------
# Phase 2 – Main agent endpoint (Orchestrator decides which sub-agent to use)
# ---------------------------------------------------------------------------
@app.post("/agent/invoke", response_model=AgentResponse, dependencies=[Depends(verify_and_rate_limit)])
async def invoke_agent(req: AgentRequest):
    """
    Receives a user query from Spring Boot, runs the LangGraph orchestration
    workflow and returns a structured AgentResponse.
    """
    try:
        logger.info("Agent invoke: session=%s user=%s query=%s", req.session_id, req.user_id, req.query[:80])
        long_term_history = []
        if _long_term_memory is not None:
            long_term_history = await _long_term_memory.get_history(
                session_id=req.session_id,
                user_id=req.user_id,
                limit=6,
            )

        if _workflow is None:
            result = {"final_answer": "ADK demo fallback is active; LangGraph workflow is unavailable in this environment.", "agent_type": "adk", "sources": [], "confidence_score": 0.0, "action_result": None, "report_path": None}
        else:
            result = await _workflow.ainvoke({
                "query": req.query,
                "session_id": req.session_id,
                "user_id": req.user_id,
                "document_ids": req.document_ids or [],
                "messages": [],
                "long_term_history": long_term_history,
                "retrieved_chunks": [],
                "confidence_score": 0.0,
                "agent_plan": "",
                "agent_type": "",
                "intent_override": req.intent_override,
                "final_answer": "",
                "sources": [],
                "action_result": None,
                "report_path": None,
                "use_web_search": req.use_web_search,
                "hybrid_search_enabled": True,
            })
        if _long_term_memory is not None:
            agent_type = result.get("agent_type", "rag")
            await _long_term_memory.save_turn(
                req.user_id,
                req.session_id,
                "user",
                req.query,
                agent_type,
            )
            await _long_term_memory.save_turn(
                req.user_id,
                req.session_id,
                "assistant",
                result.get("final_answer", ""),
                agent_type,
            )
        return AgentResponse(
            session_id=req.session_id,
            answer=result.get("final_answer", ""),
            agent_type=result.get("agent_type", "rag"),
            sources=result.get("sources", []),
            confidence_score=result.get("confidence_score", 0.0),
            action_result=result.get("action_result"),
            report_path=result.get("report_path"),
        )
    except Exception as exc:
        logger.exception("Agent invoke failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# ADK demo endpoint (day 3)
# ---------------------------------------------------------------------------
@app.post("/agent/adk/demo")
async def adk_demo(request: Request):
    payload = await request.json()
    user_request = payload.get("user_request", "")
    document_name = payload.get("document_name", "demo-document")
    if not user_request:
        raise HTTPException(status_code=400, detail="user_request is required")
    return run_demo_workflow(user_request=user_request, document_name=document_name)


# ---------------------------------------------------------------------------
# Phase 4 – Explicit report generation endpoint
# ---------------------------------------------------------------------------
@app.post("/agent/report", dependencies=[Depends(verify_and_rate_limit)])
async def generate_report(req: ReportRequest):
    from agents.report_agent import ReportAgent
    agent = ReportAgent()
    path = await agent.generate_pdf_report(
        title=req.title,
        content=req.content,
        user_id=req.user_id,
    )
    return {"report_path": path, "status": "generated"}


# ---------------------------------------------------------------------------
# Phase 4 – Action execution (email, webhook, Jira, Notion)
# ---------------------------------------------------------------------------
@app.post("/agent/action", dependencies=[Depends(verify_and_rate_limit)])
async def execute_action(req: ActionRequest):
    from agents.action_agent import ActionAgent
    agent = ActionAgent()
    result = await agent.execute(req.action_type, req.payload)
    return {"status": "ok", "result": result}


# ---------------------------------------------------------------------------
# Phase 3 – Ingest from external connector (Google Drive, Gmail, Slack)
# ---------------------------------------------------------------------------
@app.post("/agent/connector/ingest", dependencies=[Depends(verify_internal_token)])
async def connector_ingest(req: ConnectorIngestRequest):
    """
    Connector ingest is an internal data-pipeline call — does not invoke LLM,
    so uses the lighter verify_internal_token (no rate limit).
    """
    from agents.ingestion_agent import IngestionAgent

    agent = IngestionAgent()
    if req.source not in agent.supported_sources():
        raise HTTPException(
            status_code=400,
            detail=f"Unknown connector source: {req.source}. Supported: {agent.supported_sources()}",
        )

    result = await agent.ingest(source=req.source, user_id=req.user_id, params=req.params)
    return {"status": "ok", "ingested": result}
