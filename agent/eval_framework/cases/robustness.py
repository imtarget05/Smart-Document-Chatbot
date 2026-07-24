"""Eval cases for robustness: edge cases, empty queries, special characters."""

from typing import Any, Dict

from ..core import EvalCase, EvalMetric, EvalResult


class RobustnessEvalCase(EvalCase):
    """Tests system behaviour on edge-case inputs."""

    EDGE_CASES = [
        ("empty_query", ""),
        ("whitespace_only", "   "),
        ("very_long", "A" * 10000),
        ("special_chars", "!@#$%^&*()_+{}|:\"<>?~`-=[]\\;',./"),
        ("html_injection", "<script>alert('xss')</script>"),
        ("sql_injection", "' OR 1=1; DROP TABLE users; --"),
        ("unicode_control", "\u0000\u0001\u0002\u0003"),
        ("emoticons", "😀🎉🔥💯🚀"),
    ]

    def __init__(
        self,
        case_id: str,
        name: str,
        edge_type: str,
        edge_input: str,
        document_ids: list[str] = None,
        expects_error: bool = False,
        importance: float = 1.0,
    ):
        super().__init__(case_id, name, importance=importance)
        self.edge_type = edge_type
        self.edge_input = edge_input
        self.document_ids = document_ids or []
        self.expects_error = expects_error

    async def build_input(self) -> Dict[str, Any]:
        return {
            "query": self.edge_input,
            "document_ids": self.document_ids,
            "session_id": f"eval-robust-{self.case_id}",
            "user_id": "eval-user",
        }

    @classmethod
    def create_all(cls, document_ids: list[str] = None) -> list["RobustnessEvalCase"]:
        cases = []
        for idx, (etype, einput) in enumerate(cls.EDGE_CASES):
            expects_err = etype in ("empty_query", "whitespace_only")
            cases.append(cls(
                case_id=f"robust-{idx}",
                name=f"Edge: {etype}",
                edge_type=etype,
                edge_input=einput,
                document_ids=document_ids,
                expects_error=expects_err,
                importance=1.0,
            ))
        return cases

    async def score(self, input_data: Dict[str, Any], output_data: Dict[str, Any], latency_ms: float) -> EvalResult:
        answer = output_data.get("final_answer", "") or output_data.get("answer", "")
        error = output_data.get("error", "")
        error_raised = bool(error) or latency_ms < 100

        if self.expects_error:
            properly_handled = error_raised or (
                not answer.strip() or
                any(p in answer.lower() for p in ["invalid", "empty", "please provide", "vui lòng"])
            )
            metrics = [
                EvalMetric("graceful_rejection", 1.0 if properly_handled else 0.0, weight=1.0, threshold=1.0),
            ]
            return EvalResult(
                case_id=self.case_id,
                case_name=self.name,
                suite_name="",
                passed=properly_handled,
                score=1.0 if properly_handled else 0.0,
                metrics=metrics,
                input_data=input_data,
                output_data={"error_raised": error_raised, "properly_handled": properly_handled},
                latency_ms=latency_ms,
            )

        answer_given = bool(answer.strip())
        no_crash = not error_raised
        metrics = [
            EvalMetric("no_crash", 1.0 if no_crash else 0.0, weight=0.6, threshold=1.0),
            EvalMetric("has_answer", 1.0 if answer_given else 0.0, weight=0.4, threshold=1.0),
        ]
        overall = sum(m.value * m.weight for m in metrics) / sum(m.weight for m in metrics)
        return EvalResult(
            case_id=self.case_id,
            case_name=self.name,
            suite_name="",
            passed=no_crash and answer_given,
            score=overall,
            metrics=metrics,
            input_data=input_data,
            output_data={"error_raised": error_raised, "answer_given": answer_given},
            latency_ms=latency_ms,
        )
