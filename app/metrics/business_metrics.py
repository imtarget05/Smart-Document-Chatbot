"""
Business Metrics Measurement - Before/After AI Automation (Smart Doc Chatbot).
Tracks time saved, quality improvement, cost reduction for knowledge management.

Issue #41: The DEFAULT_PROCESSES are baseline estimates for portfolio/demo
purposes. In production, real measurements should be collected via the
add_process_metric() API and stored in business_metrics.json. The defaults
are clearly labeled as estimates and should be replaced with real data.

Issue #62: print() replaced with logger for production code.
"""

import json
import os
import logging
from datetime import datetime
from typing import Dict, List
from dataclasses import dataclass, field

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
    is_estimate: bool = True  # Issue #41: flag estimates vs real measurements

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
            "is_estimate": self.is_estimate,  # Issue #41: expose estimate flag
        }


@dataclass
class AIMetricsSummary:
    total_processes: int = 0
    total_time_saved_monthly_hours: float = 0.0
    total_cost_saved_monthly: float = 0.0
    avg_productivity_gain_pct: float = 0.0
    processes: List[Dict] = field(default_factory=list)
    estimate_count: int = 0  # Issue #41: count of estimated vs measured


METRICS_FILE = os.path.join(
    os.path.dirname(__file__), "..", "data", "business_metrics.json"
)


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
            cost_per_hour = (
                round((cost_saved / saved_month) * 60, 2) if saved_month > 0 else 0
            )
        else:
            cost_per_hour = 0
        result.append(
            ProcessMetric(
                process_name=item["process"],
                department=item["department"],
                before_minutes=before,
                after_minutes=after,
                frequency_per_week=freq,
                cost_per_hour=cost_per_hour,
                is_estimate=item.get("is_estimate", True),
            )
        )
    return result


def save_metrics(metrics: List[ProcessMetric]):
    os.makedirs(os.path.dirname(METRICS_FILE), exist_ok=True)
    with open(METRICS_FILE, "w") as f:
        json.dump([m.to_dict() for m in metrics], f, indent=2)


def add_process_metric(metric: ProcessMetric):
    """Add or update a process metric. Set is_estimate=False for real measurements."""
    metrics = load_metrics()
    existing = [m for m in metrics if m.process_name == metric.process_name]
    if existing:
        metrics.remove(existing[0])
    metrics.append(metric)
    save_metrics(metrics)
    logger.info(
        "metric_added: %s saved=%.1f%% estimate=%s",
        metric.process_name,
        metric.productivity_gain_pct,
        metric.is_estimate,
    )


def get_summary() -> AIMetricsSummary:
    metrics = load_metrics()
    if not metrics:
        return AIMetricsSummary()

    total_hours = sum(m.time_saved_per_month / 60 for m in metrics)
    total_cost = sum(m.cost_saved_per_month for m in metrics)
    avg_gain = sum(m.productivity_gain_pct for m in metrics) / len(metrics)
    estimate_count = sum(1 for m in metrics if m.is_estimate)

    return AIMetricsSummary(
        total_processes=len(metrics),
        total_time_saved_monthly_hours=round(total_hours, 1),
        total_cost_saved_monthly=round(total_cost, 2),
        avg_productivity_gain_pct=round(avg_gain, 1),
        processes=[m.to_dict() for m in metrics],
        estimate_count=estimate_count,
    )


# Issue #41: Default processes are BASELINE ESTIMATES for portfolio/demo.
# Replace with real measurements collected via add_process_metric(is_estimate=False).
DEFAULT_PROCESSES = [
    ProcessMetric(
        process_name="Document Search & Q&A",
        department="CSKH",
        before_minutes=15,
        after_minutes=0.5,
        frequency_per_week=20,
        cost_per_hour=12.0,
        description="Manual document lookup -> RAG chatbot with Ollama",
        is_estimate=True,
    ),
    ProcessMetric(
        process_name="Policy Compliance Check",
        department="HR",
        before_minutes=30,
        after_minutes=1,
        frequency_per_week=10,
        cost_per_hour=15.0,
        description="Manual policy review -> AI-powered compliance check",
        is_estimate=True,
    ),
    ProcessMetric(
        process_name="Customer Complaint Resolution",
        department="CSKH",
        before_minutes=45,
        after_minutes=5,
        frequency_per_week=15,
        cost_per_hour=18.0,
        description="Manual case research -> AI case similarity + suggestion",
        is_estimate=True,
    ),
    ProcessMetric(
        process_name="Knowledge Base Update",
        department="IT",
        before_minutes=60,
        after_minutes=10,
        frequency_per_week=3,
        cost_per_hour=20.0,
        description="Manual documentation -> Auto-ingestion + chunking",
        is_estimate=True,
    ),
    ProcessMetric(
        process_name="8D Report Generation",
        department="Quality",
        before_minutes=120,
        after_minutes=15,
        frequency_per_week=2,
        cost_per_hour=22.0,
        description="Manual root cause analysis -> AI-assisted 8D workflow",
        is_estimate=True,
    ),
    ProcessMetric(
        process_name="Employee Onboarding Training",
        department="HR",
        before_minutes=240,
        after_minutes=30,
        frequency_per_week=1,
        cost_per_hour=15.0,
        description="Manual training sessions -> AI chatbot self-service",
        is_estimate=True,
    ),
]


def init_default_metrics():
    existing = load_metrics()
    if not existing:
        save_metrics(DEFAULT_PROCESSES)
        logger.info(
            "default_metrics_initialized: %d processes (all estimates)",
            len(DEFAULT_PROCESSES),
        )
        logger.warning(
            "Default metrics are ESTIMATES. Replace with real measurements "
            "via add_process_metric(is_estimate=False)."
        )


def print_report():
    """Print a business impact report. Uses logger instead of print() (issue #62)."""
    init_default_metrics()
    summary = get_summary()

    logger.info("=" * 65)
    logger.info("  BUSINESS IMPACT REPORT - AI Automation at Smart Doc Chatbot")
    logger.info("=" * 65)

    for p in summary.processes:
        est_tag = " [ESTIMATE]" if p.get("is_estimate", True) else " [MEASURED]"
        logger.info(
            "  %-35s before=%.0fm after=%.1fm gain=%.1f%% hrs/mo=%.1f%s",
            p["process"],
            p["before_min"],
            p["after_min"],
            p["productivity_gain_pct"],
            p["saved_per_month_hours"],
            est_tag,
        )

    logger.info("-" * 65)
    logger.info("  Total processes automated:  %d", summary.total_processes)
    logger.info(
        "  Monthly time saved:         %.1f hours",
        summary.total_time_saved_monthly_hours,
    )
    logger.info("  Monthly cost saved:         $%.2f", summary.total_cost_saved_monthly)
    logger.info(
        "  Avg productivity gain:      %.1f%%", summary.avg_productivity_gain_pct
    )
    if summary.estimate_count > 0:
        logger.warning(
            "  WARNING: %d/%d metrics are ESTIMATES, not real measurements.",
            summary.estimate_count,
            summary.total_processes,
        )
    logger.info("  Generated: %s", datetime.now().strftime("%Y-%m-%d %H:%M"))
    logger.info("=" * 65)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    print_report()
