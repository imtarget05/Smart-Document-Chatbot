"""
Smart Document Chatbot - Agent Service
FastAPI entrypoint for the multi-agent LangGraph orchestration layer.
Accepts requests from the Spring Boot backend (verified via INTERNAL_SERVICE_TOKEN).
"""

import logging
import os
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse

from graph.workflow import build_workflow
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
_long_term_memory: LongTermMemory | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _workflow, _long_term_memory
    logger.info("Starting agent service …")
    _workflow = build_workflow()
    _long_term_memory = LongTermMemory()
    await _long_term_memory.init()
    logger.info("Agent service ready.")
    yield
    logger.info("Shutting down agent service …")


app = FastAPI(
    title="Smart Document Chatbot - Agent Service",
    version="2.0.0",
    description="LangGraph multi-agent orchestration layer",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],      # Spring Boot is the only caller; restrict further if needed
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Security – shared secret injected by Spring Boot
# ---------------------------------------------------------------------------
def verify_internal_token(request: Request):
    token = request.headers.get("X-Internal-Token", "")
    if token != settings.internal_service_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------
@app.get("/health")
async def health():
    return {"status": "ok", "service": "agent"}


# ---------------------------------------------------------------------------
# Phase 2 – Main agent endpoint (Orchestrator decides which sub-agent to use)
# ---------------------------------------------------------------------------
@app.post("/agent/invoke", response_model=AgentResponse, dependencies=[Depends(verify_internal_token)])
async def invoke_agent(req: AgentRequest):
    """
    Receives a user query from Spring Boot, runs the LangGraph orchestration
    workflow and returns a structured AgentResponse.
    """
    try:
        logger.info("Agent invoke: session=%s user=%s query=%s", req.session_id, req.user_id, req.query[:80])
        result = await _workflow.ainvoke({
            "query": req.query,
            "session_id": req.session_id,
            "user_id": req.user_id,
            "document_ids": req.document_ids or [],
            "messages": [],
            "retrieved_chunks": [],
            "confidence_score": 0.0,
            "agent_plan": "",
            "agent_type": "",
            "final_answer": "",
            "sources": [],
            "action_result": None,
            "report_path": None,
            "use_web_search": req.use_web_search,
            "hybrid_search_enabled": True,
        })
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
# Phase 4 – Explicit report generation endpoint
# ---------------------------------------------------------------------------
@app.post("/agent/report", dependencies=[Depends(verify_internal_token)])
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
@app.post("/agent/action", dependencies=[Depends(verify_internal_token)])
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
    from connectors.google_drive import GoogleDriveConnector
    from connectors.gmail import GmailConnector
    from connectors.slack_connector import SlackConnector

    mapping = {
        "google_drive": GoogleDriveConnector,
        "gmail": GmailConnector,
        "slack": SlackConnector,
    }
    cls = mapping.get(req.source)
    if not cls:
        raise HTTPException(status_code=400, detail=f"Unknown connector source: {req.source}")

    connector = cls()
    result = await connector.ingest(user_id=req.user_id, params=req.params)
    return {"status": "ok", "ingested": result}
