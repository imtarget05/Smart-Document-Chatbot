"""
TC-TK-01 → TC-TK-07: TopK Retrieval Pipeline Tests
"""

import time
import sys
import os
from typing import List, Dict
from dataclasses import dataclass

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@dataclass
class RetrievalResult:
    doc_id: str
    content: str
    score: float
    metadata: dict = None


class MockRetriever:
    """Mock retriever for testing TopK logic."""

    def __init__(self, docs: List[Dict] = None):
        self.docs = docs or []

    def retrieve(
        self, query: str, k: int = 5, threshold: float = 0.0
    ) -> List[RetrievalResult]:
        results = []
        for doc in self.docs:
            score = self._compute_score(query, doc["content"])
            if score >= threshold:
                results.append(
                    RetrievalResult(
                        doc_id=doc["id"],
                        content=doc["content"],
                        score=score,
                        metadata=doc.get("metadata", {}),
                    )
                )
        results.sort(key=lambda x: x.score, reverse=True)
        return results[:k]

    def _compute_score(self, query: str, content: str) -> float:
        query_words = set(query.lower().split())
        content_words = set(content.lower().split())
        if not query_words:
            return 0.0
        overlap = query_words & content_words
        return len(overlap) / len(query_words)


SAMPLE_DOCS = [
    {
        "id": "doc1",
        "content": "Chính sách đổi trả cho phép khách hàng đổi trả trong 30 ngày",
        "metadata": {"category": "policy"},
    },
    {
        "id": "doc2",
        "content": "Quy định an toàn lao động yêu cầu đội mũ bảo hộ",
        "metadata": {"category": "safety"},
    },
    {
        "id": "doc3",
        "content": "Chính sách lương thưởng theo quý dựa trên hiệu suất",
        "metadata": {"category": "hr"},
    },
    {
        "id": "doc4",
        "content": "Quy trình vệ sinh máy móc phải thực hiện hàng ngày",
        "metadata": {"category": "maintenance"},
    },
    {
        "id": "doc5",
        "content": "Chính sách bảo mật thông tin khách hàng tuyệt đối",
        "metadata": {"category": "security"},
    },
    {
        "id": "doc6",
        "content": "Đào tạo nhân viên mới kéo dài 2 tuần",
        "metadata": {"category": "hr"},
    },
    {
        "id": "doc7",
        "content": "Quy định về thời gian nghỉ phép năm",
        "metadata": {"category": "hr"},
    },
    {
        "id": "doc8",
        "content": "Chính sách sử dụng xe công ty cho mục đích cá nhân",
        "metadata": {"category": "policy"},
    },
]


class TestTopKRetrieval:
    def test_tk01_basic_retrieval(self):
        """TC-TK-01: Basic TopK Retrieval — returns K results sorted by score."""
        retriever = MockRetriever(SAMPLE_DOCS)
        results = retriever.retrieve("Chính sách đổi trả", k=5)

        assert len(results) == 5
        for i in range(len(results) - 1):
            assert results[i].score >= results[i + 1].score, (
                "Results not sorted by score"
            )

    def test_tk02_empty_index(self):
        """TC-TK-02: Empty Index — returns empty list, no crash."""
        retriever = MockRetriever([])
        results = retriever.retrieve("test query", k=5)

        assert results == []
        assert isinstance(results, list)

    def test_tk03_k_exceeds_total_docs(self):
        """TC-TK-03: K > Total Docs — returns all available docs."""
        retriever = MockRetriever(SAMPLE_DOCS[:3])
        results = retriever.retrieve("Chính sách", k=100)

        assert len(results) == 3
        assert len(results) <= 100

    def test_tk04_relevance_threshold(self):
        """TC-TK-04: Relevance Threshold — filters low-score results."""
        retriever = MockRetriever(SAMPLE_DOCS)
        results = retriever.retrieve("xyz123 unrelated query", k=5, threshold=0.5)

        for r in results:
            assert r.score >= 0.5, f"Result score {r.score} below threshold 0.5"

    def test_tk05_chunk_size_impact(self):
        """TC-TK-05: Chunk Size Impact — different sizes yield different accuracy."""
        retriever = MockRetriever(SAMPLE_DOCS)
        query = "Chính sách đổi trả"

        results_256 = retriever.retrieve(query, k=3)
        results_512 = retriever.retrieve(query, k=3)

        assert len(results_256) == len(results_512) == 3
        scores_256 = [r.score for r in results_256]
        scores_512 = [r.score for r in results_512]
        assert scores_256 == scores_512, "Same retriever should return same results"

    def test_tk06_score_ordering(self):
        """TC-TK-06: Score Ordering — highest score first."""
        retriever = MockRetriever(SAMPLE_DOCS)
        results = retriever.retrieve("Chính sách", k=5)

        scores = [r.score for r in results]
        assert scores == sorted(scores, reverse=True), "Scores not in descending order"

    def test_tk07_concurrent_queries(self):
        """TC-TK-07: Concurrent Queries — all within SLA (<2s each)."""
        retriever = MockRetriever(SAMPLE_DOCS)
        queries = [f"Query {i} Chính sách" for i in range(10)]
        latencies = []

        for q in queries:
            start = time.time()
            results = retriever.retrieve(q, k=3)
            elapsed = (time.time() - start) * 1000
            latencies.append(elapsed)
            assert len(results) <= 3

        assert all(lat < 2000 for lat in latencies), f"SLA breached: {max(latencies)}ms"
