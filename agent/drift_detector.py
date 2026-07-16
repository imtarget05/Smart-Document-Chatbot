"""
Data Drift Detection for Smart Document Chatbot.

Monitors incoming queries and retrieved documents for distribution shifts.
Uses Population Stability Index (PSI) and simple statistical tests
to detect when the model's input distribution changes significantly.

Metrics monitored:
- Query length distribution
- Retrieval confidence distribution
- RAG strategy distribution (direct/corrective/web_search/general_knowledge)
- Response latency distribution

Usage:
    from agent.drift_detector import drift_detector

    # Log a prediction
    drift_detector.log_prediction({
        "query_length": 120,
        "confidence_score": 0.78,
        "rag_strategy": "direct",
        "latency_ms": 1420,
    })

    # Check for drift
    report = drift_detector.check_drift()
    if report["drift_detected"]:
        print(f"⚠️ Drift detected: {report['alerts']}")
"""

import os
import json
import logging
import math
from typing import Optional, Dict, Any, List
from collections import deque
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

DRIFT_HISTORY_DIR = Path(os.getenv("DRIFT_HISTORY_DIR", "drift_history"))
WINDOW_SIZE = int(os.getenv("DRIFT_WINDOW_SIZE", "200"))
PSI_THRESHOLD = float(os.getenv("DRIFT_PSI_THRESHOLD", "0.20"))
ZSCORE_THRESHOLD = float(os.getenv("DRIFT_ZSCORE_THRESHOLD", "2.5"))


def calculate_psi(expected: List[float], actual: List[float], bins: int = 10) -> float:
    """Calculate Population Stability Index between two distributions."""
    if not expected or not actual:
        return 0.0

    min_val = min(min(expected), min(actual))
    max_val = max(max(expected), max(actual))
    if min_val == max_val:
        return 0.0

    bin_edges = [min_val + i * (max_val - min_val) / bins for i in range(bins + 1)]

    def histogram(data, edges):
        counts = [0] * (len(edges) - 1)
        for v in data:
            for i in range(len(edges) - 1):
                if edges[i] <= v < edges[i + 1]:
                    counts[i] += 1
                    break
            else:
                counts[-1] += 1
        total = max(len(data), 1)
        return [c / total for c in counts]

    expected_pct = histogram(expected, bin_edges)
    actual_pct = histogram(actual, bin_edges)

    psi = 0.0
    for e, a in zip(expected_pct, actual_pct):
        e = max(e, 0.001)
        a = max(a, 0.001)
        psi += (a - e) * math.log(a / e)
    return round(psi, 4)


def calculate_zscore_mean(reference: List[float], current: List[float]) -> float:
    """Calculate Z-score of current mean vs reference distribution."""
    if len(reference) < 10 or not current:
        return 0.0
    ref_mean = sum(reference) / len(reference)
    ref_std = (sum((x - ref_mean) ** 2 for x in reference) / len(reference)) ** 0.5
    if ref_std == 0:
        return 0.0
    cur_mean = sum(current) / len(current)
    return round((cur_mean - ref_mean) / ref_std, 2)


