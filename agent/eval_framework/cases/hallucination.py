"""Eval cases for hallucination detection: factuality, citation faithfulness."""

import re
from typing import Any, Dict, List

from ..core import EvalCase, EvalMetric, EvalResult


class HallucinationEvalCase(EvalCase):
    """Tests whether the system hallucinates — i.e., makes claims not grounded in retrieved docs."""

    HALLUCINATION_PATTERNS = [
        r"\bI think\b",
        r"\bI believe\b",
        r"\bin my opinion\b",
        r"\bpossibly\b",
        r"\bmaybe\b",
        r"\bprobably\b",
        r"\bnot sure\b",
        r"\bcould be\b",
        r"\bmight be\b",
    ]

    def __init__(
        self,
        case_id: str,
        name: str,
        query: str,
        document_ids: List[str],
        expected_source_keywords: List[str],
        unknown_query: bool = False,
        importance: float = 1.0,
    ):
        super().__init__(case_id, name, importance=importance)
        self.query = query
        self.document_ids = document_ids
        self.expected_source_keywords = expected_source_keywords
        self.unknown_query = unknown_query

    async def build_input(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "document_ids": self.document_ids,
            "session_id": f"eval-hal-{self.case_id}",
            "user_id": "eval-user",
        }

    async def score(self, input_data: Dict[str, Any], output_data: Dict[str, Any], latency_ms: float) -> EvalResult:
        answer = output_data.get("final_answer", "") or output_data.get("answer", "")
        chunks = output_data.get("retrieved_chunks", []) or output_data.get("sources", [])

        if self.unknown_query:
            hallucinated = self._has_hallucination_patterns(answer)
            metrics = [
                EvalMetric("refuses_to_answer", 1.0 if hallucinated else 0.0, weight=0.7, threshold=0.0),
                EvalMetric("no_fabrication", 0.0 if hallucinated else 1.0, weight=0.3, threshold=1.0),
            ]
            overall = sum(m.value * m.weight for m in metrics) / sum(m.weight for m in metrics)
            return EvalResult(
                case_id=self.case_id,
                case_name=self.name,
                suite_name="",
                passed=not hallucinated,
                score=overall,
                metrics=metrics,
                input_data=input_data,
                output_data={"hallucination_patterns_found": hallucinated},
                latency_ms=latency_ms,
            )

        chunk_texts = [c.get("text", "") or c.get("chunk_text", "") for c in chunks]
        chunk_text = " ".join(chunk_texts)

        if not chunk_text.strip():
            return EvalResult(
                case_id=self.case_id,
                case_name=self.name,
                suite_name="",
                passed=False,
                score=0.0,
                metrics=[EvalMetric("no_chunks_retrieved", 0.0, weight=1.0, threshold=1.0)],
                input_data=input_data,
                latency_ms=latency_ms,
                error="No chunks retrieved — cannot evaluate hallucination",
            )

        keyword_hits = sum(
            1 for kw in self.expected_source_keywords
            if kw.lower() in answer.lower()
        )
        groundedness = keyword_hits / max(len(self.expected_source_keywords), 1)

        hal_pattern_hits = bool(re.search("|".join(self.HALLUCINATION_PATTERNS), answer, re.I))

        sentence_count = max(len(re.findall(r"[.!?]+", answer)), 1)
        claims_without_source = self._count_unsubstantiated_claims(answer, chunk_text)

        metrics = [
            EvalMetric("groundedness", groundedness, weight=0.5, threshold=0.5),
            EvalMetric("no_hallucination_patterns", 0.0 if hal_pattern_hits else 1.0, weight=0.2, threshold=1.0),
            EvalMetric("claim_grounding_ratio", max(0.0, 1.0 - claims_without_source / sentence_count), weight=0.3, threshold=0.5),
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
            output_data={"hallucination_patterns": hal_pattern_hits, "keyword_hits": keyword_hits},
            latency_ms=latency_ms,
        )

    def _has_hallucination_patterns(self, text: str) -> bool:
        return bool(re.search("|".join(self.HALLUCINATION_PATTERNS), text, re.I))

    def _count_unsubstantiated_claims(self, answer: str, context: str) -> int:
        sentences = re.split(r"[.!?]+", answer)
        count = 0
        for s in sentences:
            s = s.strip()
            if len(s) < 20:
                continue
            words = set(w.lower() for w in re.findall(r"\w+", s) if len(w) > 3)
            if not words:
                continue
            match_count = sum(1 for w in words if w in context.lower())
            if match_count / len(words) < 0.3:
                count += 1
        return count
