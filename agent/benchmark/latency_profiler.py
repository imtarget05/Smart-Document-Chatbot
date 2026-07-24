"""Step-by-step latency profiler with context manager support."""

import json
import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class LatencySpan:
    name: str
    start_ms: float
    end_ms: float
    duration_ms: float
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "start_ms": round(self.start_ms, 2),
            "end_ms": round(self.end_ms, 2),
            "duration_ms": round(self.duration_ms, 2),
            "metadata": self.metadata,
        }


@dataclass
class ProfileResult:
    query_id: str
    total_ms: float
    spans: List[LatencySpan]
    breakdown: Dict[str, float]
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query_id": self.query_id,
            "total_ms": round(self.total_ms, 2),
            "spans": [s.to_dict() for s in self.spans],
            "breakdown": {k: round(v, 2) for k, v in sorted(
                self.breakdown.items(), key=lambda x: x[1], reverse=True
            )},
            "timestamp": self.timestamp,
        }


@dataclass
class LatencySummary:
    total_profiles: int
    avg_total_ms: float
    p95_total_ms: float
    p99_total_ms: float
    step_breakdown: Dict[str, Dict[str, float]]
    period_start: str
    period_end: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_profiles": self.total_profiles,
            "avg_total_ms": round(self.avg_total_ms, 2),
            "p95_total_ms": round(self.p95_total_ms, 2),
            "p99_total_ms": round(self.p99_total_ms, 2),
            "step_breakdown": self.step_breakdown,
            "period_start": self.period_start,
            "period_end": self.period_end,
        }


class LatencyProfiler:
    """Profiles query latency with named spans (retrieval, LLM, rerank, total)."""

    def __init__(self, history_dir: str = "benchmark/latency_history"):
        self.history_dir = Path(history_dir)
        self.history_dir.mkdir(parents=True, exist_ok=True)
        self._profiles: List[ProfileResult] = []
        self._load()

    def _load(self):
        for f in sorted(self.history_dir.glob("*.json")):
            try:
                data = json.loads(f.read_text())
                spans = [LatencySpan(**s) for s in data.get("spans", [])]
                self._profiles.append(
                    ProfileResult(
                        query_id=data["query_id"],
                        total_ms=data["total_ms"],
                        spans=spans,
                        breakdown=data.get("breakdown", {}),
                        timestamp=data.get("timestamp", ""),
                    )
                )
            except Exception as exc:
                logger.debug("Failed to load profile %s: %s", f, exc)

    def _save(self, profile: ProfileResult):
        path = self.history_dir / f"{profile.query_id}.json"
        with open(path, "w") as f:
            json.dump(profile.to_dict(), f, indent=2)

    def record(
        self,
        query_id: str,
        spans: List[LatencySpan],
    ) -> ProfileResult:
        total = spans[-1].duration_ms if spans else 0
        breakdown = {}
        for s in spans:
            breakdown[s.name] = s.duration_ms
        profile = ProfileResult(
            query_id=query_id,
            total_ms=total,
            spans=spans,
            breakdown=breakdown,
        )
        self._profiles.append(profile)
        self._save(profile)
        return profile

    def get_summary(self, last_n: Optional[int] = None) -> LatencySummary:
        profiles = self._profiles[-last_n:] if last_n else self._profiles
        if not profiles:
            return LatencySummary(
                total_profiles=0,
                avg_total_ms=0,
                p95_total_ms=0,
                p99_total_ms=0,
                step_breakdown={},
                period_start="",
                period_end="",
            )

        totals = sorted(p.total_ms for p in profiles)
        n = len(totals)
        steps: Dict[str, List[float]] = defaultdict(list)
        for p in profiles:
            for step, dur in p.breakdown.items():
                steps[step].append(dur)

        return LatencySummary(
            total_profiles=n,
            avg_total_ms=sum(totals) / n,
            p95_total_ms=totals[max(0, int(n * 0.95) - 1)],
            p99_total_ms=totals[max(0, int(n * 0.99) - 1)],
            step_breakdown={
                step: {
                    "avg_ms": round(sum(vals) / len(vals), 2),
                    "p95_ms": round(
                        sorted(vals)[max(0, int(len(vals) * 0.95) - 1)], 2
                    ),
                    "count": len(vals),
                    "pct_of_total": round(
                        sum(vals) / max(sum(totals), 1) * 100, 1
                    ),
                }
                for step, vals in steps.items()
            },
            period_start=profiles[0].timestamp if profiles else "",
            period_end=profiles[-1].timestamp if profiles else "",
        )


# Context manager for inline profiling
class ProfileSpan:
    """Use with `async with ProfileSpan("step_name") as span:` to time a block."""

    def __init__(self, name: str, metadata: Dict[str, Any] = None):
        self.name = name
        self.metadata = metadata or {}
        self.start = 0.0
        self.end = 0.0
        self.duration_ms = 0.0

    async def __aenter__(self):
        self.start = time.monotonic()
        return self

    async def __aexit__(self, *args):
        self.end = time.monotonic()
        self.duration_ms = (self.end - self.start) * 1000

    def to_span(self) -> LatencySpan:
        return LatencySpan(
            name=self.name,
            start_ms=self.start * 1000,
            end_ms=self.end * 1000,
            duration_ms=self.duration_ms,
            metadata=self.metadata,
        )


latency_profiler = LatencyProfiler()
