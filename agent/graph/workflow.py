"""
LangGraph workflow – wires the Orchestrator and all sub-agents into a graph.

Flow:
  START → orchestrator → [rag | report | compare | research | action] → END

The orchestrator decides which branch to take based on user intent.
Each sub-agent node may loop back through more retrieval if confidence is low.
"""

import logging
from typing import Any, Dict, Literal

try:
    from langgraph.graph import END, START, StateGraph
except Exception:  # pragma: no cover - environment fallback
    END = "__end__"
    START = "__start__"

    class StateGraph:  # simple fallback used only for import safety
        def __init__(self, *args, **kwargs):
            self.nodes = []

        def add_node(self, *args, **kwargs):
            return None

        def add_edge(self, *args, **kwargs):
            return None

        def add_conditional_edges(self, *args, **kwargs):
            return None

        def compile(self):
            return self

from adk_runtime import run_demo_workflow

try:
    from agents.orchestrator import OrchestratorAgent
    from agents.rag_agent import RagAgent
    from agents.report_agent import ReportAgent
    from agents.comparator_agent import ComparatorAgent
    from agents.researcher_agent import ResearcherAgent
    from agents.action_agent import ActionAgent
    from agents.engineering_analysis_agent import EngineeringAnalysisAgent
except Exception:  # pragma: no cover - environment fallback
    OrchestratorAgent = None
    RagAgent = None
    ReportAgent = None
    ComparatorAgent = None
    ResearcherAgent = None
    ActionAgent = None
    EngineeringAnalysisAgent = None

from graph.state import AgentState

logger = logging.getLogger(__name__)


def run_adk_demo_node(state: AgentState) -> Dict[str, Any]:
    workflow_result = run_demo_workflow(
        user_request=state.get("query", ""),
        document_name=state.get("document_ids", ["demo-document"])[0] if state.get("document_ids") else "demo-document",
    )
    state["final_answer"] = f"ADK Demo: {workflow_result['summary']}"
    state["agent_plan"] = "ADK demo workflow executed"
    state["trace"] = workflow_result.get("trace", {})
    return state


# ---------------------------------------------------------------------------
# Routing function – reads agent_type set by orchestrator
# ---------------------------------------------------------------------------
def route_to_agent(state: AgentState) -> Literal["rag", "report", "compare", "research", "action", "engineering", "adk"]:
    agent_type = state.get("agent_type", "rag")
    logger.info("Routing to agent: %s", agent_type)
    return agent_type if agent_type in {"rag", "report", "compare", "research", "action", "engineering", "adk"} else "rag"


# ---------------------------------------------------------------------------
# Build and compile the workflow graph
# ---------------------------------------------------------------------------
def build_workflow() -> StateGraph:
    if OrchestratorAgent is not None:
        orchestrator = OrchestratorAgent()
    else:
        orchestrator = None
    if RagAgent is not None:
        rag = RagAgent()
    else:
        rag = None
    if ReportAgent is not None:
        report = ReportAgent()
    else:
        report = None
    if ComparatorAgent is not None:
        comparator = ComparatorAgent()
    else:
        comparator = None
    if ResearcherAgent is not None:
        researcher = ResearcherAgent()
    else:
        researcher = None
    if ActionAgent is not None:
        action = ActionAgent()
    else:
        action = None
    if EngineeringAnalysisAgent is not None:
        engineering = EngineeringAnalysisAgent()
    else:
        engineering = None

    graph = StateGraph(AgentState)

    # ── Nodes ───────────────────────────────────────────────────────────
    if orchestrator is not None:
        graph.add_node("orchestrator", orchestrator.run)
    if rag is not None:
        graph.add_node("rag",          rag.run)
    if report is not None:
        graph.add_node("report",       report.run)
    if comparator is not None:
        graph.add_node("compare",      comparator.run)
    if researcher is not None:
        graph.add_node("research",     researcher.run)
    if action is not None:
        graph.add_node("action",       action.run)
    if engineering is not None:
        graph.add_node("engineering",  engineering.run)
    graph.add_node("adk",          run_adk_demo_node)

    # ── Edges ────────────────────────────────────────────────────────────
    if orchestrator is not None:
        graph.add_edge(START, "orchestrator")
        graph.add_conditional_edges(
            "orchestrator",
            route_to_agent,
            {
                "rag":      "rag",
                "report":   "report",
                "compare":  "compare",
                "research": "research",
                "action":   "action",
                "engineering": "engineering",
                "adk":      "adk",
            },
        )
    else:
        graph.add_edge(START, "adk")

    # All sub-agents lead to END
    for node in ("rag", "report", "compare", "research", "action", "engineering", "adk"):
        if node in {"rag", "report", "compare", "research", "action", "engineering", "adk"}:
            graph.add_edge(node, END)

    return graph.compile()
