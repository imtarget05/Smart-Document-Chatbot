"""
Comparator Agent – Phase 2.
Compares two or more documents side-by-side on a given topic/query,
highlighting similarities, differences and key insights.
"""

import asyncio
import logging
from typing import Dict, List

from langchain_core.messages import HumanMessage, SystemMessage
from llm_factory import LLMFactory

from graph.state import AgentState
from tools.qdrant_tool import QdrantHybridSearch

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """You are a document comparison expert.
Given excerpts from multiple documents and a comparison query, produce a structured analysis:

1. **Overview** – brief description of each document
2. **Similarities** – key points both/all documents agree on
3. **Differences** – key points where documents differ, with citations [doc_name]
4. **Recommendation** – which document best addresses the query and why

Be precise and cite sources."""


class ComparatorAgent:
    def __init__(self):
        self._llm = LLMFactory.get_reasoning_model(temperature=0.1)
        self._search = QdrantHybridSearch()

    async def run(self, state: AgentState) -> AgentState:
        query = state["query"]
        document_ids = state.get("document_ids") or []

        logger.info(
            "Comparator Agent: comparing %d docs for query=%s",
            len(document_ids),
            query[:80],
        )

        if len(document_ids) < 2:
            state["final_answer"] = (
                "⚠️ Comparator requires at least 2 documents. Please select more documents."
            )
            state["agent_type"] = "compare"
            return state

        # Retrieve content from each document in parallel
        tasks = [
            self._search.hybrid_search(query, doc_id, top_k=5, use_bm25=True)
            for doc_id in document_ids
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Build per-doc context blocks
        doc_blocks: List[str] = []
        all_sources: List[Dict] = []
        for i, res in enumerate(results):
            doc_id = document_ids[i]
            if isinstance(res, Exception):
                logger.warning("Retrieval failed for doc %s: %s", doc_id, res)
                doc_blocks.append(f"[Document {doc_id}]\n(Retrieval failed)")
                continue
            chunks = res
            text = "\n".join(c.get("text", "") for c in chunks[:5])
            name = (
                chunks[0].get("document_name", f"Document {doc_id}")
                if chunks
                else f"Document {doc_id}"
            )
            doc_blocks.append(f"[{name}]\n{text}")
            all_sources.extend(
                {
                    "document_name": c.get("document_name", name),
                    "chunk_text": c.get("text", "")[:200],
                    "score": c.get("score", 0.0),
                    "source_type": "document",
                }
                for c in chunks[:3]
            )

        context = "\n\n=====\n\n".join(doc_blocks)
        response = await self._llm.ainvoke(
            [
                SystemMessage(content=_SYSTEM_PROMPT),
                HumanMessage(content=f"Query: {query}\n\nDocuments:\n{context}"),
            ]
        )

        state["final_answer"] = response.content.strip()
        state["sources"] = all_sources
        state["agent_type"] = "compare"
        return state
