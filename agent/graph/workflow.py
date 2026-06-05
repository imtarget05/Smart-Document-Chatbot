"""
LangGraph workflow – wires the Orchestrator and all sub-agents into a graph.

Flow:
  START → orchestrator → [rag | report | compare | research | action] → END

The orchestrator decides which branch to take based on user intent.
Each sub-agent node may loop back through more retrieval if confidence is low.
"""

import logging
from typing import Literal

from langgraph.graph import END, START, StateGraph

from agents.orchestrator import OrchestratorAgent
from agents.rag_agent import RagAgent
from agents.report_agent import ReportAgent
from agents.comparator_agent import ComparatorAgent
from agents.researcher_agent import ResearcherAgent
from agents.action_agent import ActionAgent
from graph.state import AgentState

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Routing function – reads agent_type set by orchestrator
# ---------------------------------------------------------------------------
def route_to_agent(state: AgentState) -> Literal["rag", "report", "compare", "research", "action"]:
    agent_type = state.get("agent_type", "rag")
    logger.info("Routing to agent: %s", agent_type)
    return agent_type if agent_type in {"rag", "report", "compare", "research", "action"} else "rag"


# ---------------------------------------------------------------------------
# Build and compile the workflow graph
# ---------------------------------------------------------------------------
def build_workflow() -> StateGraph:
    orchestrator = OrchestratorAgent()
    rag = RagAgent()
    report = ReportAgent()
    comparator = ComparatorAgent()
    researcher = ResearcherAgent()
    action = ActionAgent()

    graph = StateGraph(AgentState)

    # ── Nodes ───────────────────────────────────────────────────────────
    graph.add_node("orchestrator", orchestrator.run)
    graph.add_node("rag",          rag.run)
    graph.add_node("report",       report.run)
    graph.add_node("compare",      comparator.run)
    graph.add_node("research",     researcher.run)
    graph.add_node("action",       action.run)

    # ── Edges ────────────────────────────────────────────────────────────
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
        },
    )

    # All sub-agents lead to END
    for node in ("rag", "report", "compare", "research", "action"):
        graph.add_edge(node, END)

    return graph.compile()
