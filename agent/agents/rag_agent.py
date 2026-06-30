"""
RAG Agent – Phase 1 enhanced RAG pipeline.

Improvements over the basic Java implementation:
  1. Hybrid search:  semantic (Qdrant cosine) + BM25 keyword scoring → RRF fusion
  2. Cross-encoder reranking:  re-score top-k with a prompted LLM judge
  3. Multi-doc reasoning:      synthesise answer across several documents
  4. Citation tracking:        every answer carries structured source citations
  5. Corrective CRAG loop:     query reformulation + parallel re-retrieval on low confidence
"""

import asyncio
import logging
import re
from typing import Dict, List, Tuple

from langchain_core.messages import HumanMessage, SystemMessage

from llm_factory import LLMFactory
from graph.state import AgentState
from memory.short_term import ShortTermMemory
from settings import settings
from tools.qdrant_tool import QdrantHybridSearch

logger = logging.getLogger(__name__)

CONFIDENCE_THRESHOLD = 0.45
TOP_K = 5


class RagAgent:
    def __init__(self):
        self._llm = LLMFactory.get_reasoning_model(temperature=settings.llm_temperature)
        self._search = QdrantHybridSearch()
        self._memory = ShortTermMemory()

    # ------------------------------------------------------------------
    # Main node entry point
    # ------------------------------------------------------------------
    async def run(self, state: AgentState) -> AgentState:
        query        = state["query"]
        document_ids = state.get("document_ids") or []
        session_id   = state["session_id"]
        hybrid       = state.get("hybrid_search_enabled", True)

        logger.info("RAG Agent: query=%s docs=%s hybrid=%s", query[:80], document_ids, hybrid)

        # 1. Initial hybrid retrieval ──────────────────────────────────
        chunks, max_score = await self._retrieve(query, document_ids, hybrid)
        state["confidence_score"] = max_score

        # 2. CRAG loop if confidence is low ────────────────────────────
        if max_score < CONFIDENCE_THRESHOLD:
            logger.info("Low confidence %.2f < %.2f – starting CRAG loop", max_score, CONFIDENCE_THRESHOLD)
            chunks, max_score = await self._crag_loop(query, document_ids, hybrid)
            state["confidence_score"] = max_score

        # 3. Cross-encoder reranking ────────────────────────────────────
        if chunks:
            chunks = await self._rerank(query, chunks)

        # 4. Build answer ───────────────────────────────────────────────
        if chunks and max_score >= CONFIDENCE_THRESHOLD:
            answer = await self._generate_answer(
                query,
                chunks,
                session_id,
                state.get("long_term_history", []),
            )
        elif state.get("use_web_search"):
            answer = await self._web_search_fallback(query)
            chunks = []
        else:
            answer = await self._deep_reasoning_fallback(query)
            chunks = []

        # 5. Build citations ────────────────────────────────────────────
        sources = [
            {
                "document_name": c.get("document_name", "unknown"),
                "chunk_text":    c.get("text", "")[:300],
                "score":         round(c.get("score", 0.0), 4),
                "source_type":   c.get("source_type", "document"),
            }
            for c in chunks[:TOP_K]
        ]

        # 6. Persist to short-term memory ──────────────────────────────
        self._memory.add(session_id, "user",      query)
        self._memory.add(session_id, "assistant", answer)

        state["final_answer"]     = answer
        state["sources"]          = sources
        state["retrieved_chunks"] = chunks
        state["agent_type"]       = "rag"
        return state

    # ------------------------------------------------------------------
    # Hybrid retrieval (semantic + BM25 → Reciprocal Rank Fusion)
    # ------------------------------------------------------------------
    async def _retrieve(
        self, query: str, document_ids: List[str], hybrid: bool
    ) -> Tuple[List[Dict], float]:
        if not document_ids:
            return [], 0.0

        tasks = [
            self._search.hybrid_search(query, doc_id, top_k=TOP_K, use_bm25=hybrid)
            for doc_id in document_ids
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_chunks: List[Dict] = []
        for r in results:
            if isinstance(r, Exception):
                logger.warning("Retrieval task failed: %s", r)
                continue
            all_chunks.extend(r)

        # Deduplicate by text
        seen: Dict[str, Dict] = {}
        for c in all_chunks:
            key = c.get("text", "").strip()[:200]
            if key not in seen or seen[key]["score"] < c["score"]:
                seen[key] = c
        deduped = sorted(seen.values(), key=lambda x: x["score"], reverse=True)

        max_score = deduped[0]["score"] if deduped else 0.0
        return deduped, max_score

    # ------------------------------------------------------------------
    # Corrective CRAG loop
    # ------------------------------------------------------------------
    async def _crag_loop(
        self, query: str, document_ids: List[str], hybrid: bool
    ) -> Tuple[List[Dict], float]:
        # Step 1: reformulate queries
        variants = await self._reformulate_query(query)
        all_queries = [query] + variants

        tasks = [
            self._retrieve(q, document_ids, hybrid)
            for q in all_queries
        ]
        all_results = await asyncio.gather(*tasks, return_exceptions=True)

        merged: Dict[str, Dict] = {}
        best_score = 0.0
        for res in all_results:
            if isinstance(res, Exception):
                continue
            chunks, score = res
            if score > best_score:
                best_score = score
            for c in chunks:
                key = c.get("text", "").strip()[:200]
                if key not in merged or merged[key]["score"] < c["score"]:
                    merged[key] = c

        final = sorted(merged.values(), key=lambda x: x["score"], reverse=True)
        return final, best_score

    # ------------------------------------------------------------------
    # Query reformulation via LLM
    # ------------------------------------------------------------------
    async def _reformulate_query(self, query: str) -> List[str]:
        prompt = (
            f"Rewrite the following question into 2 alternative phrasings to improve document retrieval. "
            f"Output ONLY the two alternatives, one per line, no numbering.\n\nQuestion: {query}"
        )
        try:
            response = await self._llm.ainvoke([HumanMessage(content=prompt)])
            lines = [line.strip() for line in response.content.strip().split("\n") if line.strip()]
            return lines[:2]
        except Exception as exc:
            logger.warning("Query reformulation failed: %s", exc)
            return []

    # ------------------------------------------------------------------
    # Cross-encoder reranking (LLM-based relevance judge)
    # ------------------------------------------------------------------
    async def _rerank(self, query: str, chunks: List[Dict]) -> List[Dict]:
        if len(chunks) <= 2:
            return chunks

        system = (
            "You are a relevance judge. Given a query and a passage, output a relevance score "
            "from 0.0 to 1.0 (no other text). Be strict."
        )
        tasks = []
        for c in chunks[:TOP_K * 2]:
            text = c.get("text", "")[:500]
            user_msg = f"Query: {query}\nPassage: {text}\nScore:"
            tasks.append(
                self._llm.ainvoke([SystemMessage(content=system), HumanMessage(content=user_msg)])
            )

        responses = await asyncio.gather(*tasks, return_exceptions=True)
        rescored = []
        for i, resp in enumerate(responses):
            chunk = chunks[i]
            if isinstance(resp, Exception):
                rescored.append(chunk)
                continue
            try:
                score = float(re.search(r"[\d.]+", resp.content).group())
                chunk = dict(chunk)
                chunk["rerank_score"] = score
                chunk["score"] = (chunk["score"] + score) / 2
            except Exception:
                pass
            rescored.append(chunk)

        return sorted(rescored, key=lambda x: x["score"], reverse=True)

    # ------------------------------------------------------------------
    # Generate RAG answer
    # ------------------------------------------------------------------
    async def _generate_answer(
        self,
        query: str,
        chunks: List[Dict],
        session_id: str,
        long_term_history: List[Dict],
    ) -> str:
        history = self._memory.get_recent(session_id, turns=3)
        if not history and long_term_history:
            history = [
                {"role": item.get("role", ""), "content": item.get("content", "")}
                for item in long_term_history[-6:]
            ]
        context_parts = []
        for c in chunks[:TOP_K]:
            doc  = c.get("document_name", "document")
            text = c.get("text", "")
            context_parts.append(f"[{doc}]\n{text}")
        context = "\n\n---\n\n".join(context_parts)

        history_text = ""
        if history:
            history_text = "\n".join(
                f"{m['role'].capitalize()}: {m['content']}" for m in history
            )
            history_text = f"\n\n[Conversation history]\n{history_text}\n"

        prompt = (
            f"You are a helpful document assistant. Answer the user's question based ONLY on the "
            f"provided context. Include citations in the format [document_name].{history_text}\n\n"
            f"[Context]\n{context}\n\n[Question]\n{query}\n\n[Answer]"
        )
        response = await self._llm.ainvoke([HumanMessage(content=prompt)])
        return response.content.strip()

    # ------------------------------------------------------------------
    # Fallbacks
    # ------------------------------------------------------------------
    async def _web_search_fallback(self, query: str) -> str:
        from tools.web_search_tool import TavilySearch
        results = await TavilySearch().search(query, max_results=3)
        if not results:
            return await self._deep_reasoning_fallback(query)
        context = "\n\n".join(r["content"] for r in results)
        prompt  = f"Based on the following web search results, answer the question.\n\nResults:\n{context}\n\nQuestion: {query}\n\nAnswer:"
        response = await self._llm.ainvoke([HumanMessage(content=prompt)])
        return "🌐 [Web Search]\n\n" + response.content.strip()

    async def _deep_reasoning_fallback(self, query: str) -> str:
        prompt = (
            f"The retrieved documents don't contain enough relevant information. "
            f"Use your internal knowledge to answer as accurately as possible.\n\nQuestion: {query}\n\nAnswer:"
        )
        response = await self._llm.ainvoke([HumanMessage(content=prompt)])
        return "⚠️ [Deep Reasoning – low document confidence]\n\n" + response.content.strip()
