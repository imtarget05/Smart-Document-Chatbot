"""
LangGraph workflow – wires the Orchestrator and all sub-agents into a graph.

Flow:
  START → orchestrator → [rag | report | compare | research | action] → END

The orchestrator decides which branch to take based on user intent.
Each sub-agent node may loop back through more retrieval if confidence is low.
"""

import logging
from typing import Any, Dict, Literal

from langgraph.graph import END, START, StateGraph

from adk_runtime import run_demo_workflow
from agents.orchestrator import OrchestratorAgent
from agents.rag_agent import RagAgent
from agents.report_agent import ReportAgent
from agents.comparator_agent import ComparatorAgent
from agents.researcher_agent import ResearcherAgent
from agents.action_agent import ActionAgent
from agents.engineering_analysis_agent import EngineeringAnalysisAgent

from graph.state import AgentState
from hitl import hitl_store
from settings import settings

logger = logging.getLogger(__name__)


def run_adk_demo_node(state: AgentState) -> Dict[str, Any]:
    """Fallback node when LangGraph is working but agents fail to load."""
    workflow_result = run_demo_workflow(
        user_request=state.get("query", ""),
        document_name=state.get("document_ids", ["demo-document"])[0]
        if state.get("document_ids")
        else "demo-document",
    )
    state["final_answer"] = f"ADK Demo: {workflow_result['summary']}"
    state["agent_plan"] = "ADK demo workflow executed"
    state["trace"] = workflow_result.get("trace", {})
    return state


# ---------------------------------------------------------------------------
# Routing function – reads agent_type set by orchestrator
# ---------------------------------------------------------------------------
ALL_AGENT_TYPES = {
    "rag",
    "report",
    "compare",
    "research",
    "action",
    "engineering",
    "adk",
}


def route_to_agent(
    state: AgentState,
) -> Literal["rag", "report", "compare", "research", "action", "engineering", "adk"]:
    agent_type = state.get("agent_type", "rag")
    logger.info("Routing to agent: %s", agent_type)
    return agent_type if agent_type in ALL_AGENT_TYPES else "rag"


# ---------------------------------------------------------------------------
# Human-in-the-Loop gate — every orchestrated action needs human approval
# ---------------------------------------------------------------------------
async def hitl_gate_node(state: AgentState) -> AgentState:
    """
    Pause before executing any real-world action (email, Jira, Notion,
    webhook...). If HITL is enabled and the request is not a human-approved
    resume, create an approval request and end the run with a pending status.
    A human later approves via POST /agent/approvals/{id}/approve, which
    re-invokes the workflow with hitl_auto_approved=True.
    """
    if not settings.hitl_require_approval or state.get("hitl_auto_approved"):
        state["hitl_pending"] = False
        state["hitl_approval_id"] = None
        return state

    record = await hitl_store.create(
            query=state.get("query", ""),
            session_id=state.get("session_id", ""),
            user_id=state.get("user_id", ""),
            agent_plan=state.get("agent_plan", ""),
            document_ids=state.get("document_ids"),
        )
    state["hitl_pending"] = True
    state["hitl_approval_id"] = record["request_id"]
    state["action_result"] = {
        "hitl": True,
        "approval_id": record["request_id"],
        "status": "pending_approval",
    }
    state["final_answer"] = (
        f"⏸ Yêu cầu hành động cần phê duyệt của con người trước khi thực thi. "
        f"Mã phê duyệt: {record['request_id']}. "
        f"Duyệt: POST /api/v1/agent/approvals/{record['request_id']}/approve "
        f"— hoặc từ chối: POST /api/v1/agent/approvals/{record['request_id']}/reject."
    )
    logger.info(
        "HITL gate paused action (request=%s, session=%s)",
        record["request_id"],
        state.get("session_id", ""),
    )
    return state


def route_after_hitl(state: AgentState) -> Literal["action", "__end__"]:
    """Continue to the action node only after human approval."""
    return "__end__" if state.get("hitl_pending") else "action"


# ---------------------------------------------------------------------------
# Build and compile the workflow graph
# ---------------------------------------------------------------------------
def build_workflow() -> StateGraph:
    """
    Build the LangGraph StateGraph workflow with all sub-agents.

    This throws ImportError eagerly if langgraph is not installed, ensuring
    no silent fallback — callers must handle the exception.
    """
    orchestrator = OrchestratorAgent()
    rag = RagAgent()
    report = ReportAgent()
    comparator = ComparatorAgent()
    researcher = ResearcherAgent()
    action = ActionAgent()
    engineering = EngineeringAnalysisAgent()

    graph = StateGraph(AgentState)

    # ── Nodes ───────────────────────────────────────────────────────────
    graph.add_node("orchestrator", orchestrator.run)
    graph.add_node("rag", rag.run)
    graph.add_node("report", report.run)
    graph.add_node("compare", comparator.run)
    graph.add_node("research", researcher.run)
    graph.add_node("action", action.run)
    graph.add_node("hitl_gate", hitl_gate_node)
    graph.add_node("engineering", engineering.run)
    graph.add_node("adk", run_adk_demo_node)

    # ── Edges ────────────────────────────────────────────────────────────
    graph.add_edge(START, "orchestrator")
    graph.add_conditional_edges(
        "orchestrator",
        route_to_agent,
        {
            "rag": "rag",
            "report": "report",
            "compare": "compare",
            "research": "research",
            "action": "hitl_gate",
            "engineering": "engineering",
            "adk": "adk",
        },
    )

    # HITL gate → action only after human approval; otherwise END (paused)
    graph.add_conditional_edges(
        "hitl_gate",
        route_after_hitl,
        {"action": "action", "__end__": END},
    )

    # All sub-agents lead to END
    for node in ALL_AGENT_TYPES:
        if node != "action":
            graph.add_edge(node, END)

    graph.add_edge("action", END)

    compiled = graph.compile()
    logger.info(
        "LangGraph workflow built: orchestrator→[%s]→END",
        ", ".join(sorted(ALL_AGENT_TYPES)),
    )
    return compiled
