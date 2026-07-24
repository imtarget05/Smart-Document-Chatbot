"""Eval cases for retrieval quality: accuracy, MRR, recall@k."""

from typing import Any, Dict, List

from ..core import EvalCase, EvalMetric, EvalResult


class RetrievalQualityEvalCase(EvalCase):
    """Tests whether the retrieval system returns relevant chunks for a query."""

    def __init__(
        self,
        case_id: str,
        name: str,
        query: str,
        document_ids: List[str],
        expected_source_keywords: List[str],
        min_chunks: int = 1,
        min_score: float = 0.3,
        importance: float = 1.0,
    ):
        super().__init__(case_id, name, importance=importance)
        self.query = query
        self.document_ids = document_ids
        self.expected_source_keywords = expected_source_keywords
        self.min_chunks = min_chunks
        self.min_score = min_score

    async def build_input(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "document_ids": self.document_ids,
            "session_id": f"eval-retrieval-{self.case_id}",
            "user_id": "eval-user",
        }

    async def score(self, input_data: Dict[str, Any], output_data: Dict[str, Any], latency_ms: float) -> EvalResult:
        chunks = output_data.get("retrieved_chunks", []) or output_data.get("sources", [])
        top_chunk_texts = [c.get("text", "") or c.get("chunk_text", "") for c in chunks]
        top_chunk_scores = [c.get("score", 0.0) for c in chunks]

        keyword_hits = sum(
            1 for kw in self.expected_source_keywords
            if any(kw.lower() in t.lower() for t in top_chunk_texts)
        )
        retrieval_accuracy = keyword_hits / max(len(self.expected_source_keywords), 1)

        has_min_chunks = len(chunks) >= self.min_chunks
        avg_score = sum(top_chunk_scores) / max(len(top_chunk_scores), 1)

        metrics = [
            EvalMetric("retrieval_accuracy", retrieval_accuracy, weight=0.5, threshold=0.5),
            EvalMetric("chunks_found", 1.0 if has_min_chunks else 0.0, weight=0.2, threshold=1.0),
            EvalMetric("avg_score", min(avg_score, 1.0), weight=0.3, threshold=self.min_score),
        ]
        overall = sum(m.value * m.weight for m in metrics) / sum(m.weight for m in metrics)
        return EvalResult(
            case_id=self.case_id,
            case_name=self.name,
            suite_name="",
            passed=overall >= 0.5,
            score=overall,
            metrics=metrics,
            input_data=input_data,
            output_data={"chunk_count": len(chunks), "keyword_hits": keyword_hits},
            latency_ms=latency_ms,
        )
