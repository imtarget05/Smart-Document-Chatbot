"""Eval cases for answer quality: correctness, completeness, conciseness."""

from typing import Any, Dict, List

from ..core import EvalCase, EvalMetric, EvalResult


class AnswerQualityEvalCase(EvalCase):
    """Tests whether the generated answer is correct, complete, and concise."""

    def __init__(
        self,
        case_id: str,
        name: str,
        query: str,
        document_ids: List[str],
        expected_answer_keywords: List[str],
        forbidden_keywords: List[str] = None,
        min_answer_words: int = 10,
        max_answer_words: int = 2000,
        importance: float = 1.0,
    ):
        super().__init__(case_id, name, importance=importance)
        self.query = query
        self.document_ids = document_ids
        self.expected_answer_keywords = expected_answer_keywords
        self.forbidden_keywords = forbidden_keywords or []
        self.min_answer_words = min_answer_words
        self.max_answer_words = max_answer_words

    async def build_input(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "document_ids": self.document_ids,
            "session_id": f"eval-answer-{self.case_id}",
            "user_id": "eval-user",
        }

    async def score(self, input_data: Dict[str, Any], output_data: Dict[str, Any], latency_ms: float) -> EvalResult:
        answer = output_data.get("final_answer", "") or output_data.get("answer", "")
        confidence = output_data.get("confidence_score", 0.0)
        sources = output_data.get("sources", [])

        keyword_hits = sum(
            1 for kw in self.expected_answer_keywords
            if kw.lower() in answer.lower()
        )
        correctness = keyword_hits / max(len(self.expected_answer_keywords), 1)

        forbidden_hits = sum(
            1 for kw in self.forbidden_keywords
            if kw.lower() in answer.lower()
        )
        forbidden_penalty = 1.0 - (forbidden_hits / max(len(self.forbidden_keywords), 1))

        word_count = len(answer.split())
        length_score = 0.0
        if self.min_answer_words <= word_count <= self.max_answer_words:
            length_score = 1.0
        elif word_count < self.min_answer_words:
            length_score = word_count / self.min_answer_words
        else:
            length_score = max(0.0, 1.0 - (word_count - self.max_answer_words) / self.max_answer_words)

        has_citations = bool(sources)
        citation_coverage = 1.0 if has_citations else 0.0
        if sources:
            cited_docs = set()
            for s in sources:
                name = s.get("document_name", "")
                if name and name.lower() in answer.lower():
                    cited_docs.add(name)
            citation_coverage = len(cited_docs) / max(len(sources), 1)

        metrics = [
            EvalMetric("answer_correctness", correctness, weight=0.5, threshold=0.5),
            EvalMetric("forbidden_keyword_penalty", forbidden_penalty, weight=0.15, threshold=0.8),
            EvalMetric("length_score", length_score, weight=0.1, threshold=0.5),
            EvalMetric("citation_coverage", citation_coverage, weight=0.15, threshold=0.5),
            EvalMetric("confidence", min(confidence, 1.0), weight=0.1, threshold=0.3),
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
            output_data={"answer_length": word_count, "keyword_hits": keyword_hits, "citation_count": len(sources)},
            latency_ms=latency_ms,
        )
