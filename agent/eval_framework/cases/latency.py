"""Eval cases for latency performance: end-to-end, retrieval, LLM."""

from typing import Any, Dict

from ..core import EvalCase, EvalMetric, EvalResult


class LatencyEvalCase(EvalCase):
    """Tests whether the system responds within acceptable latency thresholds."""

    def __init__(
        self,
        case_id: str,
        name: str,
        query: str,
        document_ids: list[str],
        max_total_ms: float = 30000,
        importance: float = 1.0,
    ):
        super().__init__(case_id, name, importance=importance)
        self.query = query
        self.document_ids = document_ids
        self.max_total_ms = max_total_ms

    async def build_input(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "document_ids": self.document_ids,
            "session_id": f"eval-latency-{self.case_id}",
            "user_id": "eval-user",
        }

    async def score(self, input_data: Dict[str, Any], output_data: Dict[str, Any], latency_ms: float) -> EvalResult:
        has_answer = bool(output_data.get("final_answer", "") or output_data.get("answer", ""))

        latency_ok = latency_ms <= self.max_total_ms
        latency_score = 1.0 - (latency_ms / self.max_total_ms) if latency_ms > 0 else 0.0
        latency_score = max(0.0, min(1.0, latency_score))

        metrics = [
            EvalMetric("total_latency_ms", max(0.0, 1.0 - latency_ms / self.max_total_ms), weight=0.6, threshold=0.3),
            EvalMetric("under_max_threshold", 1.0 if latency_ok else 0.0, weight=0.2, threshold=1.0),
            EvalMetric("answer_produced", 1.0 if has_answer else 0.0, weight=0.2, threshold=1.0),
        ]
        overall = sum(m.value * m.weight for m in metrics) / sum(m.weight for m in metrics)
        return EvalResult(
            case_id=self.case_id,
            case_name=self.name,
            suite_name="",
            passed=latency_ok and has_answer,
            score=overall,
            metrics=metrics,
            input_data=input_data,
            output_data={"actual_latency_ms": latency_ms, "under_max": latency_ok},
            latency_ms=latency_ms,
        )
