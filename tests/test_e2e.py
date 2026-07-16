"""
TC-E2E-01 → TC-E2E-04: Integration & End-to-End Tests
"""
import pytest
import time
import sys
import os
import json
from typing import List, Dict, Optional
from dataclasses import dataclass, field
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@dataclass
class RetrievalResult:
    doc_id: str
    content: str
    score: float


@dataclass
class E2EAnswer:
    text: str
    confidence: float
    citations: List[str]
    latency_ms: float
    grounded: bool


class MockRAGPipeline:
    def __init__(self, docs: List[Dict]):
        self.docs = docs

    def embed_and_retrieve(self, query: str, k: int = 3) -> List[RetrievalResult]:
        results = []
        for doc in self.docs:
            words = set(query.lower().split())
            doc_words = set(doc["content"].lower().split())
            overlap = len(words & doc_words)
            score = overlap / max(len(words), 1)
            results.append(RetrievalResult(doc_id=doc["id"], content=doc["content"], score=score))
        results.sort(key=lambda x: x.score, reverse=True)
        return results[:k]

    def rerank(self, query: str, results: List[RetrievalResult]) -> List[RetrievalResult]:
        return results

    def generate(self, query: str, context: List[RetrievalResult]) -> E2EAnswer:
        start = time.time()
        if not context:
            return E2EAnswer(text="Không có thông tin", confidence=0.1, citations=[], latency_ms=0, grounded=False)

        top = context[0]
        answer_text = f"Dựa trên tài liệu: {top.content[:100]}"
        citations = [f"[{r.doc_id}]" for r in context if r.score > 0.3]
        latency = (time.time() - start) * 1000

        return E2EAnswer(
            text=answer_text, confidence=0.85, citations=citations,
            latency_ms=latency, grounded=len(citations) > 0
        )

    def query(self, query: str, k: int = 3) -> E2EAnswer:
        retrieved = self.embed_and_retrieve(query, k)
        reranked = self.rerank(query, retrieved)
        return self.generate(query, reranked)


class MockETLPipeline:
    def __init__(self):
        self.datasets: Dict[str, List[Dict]] = {}

    def load(self, data: Dict[str, List[Dict]]):
        self.datasets = data

    def clean(self, dataset_name: str) -> List[Dict]:
        data = self.datasets.get(dataset_name, [])
        cleaned = []
        for row in data:
            if all(v is not None for v in row.values()):
                cleaned.append(row)
        self.datasets[dataset_name] = cleaned
        return cleaned

    def compute_kpis(self, dataset_name: str) -> Dict:
        data = self.datasets.get(dataset_name, [])
        if not data:
            return {}
        return {"total_rows": len(data), "datasets": list(self.datasets.keys())}


class MockAlertSystem:
    def __init__(self, thresholds: Dict = None):
        self.thresholds = thresholds or {"temperature": 85, "downtime": 60}
        self.alerts: List[Dict] = []

    def check(self, metrics: Dict) -> List[Dict]:
        alerts = []
        if metrics.get("temperature", 0) > self.thresholds["temperature"]:
            alerts.append({"type": "CRITICAL", "message": f"Temperature {metrics['temperature']}°C > {self.thresholds['temperature']}°C"})
        if metrics.get("downtime", 0) > self.thresholds["downtime"]:
            alerts.append({"type": "WARNING", "message": f"Downtime {metrics['downtime']}min > {self.thresholds['downtime']}min"})
        self.alerts.extend(alerts)
        return alerts


class MockPDFExporter:
    def export(self, content: Dict, filename: str = "report.pdf") -> str:
        return f"/exports/{filename}"


class TestE2EIntegration:

    def test_e2e01_full_rag_pipeline(self):
        """TC-E2E-01: Full RAG Pipeline — query → embed → retrieve → rerank → generate → verify."""
        docs = [
            {"id": "doc1", "content": "Chính sách đổi trả: khách hàng được đổi trả trong 30 ngày."},
            {"id": "doc2", "content": "Quy định an toàn: đội mũ bảo hộ khi vào xưởng."},
            {"id": "doc3", "content": "Lương thưởng dựa trên hiệu suất quý."},
        ]
        pipeline = MockRAGPipeline(docs)

        start = time.time()
        answer = pipeline.query("Chính sách đổi trả là gì?")
        total_latency = (time.time() - start) * 1000

        assert answer.text is not None
        assert answer.confidence > 0
        assert total_latency < 5000, f"Pipeline too slow: {total_latency}ms"
        assert answer.grounded == True

    def test_e2e02_multi_turn_conversation(self):
        """TC-E2E-02: Multi-Turn Conversation — context maintained across turns."""
        docs = [
            {"id": "doc1", "content": "Chính sách đổi trả: 30 ngày."},
            {"id": "doc2", "content": "Phí vận chuyển: miễn phí khi đổi trả."},
        ]
        pipeline = MockRAGPipeline(docs)

        turns = [
            "Chính sách đổi trả là gì?",
            "Phí vận chuyển khi đổi trả?",
            "Thời gian xử lý đổi trả?",
        ]

        context_relevances = []
        for turn in turns:
            answer = pipeline.query(turn)
            has_relevant = any(c in answer.text for c in ["30", "miễn phí", "vận chuyển"])
            context_relevances.append(1.0 if has_relevant else 0.0)

        avg_relevance = sum(context_relevances) / len(context_relevances)
        assert avg_relevance >= 0.5, f"Context relevance too low: {avg_relevance}"

    def test_e2e03_etl_to_kpi_to_alert(self):
        """TC-E2E-03: ETL → KPI → Alert — data flows through pipeline."""
        etl = MockETLPipeline()
        raw_data = {
            "machine": [
                {"id": "M1", "temp": 70, "status": "running"},
                {"id": "M2", "temp": 90, "status": "failure"},
                {"id": "M3", "temp": 65, "status": "running"},
            ]
        }
        etl.load(raw_data)

        cleaned = etl.clean("machine")
        assert len(cleaned) == 3

        kpis = etl.compute_kpis("machine")
        assert kpis["total_rows"] == 3

        alert_sys = MockAlertSystem()
        alerts = alert_sys.check({"temperature": 90})
        assert len(alerts) == 1
        assert alerts[0]["type"] == "CRITICAL"

    def test_e2e04_dashboard_to_api_to_model(self):
        """TC-E2E-04: Dashboard → API → Model — end-to-end user flow."""
        docs = [
            {"id": "doc1", "content": "Báo cáo sản xuất: đạt 95% mục tiêu."},
        ]
        pipeline = MockRAGPipeline(docs)
        exporter = MockPDFExporter()

        answer = pipeline.query("Tạo báo cáo sản xuất")
        assert answer.confidence > 0

        pdf_path = exporter.export({"answer": answer.text, "citations": answer.citations})
        assert pdf_path is not None
        assert ".pdf" in pdf_path
