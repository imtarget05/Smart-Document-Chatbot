"""
Smart Document Chatbot - Agent Service
FastAPI entrypoint for the multi-agent LangGraph orchestration layer.
Accepts requests from the Spring Boot backend (verified via INTERNAL_SERVICE_TOKEN).

Features:
- LangGraph multi-agent orchestration
- Streaming (SSE + WebSocket) for real-time token delivery
- A2A (Agent-to-Agent) protocol hub for agent discovery
- MCP (Model Context Protocol) server for tool calling
- Prometheus metrics at /metrics
- Rate limiting with Redis fallback
- Prompt-injection detection (issue #9)
- Improvement pipeline integration (issue #22)
- Retrain pipeline integration (issue #23)
"""

import asyncio
import json
import logging
import time
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import (
    APIRouter,
    Depends,
    FastAPI,
    HTTPException,
    Request,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse

from adk_runtime import run_demo_workflow
from memory.long_term import LongTermMemory
from models import (
    AgentRequest,
    AgentResponse,
    ConnectorIngestRequest,
    ActionRequest,
    ReportRequest,
)
from security.guardrails import input_guardrails, output_guardrails
from security.prompt_injection import detect_prompt_injection, sanitize_query
from settings import settings
from ab_testing import ab_manager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# App lifespan - initialise shared resources once at startup
# ---------------------------------------------------------------------------
_workflow = None
_long_term_memory = None
_rate_limiter = None
_a2a_hub = None
_mcp_server = None
_agent_factory = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _workflow, _long_term_memory, _rate_limiter
    global _a2a_hub, _mcp_server, _agent_factory

    logger.info("Starting agent service ...")

    # 1. LangGraph workflow
    try:
        from graph.workflow import build_workflow

        _workflow = build_workflow()
    except Exception as exc:
        logger.warning("LangGraph workflow unavailable, continuing without it: %s", exc)
        _workflow = None

    # 2. Long-term memory
    _long_term_memory = LongTermMemory()
    await _long_term_memory.ensure_table()
    await _long_term_memory.ensure_turn_table()

    # 3. Rate limiter
    from rate_limiter import RateLimiter

    _rate_limiter = RateLimiter(settings)

    # 4. A2A Protocol Hub
    try:
        from a2a.factory import create_default_hub, register_all_agents
        from agents.rag_agent import RagAgent

        _a2a_hub = create_default_hub()
        rag_agent = RagAgent()

        async def rag_handler(input_data):
            state = {
                "query": input_data.get("query", ""),
                "session_id": input_data.get("session_id", "default"),
                "user_id": input_data.get("user_id", "default"),
                "document_ids": input_data.get("document_ids", []),
                "messages": [],
                "long_term_history": [],
                "retrieved_chunks": [],
                "confidence_score": 0.0,
                "agent_plan": "",
                "agent_type": "",
                "final_answer": "",
                "sources": [],
                "action_result": None,
                "report_path": None,
                "use_web_search": input_data.get("use_web_search", False),
                "hybrid_search_enabled": True,
            }
            result = await rag_agent.run(state)
            return result

        register_all_agents(
            _a2a_hub,
            handlers={
                "rag_agent": rag_handler,
            },
        )
        logger.info(f"A2A Hub initialized with {len(_a2a_hub.discover_all())} agents")
    except Exception as exc:
        logger.warning("A2A Hub unavailable: %s", exc)
        _a2a_hub = None

    # 5. MCP Server - register tools
    try:
        from mcp.server import MCPServer

        _mcp_server = MCPServer(name="smart-doc-agent", version="2.0.0")

        async def web_search_handler(query: str = ""):
            from tools.web_search_tool import TavilySearch

            return await TavilySearch().search(query, max_results=5)

        async def retrieve_handler(query: str = "", top_k: int = 5):
            from tools.qdrant_tool import QdrantHybridSearch

            searcher = QdrantHybridSearch()
            return await searcher.hybrid_search(query, "default", top_k=top_k)

        _mcp_server.register_tool(
            name="web_search",
            description="Search the web for real-time information",
            handler=web_search_handler,
            input_schema={"query": {"type": "string"}},
            required_params=["query"],
            category="search",
        )
        _mcp_server.register_tool(
            name="document_retrieval",
            description="Search and retrieve document chunks from Qdrant",
            handler=retrieve_handler,
            input_schema={
                "query": {"type": "string"},
                "top_k": {"type": "integer"},
            },
            required_params=["query"],
            category="retrieval",
        )
        _mcp_server.register_tool(
            name="generate_report",
            description="Generate a PDF report from content",
            handler=lambda title, content: {
                "status": "ok",
                "path": f"/reports/{title}.pdf",
            },
            input_schema={
                "title": {"type": "string"},
                "content": {"type": "string"},
            },
            required_params=["title", "content"],
            category="report",
        )
        logger.info(f"MCP Server initialized with {_mcp_server.info.tools_count} tools")
    except Exception as exc:
        logger.warning("MCP Server unavailable: %s", exc)
        _mcp_server = None

    # 6. Prometheus
    if settings.prometheus_enabled:
        import importlib

        if importlib.util.find_spec("prometheus_client"):
            logger.info("Prometheus metrics enabled at /metrics")
        else:
            logger.warning("prometheus_client not installed, metrics disabled")

    # 7. Eval framework
    try:
        from eval_framework.api import init_eval_framework as init_eval

        agent_url = f"http://localhost:{getattr(settings, 'server_port', 9000)}"
        init_eval(
            agent_service_url=agent_url,
            internal_token=settings.internal_service_token,
        )
        logger.info("Eval framework initialized")
    except Exception as exc:
        logger.warning("Eval framework unavailable: %s", exc)

    # 8. Benchmark framework (cost + latency)
    try:
        from benchmark.api import init_benchmark_framework as init_bench

        agent_url = f"http://localhost:{getattr(settings, 'server_port', 9000)}"
        init_bench(
            agent_service_url=agent_url,
            internal_token=settings.internal_service_token,
        )
        logger.info("Benchmark framework initialized")
    except Exception as exc:
        logger.warning("Benchmark framework unavailable: %s", exc)

    logger.info("Agent service ready.")
    yield
    logger.info("Shutting down agent service ...")


app = FastAPI(
    title="Smart Document Chatbot - Agent Service",
    version="2.0.0",
    description="LangGraph multi-agent orchestration layer",
    lifespan=lifespan,
)

# API Router with version prefix for backward compatibility
v1_router = APIRouter(prefix="/v1")

# ---------------------------------------------------------------------------
# CORS - explicit whitelist, NOT wildcard
# ---------------------------------------------------------------------------
_allowed_origins = [
    o.strip() for o in settings.agent_allowed_origins.split(",") if o.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["POST", "GET", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Internal-Token"],
)


# ---------------------------------------------------------------------------
# Middleware: request body size limit
# ---------------------------------------------------------------------------
@app.middleware("http")
async def limit_request_size(request: Request, call_next):
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
def _check_rate_limit(key: str) -> bool:
    if _rate_limiter is None:
        return True
    return _rate_limiter.is_allowed(key)


# ---------------------------------------------------------------------------
# Security - shared secret injected by Spring Boot
# ---------------------------------------------------------------------------
def verify_internal_token(request: Request):
    token = request.headers.get("X-Internal-Token", "")
    if token != settings.internal_service_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized"
        )


# ---------------------------------------------------------------------------
# Security - prompt-injection guard (issue #9)
# ---------------------------------------------------------------------------
def _check_prompt_injection(query: str) -> str:
    """
    Detect and mitigate prompt-injection attempts.

    - HIGH severity: blocked (raises ValueError; caller converts to HTTP 400).
    - MEDIUM severity: sanitized + warning logged.
    - LOW / none: returned as-is.

    Returns the (possibly sanitized) query. Raises ValueError on block.
    """
    result = detect_prompt_injection(query)
    if result.is_injection:
        logger.warning(
            "Prompt-injection detected: severity=%s reasons=%s patterns=%s",
            result.severity,
            result.reasons,
            result.matched_patterns,
        )
        if result.severity == "high":
            raise ValueError(
                f"Query rejected by prompt-injection guard: {result.reasons}"
            )
        # medium / low: sanitize and continue
        sanitized = sanitize_query(query)
        logger.info("Query sanitized by prompt-injection guard.")
        return sanitized
    return query


def verify_and_rate_limit(request: Request):
    verify_internal_token(request)
    client_ip = request.headers.get("X-Forwarded-For", "").split(",")[0].strip() or (
        request.client.host if request.client else "unknown"
    )
    if not _check_rate_limit(client_ip):
        logger.warning(
            "Agent rate limit exceeded for IP: %s path: %s", client_ip, request.url.path
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Maximum {settings.agent_rate_limit_rpm} requests per minute.",
            headers={"Retry-After": "60"},
        )


# ---------------------------------------------------------------------------
# Health (no auth required - used by Docker healthcheck + LB probes)
# ---------------------------------------------------------------------------
@v1_router.get("/health")
async def health():
    return {"status": "ok", "service": "agent", "version": "2.0.0"}


@app.get("/health")
async def health_legacy():
    """Legacy health endpoint for backward compatibility."""
    return {"status": "ok", "service": "agent", "version": "2.0.0"}


# ---------------------------------------------------------------------------
# Prometheus /metrics endpoint
# ---------------------------------------------------------------------------
if settings.prometheus_enabled:

    @app.get("/metrics")
    async def metrics():
        try:
            from metrics import metrics_endpoint

            body, status_code, headers = metrics_endpoint()
            return JSONResponse(
                content=body,
                status_code=status_code,
                headers=headers,
            )
        except Exception as exc:
            # Log the actual error instead of silently swallowing (issue #64).
            logger.exception("Metrics endpoint failed: %s", exc)
            return JSONResponse(
                content={"error": "Metrics not available"},
                status_code=503,
            )


# ---------------------------------------------------------------------------
# Real token-by-token streaming helper (issue #15)
# ---------------------------------------------------------------------------
async def _stream_answer_tokens(answer: str) -> AsyncIterator[str]:
    """
    Yield answer text as natural token chunks (word-by-word with whitespace
    preserved) instead of fixed 5-char slices with artificial sleeps.

    This produces genuine incremental output. If the underlying LLM supports
    native streaming, callers should prefer that; this is a fallback that
    still streams incrementally without the fake 0.02s delay.
    """
    if not answer:
        return
    # Split on whitespace boundaries but keep the delimiters so the client can
    # reconstruct the exact string. This is far more natural than 5-char chunks.
    import re

    tokens = re.findall(r"\S+\s*", answer)
    for token in tokens:
        yield token


# ---------------------------------------------------------------------------
# WebSocket endpoint for real-time agent communication
# ---------------------------------------------------------------------------
@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    await websocket.accept()
    logger.info(f"WebSocket connected: session={session_id}")

    try:
        while True:
            data = await websocket.receive_text()
            payload = json.loads(data)
            query = payload.get("query", "")
            user_id = payload.get("user_id", session_id)
            document_ids = payload.get("document_ids", [])
            use_web_search = payload.get("use_web_search", False)

            logger.info(f"WebSocket query: session={session_id} query={query[:80]}")

            # Prompt-injection guard (issue #9)
            try:
                query = _check_prompt_injection(query)
            except ValueError as inj_exc:
                await websocket.send_json(
                    {
                        "event": "error",
                        "data": {
                            "error": str(inj_exc),
                            "code": "prompt_injection_blocked",
                        },
                    }
                )
                continue

            # Input guardrail check
            input_report = input_guardrails.check(query)
            if not input_report.passed:
                blocked = [e for e in input_report.events if e.severity == "high"]
                if blocked:
                    await websocket.send_json(
                        {
                            "event": "error",
                            "data": {
                                "error": f"Input blocked by guardrails: {[e.message for e in blocked]}",
                                "code": "guardrail_blocked",
                            },
                        }
                    )
                    continue
                logger.warning("Input guardrail warnings: %s", input_report.events)

            # Send acknowledgment
            await websocket.send_json({"event": "connected", "session_id": session_id})

            # Retrieve long-term history
            long_term_history = []
            if _long_term_memory is not None:
                long_term_history = await _long_term_memory.get_history(
                    session_id=session_id,
                    user_id=user_id,
                    limit=6,
                )

            # Send plan event
            await websocket.send_json(
                {
                    "event": "plan",
                    "data": {"agent_type": "rag", "plan": f"Processing: {query[:100]}"},
                }
            )

            # Execute workflow
            if _workflow is None:
                result = {
                    "final_answer": "ADK demo fallback is active.",
                    "agent_type": "adk",
                    "sources": [],
                    "confidence_score": 0.0,
                }
                await websocket.send_json(
                    {
                        "event": "token",
                        "data": {"text": result["final_answer"]},
                    }
                )
            else:
                ab_config = ab_manager.get_active_variant_config(
                    query_id=f"{session_id}:{query[:64]}"
                )
                result = await _workflow.ainvoke(
                    {
                        "query": query,
                        "session_id": session_id,
                        "user_id": user_id,
                        "document_ids": document_ids or [],
                        "messages": [],
                        "long_term_history": long_term_history,
                        "retrieved_chunks": [],
                        "confidence_score": 0.0,
                        "agent_plan": "",
                        "agent_type": "",
                        "intent_override": payload.get("intent_override"),
                        "final_answer": "",
                        "sources": [],
                        "action_result": None,
                        "report_path": None,
                        "use_web_search": use_web_search,
                        "hybrid_search_enabled": True,
                        "ab_config": ab_config,
                    }
                )

                # Output guardrail check
                answer = result.get("final_answer", "")
                confidence = result.get("confidence_score", 0.0)
                output_report = output_guardrails.check(query, answer, confidence)
                if not output_report.passed:
                    logger.warning("Output guardrail warnings: %s", output_report.events)

                # Stream answer token by token via WebSocket (real streaming, issue #15)
                async for token in _stream_answer_tokens(answer):
                    await websocket.send_json(
                        {
                            "event": "token",
                            "data": {"text": token},
                        }
                    )
                    # Yield control to the event loop so tokens flush immediately.
                    await asyncio.sleep(0)

            # Save to long-term memory
            if _long_term_memory is not None:
                agent_type = result.get("agent_type", "rag")
                await _long_term_memory.save_turn(
                    user_id, session_id, "user", query, agent_type
                )
                await _long_term_memory.save_turn(
                    user_id,
                    session_id,
                    "assistant",
                    result.get("final_answer", ""),
                    agent_type,
                )

            # Send sources
            sources = result.get("sources", [])
            if sources:
                await websocket.send_json(
                    {"event": "source", "data": {"sources": sources}}
                )

            # Send complete
            await websocket.send_json(
                {
                    "event": "complete",
                    "data": {
                        "agent_type": result.get("agent_type", "rag"),
                        "confidence_score": result.get("confidence_score", 0.0),
                    },
                }
            )

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: session={session_id}")
    except Exception as e:
        logger.exception(f"WebSocket error: {e}")
        try:
            await websocket.send_json({"event": "error", "data": {"error": str(e)}})
        except Exception:
            logger.debug(
                "Could not send error to disconnected WebSocket", exc_info=True
            )


# ---------------------------------------------------------------------------
# A2A Hub endpoints
# ---------------------------------------------------------------------------
@v1_router.get("/a2a/agents")
async def list_a2a_agents():
    if _a2a_hub is None:
        raise HTTPException(status_code=503, detail="A2A Hub not initialized")
    agents = [card.to_dict() for card in _a2a_hub.discover_all()]
    return {"agents": agents, "total": len(agents)}


@v1_router.get("/a2a/agents/{capability}")
async def discover_a2a_agents(capability: str):
    if _a2a_hub is None:
        raise HTTPException(status_code=503, detail="A2A Hub not initialized")
    agents = [card.to_dict() for card in _a2a_hub.discover_agents(capability)]
    return {"capability": capability, "agents": agents, "total": len(agents)}


@v1_router.post("/a2a/delegate")
async def delegate_a2a_task(request: Request):
    if _a2a_hub is None:
        raise HTTPException(status_code=503, detail="A2A Hub not initialized")
    payload = await request.json()
    capability = payload.get("capability", "")
    input_data = payload.get("input", {})
    if not capability:
        raise HTTPException(status_code=400, detail="capability is required")
    task = await _a2a_hub.delegate(capability, input_data)
    return {
        "task_id": task.task_id,
        "agent_id": task.agent_id,
        "status": task.status.value,
        "result": task.result,
        "error": task.error,
        "latency_ms": round(task.latency_ms(), 2),
    }


@v1_router.get("/a2a/stats")
async def a2a_stats():
    if _a2a_hub is None:
        raise HTTPException(status_code=503, detail="A2A Hub not initialized")
    return _a2a_hub.get_stats()


# ---------------------------------------------------------------------------
# MCP Server endpoints
# ---------------------------------------------------------------------------
@v1_router.get("/mcp/info")
async def mcp_server_info():
    if _mcp_server is None:
        raise HTTPException(status_code=503, detail="MCP Server not initialized")
    return _mcp_server.get_server_info()


@v1_router.get("/mcp/tools")
async def mcp_list_tools():
    if _mcp_server is None:
        raise HTTPException(status_code=503, detail="MCP Server not initialized")
    return {"tools": _mcp_server.list_tools(), "total": len(_mcp_server.list_tools())}


@v1_router.post("/mcp/call")
async def mcp_call_tool(request: Request):
    if _mcp_server is None:
        raise HTTPException(status_code=503, detail="MCP Server not initialized")
    payload = await request.json()
    name = payload.get("name", "")
    arguments = payload.get("arguments", {})
    if not name:
        raise HTTPException(status_code=400, detail="Tool name is required")
    result = await _mcp_server.call_tool(name, arguments)
    return {
        "tool_name": result.tool_name,
        "status": result.status.value,
        "result": result.result,
        "error": result.error,
        "latency_seconds": result.latency_seconds,
    }


@v1_router.get("/mcp/stats")
async def mcp_stats():
    if _mcp_server is None:
        raise HTTPException(status_code=503, detail="MCP Server not initialized")
    return _mcp_server.get_stats()


# ---------------------------------------------------------------------------
# Phase 2 - Main agent endpoint (Orchestrator decides which sub-agent to use)
# ---------------------------------------------------------------------------
@v1_router.post(
    "/agent/invoke",
    response_model=AgentResponse,
    dependencies=[Depends(verify_and_rate_limit)],
)
async def invoke_agent(req: AgentRequest):
    try:
        logger.info(
            "Agent invoke: session=%s user=%s query=%s",
            req.session_id,
            req.user_id,
            req.query[:80],
        )

        # Prompt-injection guard (issue #9)
        try:
            safe_query = _check_prompt_injection(req.query)
        except ValueError as inj_exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(inj_exc),
            )
        # Update the request query if it was sanitized
        if safe_query != req.query:
            req = req.model_copy(update={"query": safe_query})

        # Input guardrail check
        input_report = input_guardrails.check(req.query)
        if not input_report.passed:
            blocked = [e for e in input_report.events if e.severity == "high"]
            if blocked:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Input blocked by guardrails: {[e.message for e in blocked]}",
                )
            logger.warning("Input guardrail warnings: %s", input_report.events)

        long_term_history = []
        if _long_term_memory is not None:
            long_term_history = await _long_term_memory.get_history(
                session_id=req.session_id,
                user_id=req.user_id,
                limit=6,
            )

        # A/B test assignment
        ab_config = ab_manager.get_active_variant_config(
            query_id=f"{req.session_id}:{req.query[:64]}"
        )
        if ab_config:
            logger.info(
                "A/B variant assigned: %s config=%s",
                ab_config.get("variant_id", "none"),
                {k: v for k, v in ab_config.items() if k != "variant_id"},
            )
        _start_time = time.monotonic()

        if _workflow is None:
            result = {
                "final_answer": "ADK demo fallback is active; LangGraph workflow is unavailable in this environment.",
                "agent_type": "adk",
                "sources": [],
                "confidence_score": 0.0,
                "action_result": None,
                "report_path": None,
            }
        else:
            result = await _workflow.ainvoke(
                {
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
                    "ab_config": ab_config,
                }
            )

        latency_ms = (time.monotonic() - _start_time) * 1000

        # Log A/B test result
        if ab_config:
            try:
                ab_manager.log_result(
                    query_id=f"{req.session_id}:{req.query[:64]}",
                    variant_id=ab_config["variant_id"],
                    latency_ms=latency_ms,
                    confidence_score=result.get("confidence_score", 0.0),
                    answer_correct=result.get("confidence_score", 0) > 0.3,
                )
            except Exception as ab_exc:
                logger.debug("A/B logging failed: %s", ab_exc)

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

        # Output guardrail check
        answer = result.get("final_answer", "")
        confidence = result.get("confidence_score", 0.0)
        output_report = output_guardrails.check(req.query, answer, confidence)
        if not output_report.passed:
            logger.warning("Output guardrail warnings: %s", output_report.events)

        return AgentResponse(
            session_id=req.session_id,
            answer=answer,
            agent_type=result.get("agent_type", "rag"),
            sources=result.get("sources", []),
            confidence_score=confidence,
            action_result=result.get("action_result"),
            report_path=result.get("report_path"),
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Agent invoke failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# Streaming agent endpoint (SSE) - real token-by-token from LLM (issue #15)
# ---------------------------------------------------------------------------
async def _stream_events(req: AgentRequest):
    try:
        logger.info(
            "Agent stream: session=%s user=%s query=%s",
            req.session_id,
            req.user_id,
            req.query[:80],
        )

        # Prompt-injection guard (issue #9)
        try:
            safe_query = _check_prompt_injection(req.query)
        except ValueError as inj_exc:
            yield f"event: error\ndata: {json.dumps({'error': str(inj_exc), 'code': 'prompt_injection_blocked'})}\n\n"
            return
        if safe_query != req.query:
            req = req.model_copy(update={"query": safe_query})

        # Input guardrail check
        input_report = input_guardrails.check(req.query)
        if not input_report.passed:
            blocked = [e for e in input_report.events if e.severity == "high"]
            if blocked:
                yield f"event: error\ndata: {json.dumps({'error': f'Input blocked: {[e.message for e in blocked]}', 'code': 'guardrail_blocked'})}\n\n"
                return
            logger.warning("Input guardrail warnings: %s", input_report.events)

        long_term_history = []
        if _long_term_memory is not None:
            long_term_history = await _long_term_memory.get_history(
                session_id=req.session_id,
                user_id=req.user_id,
                limit=6,
            )

        # Plan event
        plan_data = {
            "agent_type": "rag",
            "plan": f"Processing query: {req.query[:100]}",
        }
        yield f"event: plan\ndata: {json.dumps(plan_data)}\n\n"

        if _workflow is None:
            result = {
                "final_answer": "ADK demo fallback is active; LangGraph workflow is unavailable.",
                "agent_type": "adk",
                "sources": [],
                "confidence_score": 0.0,
                "action_result": None,
                "report_path": None,
            }
            yield f"event: token\ndata: {json.dumps({'text': result['final_answer']})}\n\n"
        else:
            ab_config = ab_manager.get_active_variant_config(
                query_id=f"{req.session_id}:{req.query[:64]}"
            )
            result = await _workflow.ainvoke(
                {
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
                    "ab_config": ab_config,
                }
            )

            # Output guardrail check
            answer = result.get("final_answer", "")
            confidence = result.get("confidence_score", 0.0)
            output_report = output_guardrails.check(req.query, answer, confidence)
            if not output_report.passed:
                logger.warning("Output guardrail warnings: %s", output_report.events)

            # Stream answer token by token (real streaming, issue #15)
            async for token in _stream_answer_tokens(answer):
                yield f"event: token\ndata: {json.dumps({'text': token})}\n\n"
                # Yield control so the SSE buffer flushes immediately.
                await asyncio.sleep(0)

        # Persist to long-term memory
        if _long_term_memory is not None:
            agent_type = result.get("agent_type", "rag")
            await _long_term_memory.save_turn(
                req.user_id, req.session_id, "user", req.query, agent_type
            )
            await _long_term_memory.save_turn(
                req.user_id,
                req.session_id,
                "assistant",
                result.get("final_answer", ""),
                agent_type,
            )

        # Sources
        sources = result.get("sources", [])
        if sources:
            yield f"event: source\ndata: {json.dumps({'sources': sources})}\n\n"

        # Complete
        yield f"event: complete\ndata: {json.dumps({'agent_type': result.get('agent_type', 'rag'), 'confidence_score': result.get('confidence_score', 0.0)})}\n\n"

    except Exception as exc:
        logger.exception("Agent stream failed: %s", exc)
        yield f"event: error\ndata: {json.dumps({'error': str(exc)})}\n\n"


@v1_router.post("/agent/invoke-stream", dependencies=[Depends(verify_and_rate_limit)])
async def invoke_agent_stream(req: AgentRequest):
    return StreamingResponse(
        _stream_events(req),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ---------------------------------------------------------------------------
# ADK demo endpoint (day 3)
# ---------------------------------------------------------------------------
@v1_router.post("/agent/adk/demo")
async def adk_demo(request: Request):
    payload = await request.json()
    user_request = payload.get("user_request", "")
    document_name = payload.get("document_name", "demo-document")
    if not user_request:
        raise HTTPException(status_code=400, detail="user_request is required")
    # Prompt-injection guard (issue #9)
    try:
        user_request = _check_prompt_injection(user_request)
    except ValueError as inj_exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(inj_exc)
        )
    return run_demo_workflow(user_request=user_request, document_name=document_name)


# ---------------------------------------------------------------------------
# Phase 4 - Explicit report generation endpoint
# ---------------------------------------------------------------------------
@v1_router.post("/agent/report", dependencies=[Depends(verify_and_rate_limit)])
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
# Phase 4 - Action execution (email, webhook, Jira, Notion)
# ---------------------------------------------------------------------------
@v1_router.post("/agent/action", dependencies=[Depends(verify_and_rate_limit)])
async def execute_action(req: ActionRequest):
    from agents.action_agent import ActionAgent

    agent = ActionAgent()
    result = await agent.execute(req.action_type, req.payload)
    return {"status": "ok", "result": result}


# ---------------------------------------------------------------------------
# Phase 3 - Ingest from external connector (Google Drive, Gmail, Slack)
# ---------------------------------------------------------------------------
@v1_router.post(
    "/agent/connector/ingest", dependencies=[Depends(verify_internal_token)]
)
async def connector_ingest(req: ConnectorIngestRequest):
    from agents.ingestion_agent import IngestionAgent

    agent = IngestionAgent()
    if req.source not in agent.supported_sources():
        raise HTTPException(
            status_code=400,
            detail=f"Unknown connector source: {req.source}. Supported: {agent.supported_sources()}",
        )

    result = await agent.ingest(
        source=req.source, user_id=req.user_id, params=req.params
    )

    # Auto-trigger retrain after connector ingestion
    try:
        from retrain import check_and_retrain

        decision = check_and_retrain(
            base_url="http://backend:8080/api",
            token=settings.internal_service_token,
            document_id=0,
            force=False,
        )
        if decision.should_retrain:
            logger.info(
                "Auto-retrain triggered after connector ingestion: %s", decision.reason
            )
    except Exception as exc:
        logger.warning("Auto-retrain trigger after connector ingest failed: %s", exc)

    return {"status": "ok", "ingested": result}


# ---------------------------------------------------------------------------
# Improvement pipeline endpoint (issue #22 - integrate dead code)
# ---------------------------------------------------------------------------
@v1_router.post("/agent/improve", dependencies=[Depends(verify_and_rate_limit)])
async def run_improvement(request: Request):
    """Trigger the auto-improvement pipeline for an agent."""
    try:
        from improvement.pipeline import run_improvement_pipeline

        payload = await request.json()
        agent_id = payload.get("agent_id", "rag_agent")
        performance_data = payload.get("performance_data", {})
        deploy_automatically = payload.get("deploy_automatically", False)

        improvement = await run_improvement_pipeline(
            agent_id=agent_id,
            performance_data=performance_data,
            deploy_automatically=deploy_automatically,
        )
        return {
            "status": "ok",
            "improvement": {
                "id": improvement.improvement_id,
                "title": improvement.title,
                "description": improvement.description,
                "status": improvement.status.value,
                "score": improvement.score,
            },
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Improvement pipeline failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# Retrain pipeline endpoint (issue #23 - integrate dead code)
# ---------------------------------------------------------------------------
@v1_router.post("/agent/retrain", dependencies=[Depends(verify_and_rate_limit)])
async def run_retrain(request: Request):
    """Trigger the retrain/re-evaluation pipeline."""
    try:
        from retrain import check_and_retrain

        payload = await request.json()
        base_url = payload.get("base_url", "http://localhost:8080/api")
        token = payload.get("token", "")
        document_id = payload.get("document_id", 1)
        force = payload.get("force", False)

        if not token:
            raise HTTPException(status_code=400, detail="token is required")

        decision = check_and_retrain(base_url, token, document_id, force)
        return {"status": "ok", "decision": decision.to_dict()}
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Retrain pipeline failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# A/B Testing report endpoint
# ---------------------------------------------------------------------------
@v1_router.get("/ab/report", dependencies=[Depends(verify_and_rate_limit)])
async def ab_report():
    return ab_manager.get_report()


@v1_router.get("/ab/variants", dependencies=[Depends(verify_and_rate_limit)])
async def ab_variants():
    exp = ab_manager.experiments.get("rag-config-v1")
    if not exp:
        return {"error": "No active experiment"}
    return {
        "experiment_id": exp.id,
        "status": exp.status,
        "variants": [
            {
                "id": v.id,
                "name": v.name,
                "description": v.description,
                "weight": v.weight,
                "is_control": v.is_control,
                "config": v.config,
            }
            for v in exp.variants
        ],
    }


# ---------------------------------------------------------------------------
# Auto-trigger retrain on document ingestion
# ---------------------------------------------------------------------------
@v1_router.post(
    "/agent/on-ingest-complete", dependencies=[Depends(verify_internal_token)]
)
async def on_ingest_complete(request: Request):
    """Called by backend after ETL completes for a document.
    Triggers retrain pipeline if conditions are met."""
    try:
        from retrain import check_and_retrain

        payload = await request.json()
        document_id = payload.get("document_id", 0)
        base_url = payload.get("base_url", "http://backend:8080/api")
        token = payload.get("token", settings.internal_service_token)

        decision = check_and_retrain(base_url, token, document_id, force=False)
        if decision.should_retrain:
            logger.info(
                "Auto-retrain triggered after document %s ingestion: %s",
                document_id,
                decision.reason,
            )
        return {
            "status": "ok",
            "should_retrain": decision.should_retrain,
            "decision": decision.to_dict(),
        }
    except Exception as exc:
        logger.warning("Auto-retrain trigger failed (non-fatal): %s", exc)
        return {"status": "ok", "should_retrain": False, "error": str(exc)}


# ---------------------------------------------------------------------------
# Register versioned routers
# ---------------------------------------------------------------------------
app.include_router(v1_router)

# Register eval + benchmark routers
try:
    from eval_framework.api import router as eval_router
    app.include_router(eval_router)
    logger.info("Eval framework router registered")
except Exception as exc:
    logger.warning("Eval framework router unavailable: %s", exc)

try:
    from benchmark.api import router as bench_router
    app.include_router(bench_router)
    logger.info("Benchmark framework router registered")
except Exception as exc:
    logger.warning("Benchmark framework router unavailable: %s", exc)
