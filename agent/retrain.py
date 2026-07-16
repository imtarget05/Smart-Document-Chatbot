"""
Automated Retraining & Re-evaluation Pipeline for Smart Document Chatbot.

Monitors for new documents, triggers re-evaluation, compares with
previous results, and registers improved model versions automatically.

Usage:
    # One-shot retrain check
    python -m agent.retrain --base-url http://localhost:8080/api --token <jwt>

    # As a scheduled task (APScheduler, cron, etc.)
    from agent.retrain import check_and_retrain
    check_and_retrain(base_url, token, document_id)
"""

import os
import json
import time
import logging
import subprocess
import sys
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from pathlib import Path

from agent.model_registry import registry

logger = logging.getLogger(__name__)

EVAL_RESULTS_DIR = Path(os.getenv("EVAL_RESULTS_DIR", "eval/results"))
RETRAIN_CONFIG = {
    "min_new_documents": 1,
    "improvement_threshold": 0.02,
    "max_retrain_attempts": 3,
    "cooldown_hours": 24,
}


class RetrainDecision:
    """Encapsulates the decision from a retrain check."""

    def __init__(self, should_retrain: bool, reason: str,
                 current_metrics: Optional[Dict] = None,
                 previous_metrics: Optional[Dict] = None,
                 improvement: Optional[Dict] = None):
        self.should_retrain = should_retrain
        self.reason = reason
        self.current_metrics = current_metrics or {}
        self.previous_metrics = previous_metrics or {}
        self.improvement = improvement or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "should_retrain": self.should_retrain,
            "reason": self.reason,
            "current_metrics": self.current_metrics,
            "previous_metrics": self.previous_metrics,
            "improvement": self.improvement,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


def get_latest_eval_results() -> Optional[Dict[str, Any]]:
    """Load the most recent evaluation results."""
    EVAL_RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    result_files = sorted(EVAL_RESULTS_DIR.glob("eval_results*.json"), reverse=True)
    if not result_files:
        return None
    with open(result_files[0], "r", encoding="utf-8") as f:
        return json.load(f)


def get_previous_eval_results() -> Optional[Dict[str, Any]]:
    """Load the second most recent evaluation results for comparison."""
    EVAL_RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    result_files = sorted(EVAL_RESULTS_DIR.glob("eval_results*.json"), reverse=True)
    if len(result_files) < 2:
        return None
    with open(result_files[1], "r", encoding="utf-8") as f:
        return json.load(f)


def run_evaluation(base_url: str, token: str, document_id: int) -> Optional[Dict[str, Any]]:
    """Run the eval pipeline and return results."""
    timestamp = int(time.time())
    output_path = EVAL_RESULTS_DIR / f"eval_results_retrain_{timestamp}.json"
    try:
        result = subprocess.run(
            [
                sys.executable, "eval/eval.py",
                "--base-url", base_url,
                "--token", token,
                "--document-id", str(document_id),
                "--output", str(output_path),
                "--mlflow",
            ],
            capture_output=True, text=True, timeout=600,
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        if result.returncode == 0 and output_path.exists():
            with open(output_path, "r") as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Evaluation failed: {e}")
    return None


def calculate_improvement(current: Dict, previous: Dict) -> Dict[str, float]:
    """Calculate the improvement between two eval results."""
    improvement = {}
    for key in ["retrieval_accuracy", "answer_correctness", "hallucination_rate", "average_latency_ms"]:
        c = current.get(key, 0)
        p = previous.get(key, 0)
        improvement[key] = round(c - p, 4)
    return improvement


def check_and_retrain(base_url: str, token: str, document_id: int,
                      force: bool = False) -> RetrainDecision:
    """Check if retraining is needed and execute if so."""
    current = get_latest_eval_results()
    if not current:
        return RetrainDecision(
            should_retrain=False,
            reason="No evaluation results found. Run eval first."
        )

    previous = get_previous_eval_results()

    if previous and not force:
        improvement = calculate_improvement(current, previous)
        accuracy_change = improvement.get("retrieval_accuracy", 0)
        hallucination_change = improvement.get("hallucination_rate", 0)

        if accuracy_change < RETRAIN_CONFIG["improvement_threshold"]:
            return RetrainDecision(
                should_retrain=False,
                reason=f"Insufficient improvement: accuracy change {accuracy_change:+.2%}",
                current_metrics=current,
                previous_metrics=previous,
                improvement=improvement,
            )

        if hallucination_change > 0.05:
            return RetrainDecision(
                should_retrain=False,
                reason=f"Hallucination rate increased by {hallucination_change:+.2%}. Skipping retrain.",
                current_metrics=current,
                previous_metrics=previous,
                improvement=improvement,
            )

    if not registry.passes_quality_gate(current)[0] and not force:
        _, failures = registry.passes_quality_gate(current)
        return RetrainDecision(
            should_retrain=False,
            reason=f"Quality gate failed: {failures}",
            current_metrics=current,
        )

    version = f"v{datetime.now().strftime('%Y%m%d.%H%M%S')}"
    mv = registry.register_model(
        model_name="rag-retriever",
        version=version,
        metrics={
            "retrieval_accuracy": current.get("retrieval_accuracy", 0),
            "answer_correctness": current.get("answer_correctness", 0),
            "hallucination_rate": current.get("hallucination_rate", 0),
        },
        config={"document_id": document_id},
        description=f"Auto-retrained on {datetime.now().strftime('%Y-%m-%d %H:%M')}",
    )

    if mv:
        registry.promote_model("rag-retriever", version, "Production")
        return RetrainDecision(
            should_retrain=True,
            reason=f"Model {version} registered and promoted to Production",
            current_metrics=current,
            previous_metrics=previous or {},
            improvement=calculate_improvement(current, previous) if previous else {},
        )
    else:
        return RetrainDecision(
            should_retrain=False,
            reason=f"Quality gate rejected model {version}",
            current_metrics=current,
        )


def main():
    import argparse
    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser(description="Automated Retrain Pipeline")
    parser.add_argument("--base-url", default="http://localhost:8080/api")
    parser.add_argument("--token", required=True)
    parser.add_argument("--document-id", type=int, required=True)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    decision = check_and_retrain(args.base_url, args.token, args.document_id, args.force)
    print(json.dumps(decision.to_dict(), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
