"""
Orchestrator Agent – analyses the user query, produces a plan and decides
which specialist sub-agent should handle it.

Intent classification:
  • rag       – direct Q&A against uploaded documents
  • report    – user asks to generate a report / summary document
  • compare   – user asks to compare two or more documents / topics
  • research  – general research question, needs web search
  • action    – user asks to DO something (send email, create task …)
"""

import logging
import re

from langchain_core.messages import HumanMessage, SystemMessage

from llm_factory import LLMFactory
from graph.state import AgentState
from settings import settings

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """You are an intelligent orchestrator for a document Q&A platform.
Analyze the user's query and output EXACTLY one JSON object (no markdown) with two keys:
  "intent": one of ["rag", "report", "compare", "research", "action"]
  "plan":   a short 1-sentence description of what needs to be done

Mapping guide:
- rag      → answer question from documents
- report   → create a structured report / PDF
- compare  → compare / diff multiple documents
- research → search the web for external information
- action   → perform an action (send email, create Jira ticket, trigger webhook)

Examples:
  User: "What does the contract say about payment terms?" → {"intent":"rag","plan":"Retrieve payment term clauses from documents."}
  User: "Generate a PDF summary of document 3"           → {"intent":"report","plan":"Build a PDF report from document 3."}
  User: "Compare documents 1 and 2 on pricing"           → {"intent":"compare","plan":"Compare pricing sections of doc 1 and doc 2."}
  User: "Find the latest news about LangGraph"           → {"intent":"research","plan":"Web-search for recent LangGraph news."}
  User: "Send an email with the summary to john@co.com"  → {"intent":"action","plan":"Send email with document summary."}
"""


class OrchestratorAgent:
    def __init__(self):
        self._llm = LLMFactory.get_reasoning_model(temperature=0.0)

    async def run(self, state: AgentState) -> AgentState:
        query = state["query"]
        logger.info("Orchestrator analysing: %s", query[:120])

        # Allow caller to override intent
        if state.get("intent_override"):
            intent = state["intent_override"]
            state["agent_type"] = intent
            state["agent_plan"] = f"Intent overridden to: {intent}"
            logger.info("Intent override: %s", intent)
            return state

        try:
            response = await self._llm.ainvoke([
                SystemMessage(content=_SYSTEM_PROMPT),
                HumanMessage(content=query),
            ])
            raw = response.content.strip()

            # Extract JSON – handle models that wrap in markdown code blocks
            json_match = re.search(r'\{[^}]+\}', raw, re.DOTALL)
            if json_match:
                import json
                parsed = json.loads(json_match.group())
                intent = parsed.get("intent", "rag")
                plan   = parsed.get("plan", "")
            else:
                # Fallback heuristics
                intent, plan = self._heuristic_intent(query)

        except Exception as exc:
            logger.warning("Orchestrator LLM call failed: %s – falling back to heuristic", exc)
            intent, plan = self._heuristic_intent(query)

        state["agent_type"] = intent
        state["agent_plan"]  = plan
        logger.info("Orchestrator decision → intent=%s plan=%s", intent, plan)
        return state

    # ------------------------------------------------------------------
    # Simple keyword heuristics as a safe fallback
    # ------------------------------------------------------------------
    @staticmethod
    def _heuristic_intent(query: str):
        q = query.lower()
        if any(k in q for k in ("report", "pdf", "summary", "tóm tắt", "báo cáo", "xuất")):
            return "report", "Generate a report from documents."
        if any(k in q for k in ("compare", "so sánh", "difference", "diff", "vs")):
            return "compare", "Compare documents."
        if any(k in q for k in ("search web", "tìm kiếm", "news", "latest", "researcher")):
            return "research", "Research via web."
        if any(k in q for k in ("send email", "gửi email", "jira", "notion", "task", "webhook", "trigger")):
            return "action", "Execute an action."
        return "rag", "Answer from documents using RAG."
