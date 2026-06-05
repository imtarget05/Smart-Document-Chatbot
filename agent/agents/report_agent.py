"""
Report Agent – Phase 4.
Synthesises document content and generates structured PDF / text reports.
"""

import logging
import os
import tempfile
from datetime import datetime
from typing import List

from langchain_core.messages import HumanMessage
from llm_factory import LLMFactory

from graph.state import AgentState
from settings import settings
from tools.qdrant_tool import QdrantHybridSearch
from tools.report_tool import PdfReportBuilder

logger = logging.getLogger(__name__)


class ReportAgent:
    def __init__(self):
        self._llm    = LLMFactory.get_local_model(temperature=0.2)
        self._search = QdrantHybridSearch()
        self._pdf    = PdfReportBuilder()

    # ------------------------------------------------------------------
    # LangGraph node entry point
    # ------------------------------------------------------------------
    async def run(self, state: AgentState) -> AgentState:
        query        = state["query"]
        document_ids = state.get("document_ids") or []

        logger.info("Report Agent: building report for query=%s", query[:80])

        # 1. Retrieve relevant content from all documents
        all_chunks: List[dict] = []
        for doc_id in document_ids:
            chunks = await self._search.hybrid_search(query, doc_id, top_k=8, use_bm25=True)
            all_chunks.extend(chunks)

        all_chunks.sort(key=lambda x: x.get("score", 0), reverse=True)

        # 2. Generate report content via LLM
        context = "\n\n---\n\n".join(
            f"[{c.get('document_name','doc')}]\n{c.get('text','')}" for c in all_chunks[:10]
        )
        report_prompt = (
            f"You are a professional report writer. Based on the following document excerpts, "
            f"write a comprehensive, well-structured report that addresses the user's request.\n\n"
            f"User request: {query}\n\n"
            f"Document excerpts:\n{context}\n\n"
            f"Write the report with: Executive Summary, Key Findings, Details, and Conclusion."
        )
        response  = await self._llm.ainvoke([HumanMessage(content=report_prompt)])
        report_md = response.content.strip()

        # 3. Build PDF
        title     = f"Report – {datetime.now().strftime('%Y-%m-%d')}"
        pdf_path  = await self.generate_pdf_report(title=title, content=report_md, user_id=state["user_id"])

        state["final_answer"] = f"📄 Report generated successfully.\n\n{report_md}"
        state["report_path"]  = pdf_path
        state["agent_type"]   = "report"
        state["sources"] = [
            {"document_name": c.get("document_name", ""), "chunk_text": c.get("text", "")[:200],
             "score": c.get("score", 0), "source_type": "document"}
            for c in all_chunks[:5]
        ]
        return state

    # ------------------------------------------------------------------
    # Standalone PDF generation (also called via /agent/report endpoint)
    # ------------------------------------------------------------------
    async def generate_pdf_report(self, title: str, content: str, user_id: str) -> str:
        output_dir = os.environ.get("REPORT_OUTPUT_DIR", tempfile.gettempdir())
        os.makedirs(output_dir, exist_ok=True)
        filename = f"report_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        path     = os.path.join(output_dir, filename)
        self._pdf.build(title=title, content=content, output_path=path)
        logger.info("PDF report written to %s", path)
        return path
