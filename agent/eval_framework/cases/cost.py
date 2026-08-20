"""Eval cases for cost efficiency: token usage, estimated dollar cost."""

from typing import Any, Dict

from ..core import EvalCase, EvalMetric, EvalResult


class CostEvalCase(EvalCase):
    """Estimates the dollar cost of a query based on token counts and model pricing."""

    MODEL_PRICING = {
        "@cf/meta/llama-3.3-70b-instruct-fp8-fast": {"input": 0.15, "output": 0.15},
        "@cf/baai/bge-base-en-v1.5": {"input": 0.02, "output": 0.02},
    }

    def __init__(
        self,
        case_id: str,
        name: str,
        query: str,
        document_ids: list[str],
        max_cost_usd: float = 0.05,
        model: str = "@cf/meta/llama-3.3-70b-instruct-fp8-fast",
        importance: float = 1.0,
    ):
        super().__init__(case_id, name, importance=importance)
        self.query = query
        self.document_ids = document_ids
        self.max_cost_usd = max_cost_usd
        self.model = model

    async def build_input(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "document_ids": self.document_ids,
            "session_id": f"eval-cost-{self.case_id}",
            "user_id": "eval-user",
        }

    async def score(self, input_data: Dict[str, Any], output_data: Dict[str, Any], latency_ms: float) -> EvalResult:
        answer = output_data.get("final_answer", "") or output_data.get("answer", "")
        pricing = self.MODEL_PRICING.get(self.model, {"input": 0.15, "output": 0.15})

        input_tokens = len(input_data.get("query", "").split()) * 1.3
        output_tokens = len(answer.split()) * 1.3
        cost = (input_tokens / 1000 * pricing["input"]) + (output_tokens / 1000 * pricing["output"])

        under_budget = cost <= self.max_cost_usd
        normalized_cost = 1.0 - (cost / self.max_cost_usd) if cost > 0 else 1.0
        normalized_cost = max(0.0, min(1.0, normalized_cost))

        metrics = [
            EvalMetric("estimated_cost_usd", normalized_cost, weight=0.5, threshold=0.5),
            EvalMetric("under_budget", 1.0 if under_budget else 0.0, weight=0.3, threshold=1.0),
            EvalMetric("output_tokens", min(1.0, 1000 / max(output_tokens, 1)), weight=0.2, threshold=0.3),
        ]
        overall = sum(m.value * m.weight for m in metrics) / sum(m.weight for m in metrics)
        return EvalResult(
            case_id=self.case_id,
            case_name=self.name,
            suite_name="",
            passed=under_budget,
            score=overall,
            metrics=metrics,
            input_data=input_data,
            output_data={
                "estimated_cost_usd": round(cost, 6),
                "input_tokens": int(input_tokens),
                "output_tokens": int(output_tokens),
                "model": self.model,
            },
            latency_ms=latency_ms,
        )
