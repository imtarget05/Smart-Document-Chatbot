#!/usr/bin/env python3
"""LLM-Judge Evaluation (Ragas-style).

Uses the project's existing LLM (via Cloudflare Workers AI or Ollama) as a judge
to score RAG answers on multiple dimensions:

- Faithfulness: does the answer follow from the context?
- Relevance: does the answer address the question?
- Completeness: does it cover all required concepts?
- Tone: is the tone appropriate?

Each metric returns a structured score (0-1) with an explanation.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, asdict
from typing import Any, Optional, Sequence


# ---------------------------------------------------------------------------
# Optional LLM imports — graceful fallback
# ---------------------------------------------------------------------------
try:
    from langchain_ollama import ChatOllama

    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False

try:
    import httpx

    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------
@dataclass
class JudgeScore:
    """A single judge evaluation result."""

    score: float  # 0.0 – 1.0
    explanation: str
    metric: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class JudgeResult:
    """Aggregated judge evaluation for one Q/A pair."""

    faithfulness: Optional[JudgeScore] = None
    relevance: Optional[JudgeScore] = None
    completeness: Optional[JudgeScore] = None
    tone: Optional[JudgeScore] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            k: v.to_dict() if v else None
            for k, v in (
                ("faithfulness", self.faithfulness),
                ("relevance", self.relevance),
                ("completeness", self.completeness),
                ("tone", self.tone),
            )
        }

    @property
    def average_score(self) -> Optional[float]:
        scores = [
            s.score
            for s in (self.faithfulness, self.relevance, self.completeness, self.tone)
            if s is not None
        ]
        return round(sum(scores) / len(scores), 4) if scores else None


# ---------------------------------------------------------------------------
# LLM Client
# ---------------------------------------------------------------------------
class JudgeLLM:
    """Lightweight LLM client for judge evaluations.

    Supports:
    - Ollama-compatible endpoint (default, via langchain-ollama)
    - Cloudflare Workers AI (via direct HTTP)
    - Mock mode (returns canned responses for testing)
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.0,
        mock: bool = False,
    ):
        self.base_url = base_url or os.getenv(
            "LLM_JUDGE_BASE_URL", os.getenv("LLM_BASE_URL", "http://llm-router:8000")
        )
        self.model = model or os.getenv(
            "LLM_JUDGE_MODEL",
            os.getenv("LLM_CHAT_MODEL", "@cf/meta/llama-3.3-70b-instruct-fp8-fast"),
        )
        self.temperature = temperature
        self.mock = mock
        self._client: Any = None

        if not mock and LANGCHAIN_AVAILABLE:
            self._client = ChatOllama(
                base_url=self.base_url,
                model=self.model,
                temperature=self.temperature,
            )

    def complete(self, prompt: str) -> str:
        """Send a prompt and return the response text."""
        if self.mock:
            return self._mock_response(prompt)

        if self._client is not None:
            response = self._client.invoke(prompt)
            return response.content if hasattr(response, "content") else str(response)

        if HTTPX_AVAILABLE:
            # Direct HTTP to Ollama-compatible endpoint
            resp = httpx.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": self.temperature},
                },
                timeout=120,
            )
            resp.raise_for_status()
            return resp.json().get("response", "")

        raise RuntimeError(
            "No LLM client available. Install langchain-ollama or httpx, "
            "or use mock=True for testing."
        )

    def _mock_response(self, prompt: str) -> str:
        """Generate a deterministic mock response based on prompt content."""
        if "faithful" in prompt.lower():
            return json.dumps({"score": 0.85, "explanation": "Mock: answer is faithful to context."})
        if "relevant" in prompt.lower():
            return json.dumps({"score": 0.9, "explanation": "Mock: answer is relevant to question."})
        if "complete" in prompt.lower():
            return json.dumps({"score": 0.75, "explanation": "Mock: answer covers most concepts."})
        if "tone" in prompt.lower():
            return json.dumps({"score": 0.95, "explanation": "Mock: tone is appropriate."})
        return json.dumps({"score": 0.5, "explanation": "Mock: generic response."})


# ---------------------------------------------------------------------------
# Judge prompts
# ---------------------------------------------------------------------------
FAITHFULNESS_PROMPT = """You are an expert evaluator. Determine if the following answer is faithful to the given context.
A faithful answer only contains information that can be directly inferred from or is supported by the context.

Context:
{context}

Answer:
{answer}

Respond with a JSON object: {{"score": <0.0 to 1.0>, "explanation": "<brief reason>"}}
Score 1.0 = fully faithful, 0.0 = completely unfaithful (hallucination).
"""

RELEVANCE_PROMPT = """You are an expert evaluator. Determine if the following answer is relevant to the question.

Question:
{question}

Answer:
{answer}

Respond with a JSON object: {{"score": <0.0 to 1.0>, "explanation": "<brief reason>"}}
Score 1.0 = fully relevant, 0.0 = completely irrelevant.
"""

COMPLETENESS_PROMPT = """You are an expert evaluator. Determine if the following answer covers all the required concepts.

Question:
{question}

Required concepts (comma-separated):
{concepts}

Answer:
{answer}

Respond with a JSON object: {{"score": <0.0 to 1.0>, "explanation": "<brief reason>"}}
Score 1.0 = all concepts covered, 0.0 = none covered.
"""

