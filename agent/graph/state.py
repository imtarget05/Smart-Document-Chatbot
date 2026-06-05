"""
LangGraph shared state definition – passed between all nodes in the workflow.
"""

import operator
from typing import Annotated, Any, Dict, List, Optional, TypedDict

from langchain_core.messages import BaseMessage


class AgentState(TypedDict):
    # ── Core query info ───────────────────────────────────────────────────
    query: str
    session_id: str
    user_id: str
    document_ids: List[str]

    # ── Conversation messages (append-only via operator.add) ──────────────
    messages: Annotated[List[BaseMessage], operator.add]

    # ── Retrieval state (Phase 1 – enhanced RAG) ──────────────────────────
    retrieved_chunks: List[Dict[str, Any]]
    confidence_score: float
    hybrid_search_enabled: bool

    # ── Orchestration (Phase 2) ───────────────────────────────────────────
    agent_plan: str          # natural-language plan from orchestrator
    agent_type: str          # "rag" | "report" | "compare" | "research" | "action"
    use_web_search: bool

    # ── Outputs ───────────────────────────────────────────────────────────
    final_answer: str
    sources: List[Dict[str, Any]]
    action_result: Optional[Dict[str, Any]]
    report_path: Optional[str]
