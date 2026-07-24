"""
Researcher Agent – Phase 2 + Phase 3.
Performs web research using Tavily, optionally augments with document content,
and synthesises a comprehensive answer with citations.
"""

import logging
from typing import Dict, List

from langchain_core.messages import HumanMessage, SystemMessage
from llm_factory import LLMFactory

from graph.state import AgentState
from tools.web_search_tool import TavilySearch
from tools.qdrant_tool import QdrantHybridSearch

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """You are an expert research assistant.
Synthesise the following web search results and (optionally) document excerpts into a clear,
well-structured answer. Include inline citations in the format [Source: title] or [Document: name].
Always mention the date/recency of information where possible."""


class ResearcherAgent:
    def __init__(self):
        self._llm = LLMFactory.get_reasoning_model(temperature=0.3)
        self._web = TavilySearch()
        self._search = QdrantHybridSearch()

    async def run(self, state: AgentState) -> AgentState:
        query = state["query"]
        document_ids = state.get("document_ids") or []

        logger.info("Researcher Agent: web research for query=%s", query[:80])

        # 1. Web search
        web_results: List[Dict] = []
        try:
            web_results = await self._web.search(query, max_results=5)
        except Exception as exc:
            logger.warning("Tavily web search failed: %s", exc)

        # 2. Optional document retrieval for grounding
        doc_chunks: List[Dict] = []
        for doc_id in document_ids[:3]:
            try:
                chunks = await self._search.hybrid_search(
                    query, doc_id, top_k=3, use_bm25=True
                )
                doc_chunks.extend(chunks)
            except Exception as exc:
                logger.warning("Doc retrieval failed: %s", exc)

        # 3. Build context
        web_context = "\n\n".join(
            f"[{r.get('title', 'Web')}] (url: {r.get('url', '')})\n{r.get('content', '')}"
            for r in web_results
        )
        doc_context = "\n\n".join(
            f"[{c.get('document_name', 'doc')}]\n{c.get('text', '')}"
            for c in doc_chunks[:5]
        )
        full_context = ""
        if web_context:
            full_context += f"=== Web Results ===\n{web_context}\n\n"
        if doc_context:
            full_context += f"=== Document Context ===\n{doc_context}"

        if not full_context:
            # Pure LLM fallback
            response = await self._llm.ainvoke([HumanMessage(content=query)])
            state["final_answer"] = (
                "💭 [No external sources found]\n\n" + response.content.strip()
            )
            state["sources"] = []
            state["agent_type"] = "research"
            return state

        response = await self._llm.ainvoke(
            [
                SystemMessage(content=_SYSTEM_PROMPT),
                HumanMessage(content=f"Query: {query}\n\n{full_context}"),
            ]
        )

        sources = [
            {
                "document_name": r.get("title", "Web"),
                "chunk_text": r.get("content", "")[:300],
                "score": 1.0,
                "source_type": "web",
                "url": r.get("url", ""),
            }
            for r in web_results
        ] + [
            {
                "document_name": c.get("document_name", ""),
                "chunk_text": c.get("text", "")[:200],
                "score": c.get("score", 0),
                "source_type": "document",
            }
            for c in doc_chunks[:3]
        ]

        state["final_answer"] = "🔍 [Web Research]\n\n" + response.content.strip()
        state["sources"] = sources
        state["agent_type"] = "research"
        return state