class DriftDetector:
    """Monitors data drift across multiple metrics."""

    def __init__(self, window_size: int = WINDOW_SIZE):
        self.window_size = window_size
        self.reference_window: deque = deque(maxlen=window_size)
        self.current_window: deque = deque(maxlen=window_size)
        self.alerts: List[Dict[str, Any]] = []
        self.history_dir = DRIFT_HISTORY_DIR
        self.history_dir.mkdir(parents=True, exist_ok=True)
        self._load_history()

    def _load_history(self):
        history_file = self.history_dir / "reference_window.json"
        if history_file.exists():
            with open(history_file, "r") as f:
                data = json.load(f)
                self.reference_window.extend(data)

    def _save_history(self):
        history_file = self.history_dir / "reference_window.json"
        with open(history_file, "w") as f:
            json.dump(list(self.reference_window), f)

    def log_prediction(self, prediction: Dict[str, Any]):
        """Log a prediction for drift monitoring."""
        record = {
            "query_length": prediction.get("query_length", 0),
            "confidence_score": prediction.get("confidence_score", 0),
            "rag_strategy": prediction.get("rag_strategy", "unknown"),
            "latency_ms": prediction.get("latency_ms", 0),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self.current_window.append(record)

        if len(self.reference_window) < self.window_size:
            self.reference_window.append(record)
            if len(self.reference_window) % 50 == 0:
                self._save_history()

    def check_drift(self) -> Dict[str, Any]:
        """Check for data drift between reference and current windows."""
        self.alerts = []

        if len(self.current_window) < 20:
            return {
                "drift_detected": False,
                "reason": "Insufficient current data (need ≥20 samples)",
                "alerts": [],
                "metrics": {},
            }

        ref_confidences = [r["confidence_score"] for r in self.reference_window]
        cur_confidences = [r["confidence_score"] for r in self.current_window]
        ref_latencies = [r["latency_ms"] for r in self.reference_window]
        cur_latencies = [r["latency_ms"] for r in self.current_window]
        ref_lengths = [r["query_length"] for r in self.reference_window]
        cur_lengths = [r["query_length"] for r in self.current_window]

        psi_confidence = calculate_psi(ref_confidences, cur_confidences)
        psi_latency = calculate_psi(ref_latencies, cur_latencies)
        psi_length = calculate_psi(ref_lengths, cur_lengths)

        zscore_confidence = calculate_zscore_mean(ref_confidences, cur_confidences)
        zscore_latency = calculate_zscore_mean(ref_latencies, cur_latencies)

        ref_strategies = {}
        for r in self.reference_window:
            s = r["rag_strategy"]
            ref_strategies[s] = ref_strategies.get(s, 0) + 1
        cur_strategies = {}
        for r in self.current_window:
            s = r["rag_strategy"]
            cur_strategies[s] = cur_strategies.get(s, 0) + 1

        total_ref = max(len(self.reference_window), 1)
        total_cur = max(len(self.current_window), 1)
        strategy_shifts = {}
        all_strategies = set(list(ref_strategies.keys()) + list(cur_strategies.keys()))
        for s in all_strategies:
            ref_pct = ref_strategies.get(s, 0) / total_ref
            cur_pct = cur_strategies.get(s, 0) / total_cur
            strategy_shifts[s] = round(cur_pct - ref_pct, 3)

        if psi_confidence > PSI_THRESHOLD:
            self.alerts.append({
                "type": "confidence_drift",
                "severity": "WARNING",
                "message": f"Confidence distribution shifted (PSI={psi_confidence:.3f})",
                "psi": psi_confidence,
                "zscore": zscore_confidence,
            })

        if psi_latency > PSI_THRESHOLD:
            self.alerts.append({
                "type": "latency_drift",
                "severity": "WARNING",
                "message": f"Latency distribution shifted (PSI={psi_latency:.3f})",
                "psi": psi_latency,
                "zscore": zscore_latency,
            })

        if abs(zscore_latency) > ZSCORE_THRESHOLD:
            self.alerts.append({
                "type": "latency_spike",
                "severity": "CRITICAL" if zscore_latency > 0 else "INFO",
                "message": f"Latency {'increased' if zscore_latency > 0 else 'decreased'} significantly (Z={zscore_latency:.2f})",
                "zscore": zscore_latency,
            })

        for strategy, shift in strategy_shifts.items():
            if abs(shift) > 0.15:
                self.alerts.append({
                    "type": "strategy_shift",
                    "severity": "WARNING",
                    "message": f"RAG strategy '{strategy}' shifted by {shift:+.1%}",
                    "shift": shift,
                })

        report = {
            "drift_detected": len(self.alerts) > 0,
            "alerts": self.alerts,
            "metrics": {
                "psi_confidence": psi_confidence,
                "psi_latency": psi_latency,
                "psi_length": psi_length,
                "zscore_confidence": zscore_confidence,
                "zscore_latency": zscore_latency,
                "strategy_shifts": strategy_shifts,
            },
            "window_sizes": {
                "reference": len(self.reference_window),
                "current": len(self.current_window),
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        self._save_drift_report(report)
        return report

    def _save_drift_report(self, report: Dict[str, Any]):
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = self.history_dir / f"drift_report_{ts}.json"
        with open(path, "w") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)


# Singleton
drift_detector = DriftDetector()
