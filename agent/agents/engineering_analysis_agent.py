"""
Engineering Analysis Agent.

Specialized for test reports, failure summaries, root-cause analysis, corrective
actions, and 8D-style engineering reports grounded in retrieved evidence.
"""

import logging
from typing import Dict, List

from langchain_core.messages import HumanMessage, SystemMessage

from graph.state import AgentState
from llm_factory import LLMFactory
from tools.qdrant_tool import QdrantHybridSearch

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """You are an engineering document analysis agent.
Use only the provided evidence. Produce a concise, structured 8D-style report:

D1 Team / Scope
D2 Problem Description
D3 Containment Actions
D4 Root Cause Analysis
D5 Corrective Actions
D6 Verification Plan
D7 Prevention / Lessons Learned
D8 Closure Summary

Rules:
- Cite evidence inline with [document_name].
- If evidence is missing, say "Not found in provided evidence".
- Do not invent measurements, owners, dates, or corrective actions."""


class EngineeringAnalysisAgent:
    def __init__(self) -> None:
        self._llm = LLMFactory.get_reasoning_model(temperature=0.1)
        self._search = QdrantHybridSearch()

    async def run(self, state: AgentState) -> AgentState:
        query = state["query"]
        document_ids = state.get("document_ids") or []
        logger.info(
            "EngineeringAnalysisAgent query=%s docs=%s", query[:80], document_ids
        )

        if not document_ids:
            state["final_answer"] = (
                "Engineering analysis requires at least one indexed document or connector collection. "
                "Ingest/upload a test report first, then retry with the returned collection id."
            )
            state["sources"] = []
            state["agent_type"] = "engineering"
            return state

        chunks = await self._retrieve_engineering_evidence(query, document_ids)
        if not chunks:
            state["final_answer"] = (
                "No relevant engineering evidence was retrieved. Try selecting the test report "
                "document or connector collection explicitly."
            )
            state["sources"] = []
            state["agent_type"] = "engineering"
            state["confidence_score"] = 0.0
            return state

        evidence = "\n\n---\n\n".join(
            f"[{c.get('document_name', 'document')}]\n{c.get('text', '')}"
            for c in chunks[:12]
        )
        response = await self._llm.ainvoke(
            [
                SystemMessage(content=_SYSTEM_PROMPT),
                HumanMessage(content=f"User request: {query}\n\nEvidence:\n{evidence}"),
            ]
        )

        state["final_answer"] = response.content.strip()
        state["sources"] = self._sources(chunks)
        state["agent_type"] = "engineering"
        state["confidence_score"] = max(
            (c.get("score", 0.0) for c in chunks), default=0.0
        )
        return state

    async def _retrieve_engineering_evidence(
        self,
        query: str,
        document_ids: List[str],
    ) -> List[Dict]:
        search_query = (
            f"{query}\n"
            "failure root cause containment corrective action verification 8D test report"
        )
        all_chunks: List[Dict] = []
        for doc_id in document_ids:
            try:
                all_chunks.extend(
                    await self._search.hybrid_search(
                        search_query, doc_id, top_k=8, use_bm25=True
                    )
                )
            except Exception as exc:
                logger.warning("Engineering retrieval failed for %s: %s", doc_id, exc)

        deduped: Dict[str, Dict] = {}
        for chunk in all_chunks:
            key = chunk.get("text", "").strip()[:240]
            if key and (
                key not in deduped
                or deduped[key].get("score", 0) < chunk.get("score", 0)
            ):
                deduped[key] = chunk
        return sorted(deduped.values(), key=lambda c: c.get("score", 0), reverse=True)

    @staticmethod
    def _sources(chunks: List[Dict]) -> List[Dict]:
        return [
            {
                "document_name": c.get("document_name", "document"),
                "chunk_text": c.get("text", "")[:300],
                "score": round(c.get("score", 0.0), 4),
                "source_type": c.get("source_type", "document"),
            }
            for c in chunks[:6]
        ]
