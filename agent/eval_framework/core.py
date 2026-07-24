"""
Eval Framework — pluggable evaluation for RAG/agentic systems.

Architecture:
  EvalSuite  (a collection of related scenarios)
    └── EvalCase  (one test: input → expected → actual → score)
          └── EvalResult  (structured outcome with metrics)
                └── EvalReport  (aggregated across all cases/suites)

Scoring conventions:
  - All metric values are normalised to [0.0, 1.0] where 1.0 is perfect.
  - A case passes iff its overall score >= the suite's pass_threshold.
  - Scores are weighted averages of sub-scores (weighted by case importance).
"""

import json
import logging
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ── Result types ──────────────────────────────────────────────────────────


@dataclass
class EvalMetric:
    name: str
    value: float
    weight: float = 1.0
    threshold: Optional[float] = None
    passed: Optional[bool] = None
    details: str = ""

    def __post_init__(self):
        if self.threshold is not None:
            self.passed = self.value >= self.threshold


@dataclass
class EvalResult:
    case_id: str
    case_name: str
    suite_name: str
    passed: bool
    score: float
    metrics: List[EvalMetric]
    input_data: Dict[str, Any] = field(default_factory=dict)
    output_data: Dict[str, Any] = field(default_factory=dict)
    latency_ms: float = 0.0
    error: Optional[str] = None
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "case_id": self.case_id,
            "case_name": self.case_name,
            "suite_name": self.suite_name,
            "passed": self.passed,
            "score": round(self.score, 4),
            "metrics": [
                {
                    "name": m.name,
                    "value": round(m.value, 4),
                    "weight": m.weight,
                    "threshold": m.threshold,
                    "passed": m.passed,
                    "details": m.details,
                }
                for m in self.metrics
            ],
            "latency_ms": round(self.latency_ms, 2),
            "error": self.error,
            "timestamp": self.timestamp,
        }


@dataclass
class EvalReport:
    run_id: str
    suite_name: str
    total_cases: int
    passed_cases: int
    overall_score: float
    results: List[EvalResult]
    duration_ms: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "suite_name": self.suite_name,
            "total_cases": self.total_cases,
            "passed_cases": self.passed_cases,
            "failed_cases": self.total_cases - self.passed_cases,
            "overall_score": round(self.overall_score, 4),
            "pass_rate": round(self.passed_cases / max(self.total_cases, 1), 4),
            "duration_ms": round(self.duration_ms, 2),
            "results": [r.to_dict() for r in self.results],
            "metadata": self.metadata,
            "timestamp": self.timestamp,
        }

    def to_markdown(self) -> str:
        lines = [
            f"# Eval Report: {self.suite_name}",
            f"**Run ID:** {self.run_id}  ",
            f"**Date:** {self.timestamp}  ",
            f"**Duration:** {self.duration_ms:.0f}ms  ",
            "",
            "## Summary",
            "| Metric | Value |",
            "|--------|-------|",
            f"| Pass Rate | {self.passed_cases}/{self.total_cases} ({self.passed_cases / max(self.total_cases, 1) * 100:.1f}%) |",
            f"| Overall Score | {self.overall_score:.4f} |",
            "",
            "## Results",
        ]
        for r in self.results:
            status = "✅" if r.passed else "❌"
            lines.append(f"### {status} {r.case_name} (`{r.case_id}`)")
            lines.append(f"- Score: {r.score:.4f} | Latency: {r.latency_ms:.1f}ms")
            if r.error:
                lines.append(f"- Error: {r.error}")
            for m in r.metrics:
                check = "✓" if m.passed else "✗" if m.passed is False else "–"
                lines.append(f"  - {check} **{m.name}**: {m.value:.4f} (threshold: {m.threshold})")
            lines.append("")
        return "\n".join(lines)


# ── Base case class ───────────────────────────────────────────────────────


class EvalCase(ABC):
    """One evaluation test case. Subclasses define input and scoring."""

    def __init__(
        self,
        case_id: str,
        name: str,
        description: str = "",
        importance: float = 1.0,
    ):
        self.case_id = case_id
        self.name = name
        self.description = description
        self.importance = importance

    @abstractmethod
    async def build_input(self) -> Dict[str, Any]:
        """Return the input dict to send to the system under test."""

    @abstractmethod
    async def score(self, input_data: Dict[str, Any], output_data: Dict[str, Any], latency_ms: float) -> EvalResult:
        """Score the system's response and return an EvalResult."""

    async def run(self, system_under_test: Any) -> EvalResult:
        start = time.monotonic()
        input_data = await self.build_input()
        try:
            output_data = await system_under_test(input_data)
        except Exception as exc:
            latency_ms = (time.monotonic() - start) * 1000
            return EvalResult(
                case_id=self.case_id,
                case_name=self.name,
                suite_name="",
                passed=False,
                score=0.0,
                metrics=[],
                input_data=input_data,
                latency_ms=latency_ms,
                error=str(exc),
            )
        latency_ms = (time.monotonic() - start) * 1000
        return await self.score(input_data, output_data, latency_ms)


# ── Suite ─────────────────────────────────────────────────────────────────


class EvalSuite:
    """A collection of EvalCases that test one aspect of the system."""

    def __init__(
        self,
        name: str,
        description: str = "",
        pass_threshold: float = 0.7,
        cases: Optional[List[EvalCase]] = None,
    ):
        self.name = name
        self.description = description
        self.pass_threshold = pass_threshold
        self.cases = cases or []

    def add_case(self, case: EvalCase):
        self.cases.append(case)

    async def run(self, system_under_test: Any) -> EvalReport:
        run_id = f"eval-{uuid.uuid4().hex[:12]}"
        start = time.monotonic()
        results: List[EvalResult] = []
        for case in self.cases:
            result = await case.run(system_under_test)
            result.suite_name = self.name
            results.append(result)
            logger.info(
                "Eval case %s: score=%.4f passed=%s latency=%.1fms",
                case.case_id,
                result.score,
                result.passed,
                result.latency_ms,
            )

        duration_ms = (time.monotonic() - start) * 1000
        passed = [r for r in results if r.passed]
        total_weight = sum(
            c.importance for c in self.cases if c.importance > 0
        ) or 1.0
        weighted_score = sum(
            r.score * c.importance
            for r, c in zip(results, self.cases)
            if c.importance > 0
        ) / total_weight

        return EvalReport(
            run_id=run_id,
            suite_name=self.name,
            total_cases=len(results),
            passed_cases=len(passed),
            overall_score=weighted_score,
            results=results,
            duration_ms=duration_ms,
            metadata={"pass_threshold": self.pass_threshold, "description": self.description},
        )


# ── Runner ────────────────────────────────────────────────────────────────


class EvalRunner:
    """Orchestrates multiple suites and aggregates reports."""

    def __init__(self, output_dir: str = "eval_framework/reports"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    async def run_suite(self, suite: EvalSuite, system_under_test: Any) -> EvalReport:
        report = await suite.run(system_under_test)
        self._save(report)
        return report

    async def run_all(
        self, suites: List[EvalSuite], system_under_test: Any
    ) -> List[EvalReport]:
        return [await self.run_suite(s, system_under_test) for s in suites]

    def _save(self, report: EvalReport):
        path = self.output_dir / f"{report.run_id}.json"
        with open(path, "w") as f:
            json.dump(report.to_dict(), f, indent=2, ensure_ascii=False)
        logger.info("Eval report saved to %s", path)
