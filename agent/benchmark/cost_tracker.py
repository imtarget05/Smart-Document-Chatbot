"""Per-query cost tracking with model-level breakdown and aggregation."""

import json
import logging
from collections import defaultdict
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from .models import calculate_cost

logger = logging.getLogger(__name__)


@dataclass
class CostEntry:
    query_id: str
    model: str
    input_text: str
    output_text: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    is_local: bool
    provider: str
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CostSummary:
    total_queries: int
    total_cost_usd: float
    total_input_tokens: int
    total_output_tokens: int
    avg_cost_per_query: float
    avg_input_tokens: float
    avg_output_tokens: float
    p95_cost_per_query: float
    model_breakdown: Dict[str, Dict[str, Any]]
    provider_breakdown: Dict[str, Dict[str, Any]]
    period_start: str
    period_end: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_queries": self.total_queries,
            "total_cost_usd": round(self.total_cost_usd, 4),
            "projected_monthly_cost_usd": round(
                self.total_cost_usd / max(
                    (datetime.fromisoformat(self.period_end) - datetime.fromisoformat(self.period_start)).total_seconds(),
                    1,
                ) * 30 * 86400,
                2,
            ),
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "avg_cost_per_query": round(self.avg_cost_per_query, 6),
            "avg_input_tokens": round(self.avg_input_tokens, 1),
            "avg_output_tokens": round(self.avg_output_tokens, 1),
            "model_breakdown": self.model_breakdown,
            "provider_breakdown": self.provider_breakdown,
            "period_start": self.period_start,
            "period_end": self.period_end,
        }


class CostTracker:
    """Tracks per-query LLM costs with persistence and aggregation."""

    def __init__(self, history_dir: str = "benchmark/cost_history"):
        self.history_dir = Path(history_dir)
        self.history_dir.mkdir(parents=True, exist_ok=True)
        self._entries: List[CostEntry] = []
        self._load()

    def _load(self):
        for f in sorted(self.history_dir.glob("*.json")):
            try:
                data = json.loads(f.read_text())
                self._entries.append(CostEntry(**data))
            except Exception as exc:
                logger.debug("Failed to load cost entry %s: %s", f, exc)

    def _save(self, entry: CostEntry):
        path = self.history_dir / f"{entry.query_id}.json"
        with open(path, "w") as f:
            json.dump(entry.to_dict(), f, indent=2)

    def track(
        self,
        query_id: str,
        model: str,
        input_text: str,
        output_text: str,
    ) -> CostEntry:
        cost_info = calculate_cost(model, input_text, output_text)
        entry = CostEntry(
            query_id=query_id,
            model=model,
            input_text=input_text[:200],
            output_text=output_text[:200],
            input_tokens=cost_info["input_tokens"],
            output_tokens=cost_info["output_tokens"],
            cost_usd=cost_info["estimated_cost_usd"],
            is_local=cost_info["is_local"],
            provider=cost_info["provider"],
        )
        self._entries.append(entry)
        self._save(entry)
        return entry

    def get_summary(self, last_n: Optional[int] = None) -> CostSummary:
        entries = self._entries[-last_n:] if last_n else self._entries
        if not entries:
            return CostSummary(
                total_queries=0,
                total_cost_usd=0,
                total_input_tokens=0,
                total_output_tokens=0,
                avg_cost_per_query=0,
                avg_input_tokens=0,
                avg_output_tokens=0,
                p95_cost_per_query=0,
                model_breakdown={},
                provider_breakdown={},
                period_start=datetime.now(timezone.utc).isoformat(),
                period_end=datetime.now(timezone.utc).isoformat(),
            )

        model_bd: Dict[str, list] = defaultdict(list)
        provider_bd: Dict[str, list] = defaultdict(list)
        costs = []

        for e in entries:
            model_bd[e.model].append(e.cost_usd)
            provider_bd[e.provider].append(e.cost_usd)
            costs.append(e.cost_usd)

        total_cost = sum(costs)
        n = len(entries)
        costs_sorted = sorted(costs)

        return CostSummary(
            total_queries=n,
            total_cost_usd=total_cost,
            total_input_tokens=sum(e.input_tokens for e in entries),
            total_output_tokens=sum(e.output_tokens for e in entries),
            avg_cost_per_query=total_cost / n,
            avg_input_tokens=sum(e.input_tokens for e in entries) / n,
            avg_output_tokens=sum(e.output_tokens for e in entries) / n,
            p95_cost_per_query=costs_sorted[max(0, int(n * 0.95) - 1)],
            model_breakdown={
                m: {
                    "total_cost": round(sum(v), 4),
                    "count": len(v),
                    "avg_cost": round(sum(v) / len(v), 6),
                }
                for m, v in model_bd.items()
            },
            provider_breakdown={
                p: {
                    "total_cost": round(sum(v), 4),
                    "count": len(v),
                    "avg_cost": round(sum(v) / len(v), 6),
                }
                for p, v in provider_bd.items()
            },
            period_start=entries[0].timestamp if entries else "",
            period_end=entries[-1].timestamp if entries else "",
        )


cost_tracker = CostTracker()
