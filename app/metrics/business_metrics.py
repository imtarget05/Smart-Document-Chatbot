"""
Business Metrics Measurement — Before/After AI Automation (Smart Doc Chatbot).
Tracks time saved, quality improvement, cost reduction for knowledge management.
"""
import json
import os
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional
from dataclasses import dataclass, field, asdict

logger = logging.getLogger(__name__)


@dataclass
class ProcessMetric:
    process_name: str
    department: str
    before_minutes: float
    after_minutes: float
    frequency_per_week: int
    cost_per_hour: float = 0.0
    description: str = ""

    @property
    def time_saved_per_task(self) -> float:
        return self.before_minutes - self.after_minutes

    @property
    def time_saved_per_week(self) -> float:
        return self.time_saved_per_task * self.frequency_per_week

    @property
    def time_saved_per_month(self) -> float:
        return self.time_saved_per_week * 4.33

    @property
    def productivity_gain_pct(self) -> float:
        if self.before_minutes == 0:
            return 0.0
        return round((self.time_saved_per_task / self.before_minutes) * 100, 1)

    @property
    def cost_saved_per_month(self) -> float:
        return round((self.time_saved_per_month / 60) * self.cost_per_hour, 2)

    def to_dict(self) -> Dict:
        return {
            "process": self.process_name,
            "department": self.department,
            "before_min": self.before_minutes,
            "after_min": self.after_minutes,
            "saved_per_task_min": round(self.time_saved_per_task, 1),
            "frequency_per_week": self.frequency_per_week,
            "saved_per_week_min": round(self.time_saved_per_week, 1),
            "saved_per_month_hours": round(self.time_saved_per_month / 60, 1),
            "productivity_gain_pct": self.productivity_gain_pct,
            "cost_saved_per_month": self.cost_saved_per_month,
        }


@dataclass
class AIMetricsSummary:
    total_processes: int = 0
    total_time_saved_monthly_hours: float = 0.0
    total_cost_saved_monthly: float = 0.0
    avg_productivity_gain_pct: float = 0.0
    processes: List[Dict] = field(default_factory=list)


METRICS_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "business_metrics.json")


def load_metrics() -> List[ProcessMetric]:
    if not os.path.exists(METRICS_FILE):
        return []
    with open(METRICS_FILE, "r") as f:
        data = json.load(f)
    result = []
    for item in data:
        before = item["before_min"]
        after = item["after_min"]
        freq = item["frequency_per_week"]
        saved_month = item.get("saved_per_month_hours", 0)
        cost_saved = item.get("cost_saved_per_month", 0)
        if saved_month > 0 and cost_saved > 0:
            cost_per_hour = round((cost_saved / saved_month) * 60, 2) if saved_month > 0 else 0
        else:
            cost_per_hour = 0
        result.append(ProcessMetric(
            process_name=item["process"],
            department=item["department"],
            before_minutes=before,
            after_minutes=after,
            frequency_per_week=freq,
            cost_per_hour=cost_per_hour,
        ))
    return result


def save_metrics(metrics: List[ProcessMetric]):
    os.makedirs(os.path.dirname(METRICS_FILE), exist_ok=True)
    with open(METRICS_FILE, "w") as f:
        json.dump([m.to_dict() for m in metrics], f, indent=2)


def add_process_metric(metric: ProcessMetric):
    metrics = load_metrics()
    existing = [m for m in metrics if m.process_name == metric.process_name]
    if existing:
        metrics.remove(existing[0])
    metrics.append(metric)
    save_metrics(metrics)
    logger.info(f"metric_added: {metric.process_name} saved={metric.productivity_gain_pct}%")


def get_summary() -> AIMetricsSummary:
    metrics = load_metrics()
    if not metrics:
        return AIMetricsSummary()

    total_hours = sum(m.time_saved_per_month / 60 for m in metrics)
    total_cost = sum(m.cost_saved_per_month for m in metrics)
    avg_gain = sum(m.productivity_gain_pct for m in metrics) / len(metrics)

    return AIMetricsSummary(
        total_processes=len(metrics),
        total_time_saved_monthly_hours=round(total_hours, 1),
        total_cost_saved_monthly=round(total_cost, 2),
        avg_productivity_gain_pct=round(avg_gain, 1),
        processes=[m.to_dict() for m in metrics],
    )


DEFAULT_PROCESSES = [
    ProcessMetric(
        process_name="Document Search & Q&A",
        department="CSKH",
        before_minutes=15,
        after_minutes=0.5,
        frequency_per_week=20,
        cost_per_hour=12.0,
        description="Manual document lookup → RAG chatbot with Ollama",
    ),
    ProcessMetric(
        process_name="Policy Compliance Check",
        department="HR",
        before_minutes=30,
        after_minutes=1,
        frequency_per_week=10,
        cost_per_hour=15.0,
        description="Manual policy review → AI-powered compliance check",
    ),
    ProcessMetric(
        process_name="Customer Complaint Resolution",
        department="CSKH",
        before_minutes=45,
        after_minutes=5,
        frequency_per_week=15,
        cost_per_hour=18.0,
        description="Manual case research → AI case similarity + suggestion",
    ),
    ProcessMetric(
        process_name="Knowledge Base Update",
        department="IT",
        before_minutes=60,
        after_minutes=10,
        frequency_per_week=3,
        cost_per_hour=20.0,
        description="Manual documentation → Auto-ingestion + chunking",
    ),
    ProcessMetric(
        process_name="8D Report Generation",
        department="Quality",
        before_minutes=120,
        after_minutes=15,
        frequency_per_week=2,
        cost_per_hour=22.0,
        description="Manual root cause analysis → AI-assisted 8D workflow",
    ),
    ProcessMetric(
        process_name="Employee Onboarding Training",
        department="HR",
        before_minutes=240,
        after_minutes=30,
        frequency_per_week=1,
        cost_per_hour=15.0,
        description="Manual training sessions → AI chatbot self-service",
    ),
]


def init_default_metrics():
    existing = load_metrics()
    if not existing:
        save_metrics(DEFAULT_PROCESSES)
        logger.info(f"default_metrics_initialized: {len(DEFAULT_PROCESSES)} processes")


def print_report():
    init_default_metrics()
    summary = get_summary()

    print("=" * 65)
    print("  BUSINESS IMPACT REPORT — AI Automation at Smart Doc Chatbot")
    print("=" * 65)
    print(f"\n{'Process':<35} {'Before':>8} {'After':>8} {'Saved%':>8} {'Hrs/Mo':>8}")
    print("-" * 65)

    for p in summary.processes:
        print(f"{p['process']:<35} {p['before_min']:>6.0f}m {p['after_min']:>6.1f}m "
              f"{p['productivity_gain_pct']:>6.1f}% {p['saved_per_month_hours']:>6.1f}h")

    print("-" * 65)
    print(f"\n  Total processes automated:  {summary.total_processes}")
    print(f"  Monthly time saved:         {summary.total_time_saved_monthly_hours} hours")
    print(f"  Monthly cost saved:         ${summary.total_cost_saved_monthly:,.2f}")
    print(f"  Avg productivity gain:      {summary.avg_productivity_gain_pct}%")
    print(f"\n  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 65)


if __name__ == "__main__":
    print_report()