TONE_PROMPT = """You are an expert evaluator. Determine if the tone of the answer is appropriate.

Expected tone: {expected_tone}

Answer:
{answer}

Respond with a JSON object: {{"score": <0.0 to 1.0>, "explanation": "<brief reason>"}}
Score 1.0 = tone is perfectly appropriate, 0.0 = completely inappropriate.
"""


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------
def _parse_judge_json(text: str) -> tuple[float, str]:
    """Extract score and explanation from judge JSON response."""
    # Try to find JSON object in the response
    match = re.search(r"\{[^}]+\}", text, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group())
            score = float(data.get("score", 0.5))
            explanation = str(data.get("explanation", "No explanation provided."))
            return max(0.0, min(1.0, score)), explanation
        except (json.JSONDecodeError, ValueError):
            pass

    # Fallback: look for a number in the text
    num_match = re.search(r"(\d+\.?\d*)", text)
    if num_match:
        try:
            score = float(num_match.group(1))
            return max(0.0, min(1.0, score)), text.strip()[:200]
        except ValueError:
            pass

    return 0.5, f"Could not parse judge response: {text[:200]}"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
class LLMJudge:
    """LLM-based judge for RAG evaluation."""

    def __init__(
        self,
        llm: Optional[JudgeLLM] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        mock: bool = False,
    ):
        self.llm = llm or JudgeLLM(base_url=base_url, model=model, mock=mock)

    def evaluate_faithfulness(self, answer: str, context: str) -> JudgeScore:
        """Score whether the answer follows from the context."""
        prompt = FAITHFULNESS_PROMPT.format(context=context, answer=answer)
        response = self.llm.complete(prompt)
        score, explanation = _parse_judge_json(response)
        return JudgeScore(score=score, explanation=explanation, metric="faithfulness")

    def evaluate_relevance(self, question: str, answer: str) -> JudgeScore:
        """Score whether the answer addresses the question."""
        prompt = RELEVANCE_PROMPT.format(question=question, answer=answer)
        response = self.llm.complete(prompt)
        score, explanation = _parse_judge_json(response)
        return JudgeScore(score=score, explanation=explanation, metric="relevance")

    def evaluate_completeness(
        self, question: str, answer: str, expected_concepts: Sequence[str]
    ) -> JudgeScore:
        """Score whether the answer covers all required concepts."""
        concepts_str = ", ".join(expected_concepts)
        prompt = COMPLETENESS_PROMPT.format(
            question=question, concepts=concepts_str, answer=answer
        )
        response = self.llm.complete(prompt)
        score, explanation = _parse_judge_json(response)
        return JudgeScore(score=score, explanation=explanation, metric="completeness")

    def evaluate_tone(self, answer: str, expected_tone: str = "professional") -> JudgeScore:
        """Score whether the tone is appropriate."""
        prompt = TONE_PROMPT.format(expected_tone=expected_tone, answer=answer)
        response = self.llm.complete(prompt)
        score, explanation = _parse_judge_json(response)
        return JudgeScore(score=score, explanation=explanation, metric="tone")

    def evaluate_all(
        self,
        question: str,
        answer: str,
        context: str = "",
        expected_concepts: Optional[Sequence[str]] = None,
        expected_tone: str = "professional",
    ) -> JudgeResult:
        """Run all enabled evaluations and return aggregated result."""
        result = JudgeResult()

        if context:
            result.faithfulness = self.evaluate_faithfulness(answer, context)

        result.relevance = self.evaluate_relevance(question, answer)

        if expected_concepts:
            result.completeness = self.evaluate_completeness(
                question, answer, expected_concepts
            )

        result.tone = self.evaluate_tone(answer, expected_tone)
        return result


# ---------------------------------------------------------------------------
# Convenience functions (module-level)
# ---------------------------------------------------------------------------
_default_judge: Optional[LLMJudge] = None


def _get_default_judge(mock: bool = False) -> LLMJudge:
    global _default_judge
    if _default_judge is None:
        _default_judge = LLMJudge(mock=mock)
    return _default_judge


def evaluate_faithfulness(answer: str, context: str, mock: bool = False) -> JudgeScore:
    """Module-level convenience: score faithfulness."""
    return _get_default_judge(mock=mock).evaluate_faithfulness(answer, context)


def evaluate_relevance(question: str, answer: str, mock: bool = False) -> JudgeScore:
    """Module-level convenience: score relevance."""
    return _get_default_judge(mock=mock).evaluate_relevance(question, answer)


def evaluate_completeness(
    question: str, answer: str, expected_concepts: Sequence[str], mock: bool = False
) -> JudgeScore:
    """Module-level convenience: score completeness."""
    return _get_default_judge(mock=mock).evaluate_completeness(
        question, answer, expected_concepts
    )


def evaluate_tone(answer: str, expected_tone: str = "professional", mock: bool = False) -> JudgeScore:
    """Module-level convenience: score tone."""
    return _get_default_judge(mock=mock).evaluate_tone(answer, expected_tone)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main():
    import argparse

    parser = argparse.ArgumentParser(description="LLM Judge Evaluation")
    parser.add_argument("--question", required=True, help="The question")
    parser.add_argument("--answer", required=True, help="The answer to evaluate")
    parser.add_argument("--context", default="", help="Retrieved context (for faithfulness)")
    parser.add_argument("--concepts", nargs="*", help="Expected concepts (for completeness)")
    parser.add_argument("--tone", default="professional", help="Expected tone")
    parser.add_argument("--mock", action="store_true", help="Use mock LLM")
    parser.add_argument("--base-url", help="LLM base URL")
    parser.add_argument("--model", help="LLM model name")
    args = parser.parse_args()

    judge = LLMJudge(base_url=args.base_url, model=args.model, mock=args.mock)
    result = judge.evaluate_all(
        question=args.question,
        answer=args.answer,
        context=args.context,
        expected_concepts=args.concepts,
        expected_tone=args.tone,
    )

    print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
    if result.average_score is not None:
        print(f"\nAverage score: {result.average_score:.4f}")


if __name__ == "__main__":
    main()
