"""BenchmarkRunner — runs configurable benchmarks, collects cost + latency data."""

import logging
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from .cost_tracker import cost_tracker
from .latency_profiler import latency_profiler, ProfileSpan
from .models import get_hardware_cost_estimate

logger = logging.getLogger(__name__)


@dataclass
class BenchmarkQuery:
    id: str
    query: str
    document_ids: List[str]
    expected_model: str = ""
    max_latency_ms: float = 30000
    max_cost_usd: float = 0.05


@dataclass
class BenchmarkResult:
    query_id: str
    query_text: str
    latency_ms: float
    cost_usd: float
    model_used: str
    confidence: float
    spans_count: int
    passed: bool
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query_id": self.query_id,
            "query_text": self.query_text[:100],
            "latency_ms": round(self.latency_ms, 2),
            "cost_usd": round(self.cost_usd, 6),
            "model_used": self.model_used,
            "confidence": round(self.confidence, 4),
            "spans_count": self.spans_count,
            "passed": self.passed,
            "error": self.error,
        }


@dataclass
class BenchmarkReport:
    run_id: str
    queries: List[BenchmarkResult]
    total_queries: int
    passed_queries: int
    avg_latency_ms: float
    p95_latency_ms: float
    total_cost_usd: float
    avg_cost_per_query: float
    projected_monthly_cost: float
    latency_summary: Optional[Dict[str, Any]]
    hardware_estimates: Dict[str, Any]
    duration_ms: float
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "total_queries": self.total_queries,
            "passed_queries": self.passed_queries,
            "pass_rate": round(self.passed_queries / max(self.total_queries, 1), 4),
            "avg_latency_ms": round(self.avg_latency_ms, 2),
            "p95_latency_ms": round(self.p95_latency_ms, 2),
            "total_cost_usd": round(self.total_cost_usd, 4),
            "avg_cost_per_query": round(self.avg_cost_per_query, 6),
            "projected_monthly_cost_usd": round(self.projected_monthly_cost, 2),
            "latency_summary": self.latency_summary,
            "hardware_estimates": self.hardware_estimates,
            "duration_ms": round(self.duration_ms, 2),
            "timestamp": self.timestamp,
            "queries": [q.to_dict() for q in self.queries],
        }


class BenchmarkRunner:
    """Runs a set of benchmark queries and produces a cost/latency report."""

    DEFAULT_QUERIES = [
        BenchmarkQuery(
            id="bm-simple-1",
            query="What is the main topic of my documents?",
            document_ids=[],
        ),
        BenchmarkQuery(
            id="bm-complex-1",
            query="Compare and contrast the key findings across all my documents, providing a detailed analysis with citations.",
            document_ids=[],
            expected_model="complex",
            max_latency_ms=60000,
        ),
        BenchmarkQuery(
            id="bm-retrieval-1",
            query="What specific data or statistics are mentioned in my documents?",
            document_ids=[],
        ),
        BenchmarkQuery(
            id="bm-multidoc-1",
            query="Summarize each document separately and then provide a cross-document synthesis.",
            document_ids=[],
            max_latency_ms=60000,
        ),
    ]

    def __init__(self):
        self.results: List[BenchmarkResult] = []

    async def run(
        self,
        system_under_test: Callable,
        queries: Optional[List[BenchmarkQuery]] = None,
    ) -> BenchmarkReport:
        run_id = f"bench-{uuid.uuid4().hex[:12]}"
        start = time.monotonic()
        queries = queries or self.DEFAULT_QUERIES

        for q in queries:
            try:
                result = await self._run_single(system_under_test, q)
            except Exception as exc:
                result = BenchmarkResult(
                    query_id=q.id,
                    query_text=q.query,
                    latency_ms=0,
                    cost_usd=0,
                    model_used="",
                    confidence=0,
                    spans_count=0,
                    passed=False,
                    error=str(exc),
                )
            self.results.append(result)

        duration_ms = (time.monotonic() - start) * 1000
        passed = [r for r in self.results if r.passed]
        latencies = sorted(r.latency_ms for r in self.results)
        n = len(latencies)

        latency_summary = latency_profiler.get_summary().to_dict() if self.results else None
        hardware = {
            "simple": get_hardware_cost_estimate("llama3.2:3b"),
            "complex": get_hardware_cost_estimate("qwen2.5:32b-instruct"),
            "embedding": get_hardware_cost_estimate("nomic-embed-text"),
        }

        return BenchmarkReport(
            run_id=run_id,
            queries=self.results,
            total_queries=len(self.results),
            passed_queries=len(passed),
            avg_latency_ms=sum(latencies) / n if n else 0,
            p95_latency_ms=latencies[max(0, int(n * 0.95) - 1)] if n else 0,
            total_cost_usd=sum(r.cost_usd for r in self.results),
            avg_cost_per_query=sum(r.cost_usd for r in self.results) / n if n else 0,
            projected_monthly_cost=sum(r.cost_usd for r in self.results) / (
                duration_ms / 1000 / 86400 * 30
            ) if duration_ms > 0 else 0,
            latency_summary=latency_summary,
            hardware_estimates=hardware,
            duration_ms=duration_ms,
        )

    async def _run_single(
        self, sut: Callable, query: BenchmarkQuery
    ) -> BenchmarkResult:
        input_data = {
            "query": query.query,
            "document_ids": query.document_ids,
            "session_id": f"bench-{query.id}",
            "user_id": "bench-user",
        }

        retrieve_span = ProfileSpan("retrieval")
        llm_span = ProfileSpan("llm")
        total_span = ProfileSpan("total")

        async with total_span:
            async with retrieve_span:
                pass
            async with llm_span:
                output = await sut(input_data)

        spans = [retrieve_span.to_span(), llm_span.to_span(), total_span.to_span()]

        latency_profiler.record(query.id, spans)
        cost_tracker.track(
            query_id=query.id,
            model=query.expected_model or "llama3.2:3b",
            input_text=query.query,
            output_text=output.get("final_answer", "") or output.get("answer", ""),
        )

        cost_summary = cost_tracker.get_summary(last_n=1)
        per_query_cost = cost_summary.avg_cost_per_query if cost_summary.total_queries > 0 else 0

        latency = total_span.duration_ms
        confidence = output.get("confidence_score", 0.0)
        has_answer = bool(output.get("final_answer", "") or output.get("answer", ""))
        passed = has_answer and latency <= query.max_latency_ms

        return BenchmarkResult(
            query_id=query.id,
            query_text=query.query,
            latency_ms=latency,
            cost_usd=per_query_cost,
            model_used=query.expected_model or "llama3.2:3b",
            confidence=confidence,
            spans_count=len(spans),
            passed=passed,
        )
