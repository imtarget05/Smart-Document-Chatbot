"""
A/B Testing Framework for Smart Document Chatbot.

Routes queries between different model configurations (variants),
tracks per-variant metrics, and determines the winning variant
based on configurable success criteria.

Usage:
    from agent.ab_testing import ab_manager

    # Assign a variant for a new query
    variant = ab_manager.assign_variant(query_id="q-123")

    # Log result after query completes
    ab_manager.log_result(
        query_id="q-123",
        variant_id="control",
        latency_ms=1420,
        confidence_score=0.87,
        answer_correct=True,
    )

    # Get experiment report
    report = ab_manager.get_report()
"""

import os
import json
import hashlib
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from pathlib import Path
from dataclasses import dataclass, field, asdict

logger = logging.getLogger(__name__)

AB_HISTORY_DIR = Path(os.getenv("AB_HISTORY_DIR", "ab_history"))


@dataclass
class Variant:
    """A single A/B test variant."""
    id: str
    name: str
    description: str = ""
    weight: float = 0.5
    config: Dict[str, Any] = field(default_factory=dict)
    is_control: bool = False


@dataclass
class Experiment:
    """An A/B test experiment with two or more variants."""
    id: str
    name: str
    description: str = ""
    variants: List[Variant] = field(default_factory=list)
    status: str = "active"
    created_at: str = ""
    min_samples: int = 30
    confidence_level: float = 0.95

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()


@dataclass
class QueryResult:
    """Result of a single query in an A/B test."""
    query_id: str
    variant_id: str
    latency_ms: float = 0
    confidence_score: float = 0
    answer_correct: bool = False
    retrieval_accurate: bool = False
    is_hallucination: bool = False
    timestamp: str = ""


class ABTestManager:
    """Manages A/B test experiments, variant assignment, and result tracking."""

    def __init__(self):
        self.experiments: Dict[str, Experiment] = {}
        self.results: Dict[str, List[QueryResult]] = {}
        self.assignment_cache: Dict[str, str] = {}
        AB_HISTORY_DIR.mkdir(parents=True, exist_ok=True)
        self._load_state()
        self._init_default_experiment()

    def _init_default_experiment(self):
        if "rag-config-v1" not in self.experiments:
            exp = Experiment(
                id="rag-config-v1",
                name="RAG Configuration Test",
                description="Test different RAG confidence thresholds and chunk sizes",
                variants=[
                    Variant(
                        id="control",
                        name="Control (Default)",
                        description="Default RAG config: confidence=0.45, chunk_size=512",
                        weight=0.5,
                        is_control=True,
                        config={"confidence_threshold": 0.45, "chunk_size": 512},
                    ),
                    Variant(
                        id="variant-a",
                        name="Aggressive Retrieval",
                        description="Lower confidence threshold, larger chunks",
                        weight=0.5,
                        config={"confidence_threshold": 0.35, "chunk_size": 1024},
                    ),
                ],
                min_samples=30,
            )
            self.experiments[exp.id] = exp
            self.results[exp.id] = []
            self._save_state()

    def _load_state(self):
        state_file = AB_HISTORY_DIR / "ab_state.json"
        if state_file.exists():
            with open(state_file, "r") as f:
                state = json.load(f)
                for exp_data in state.get("experiments", []):
                    exp = Experiment(
                        id=exp_data["id"],
                        name=exp_data["name"],
                        description=exp_data.get("description", ""),
                        variants=[Variant(**v) for v in exp_data.get("variants", [])],
                        status=exp_data.get("status", "active"),
                        created_at=exp_data.get("created_at", ""),
                        min_samples=exp_data.get("min_samples", 30),
                    )
                    self.experiments[exp.id] = exp
                for exp_id, results_data in state.get("results", {}).items():
                    self.results[exp_id] = [QueryResult(**r) for r in results_data]

    def _save_state(self):
        state = {
            "experiments": [
                {
                    "id": exp.id,
                    "name": exp.name,
                    "description": exp.description,
                    "variants": [asdict(v) for v in exp.variants],
                    "status": exp.status,
                    "created_at": exp.created_at,
                    "min_samples": exp.min_samples,
                }
                for exp in self.experiments.values()
            ],
            "results": {
                exp_id: [asdict(r) for r in results]
                for exp_id, results in self.results.items()
            },
        }
        with open(AB_HISTORY_DIR / "ab_state.json", "w") as f:
            json.dump(state, f, indent=2, ensure_ascii=False)

    def assign_variant(self, query_id: str, experiment_id: str = "rag-config-v1") -> Optional[Variant]:
        """Deterministically assign a variant based on query_id hash."""
        exp = self.experiments.get(experiment_id)
        if not exp or exp.status != "active":
            return None

        hash_val = int(hashlib.md5(query_id.encode()).hexdigest(), 16) % 1000 / 1000.0
        cumulative = 0.0
        for variant in exp.variants:
            cumulative += variant.weight
            if hash_val < cumulative:
                self.assignment_cache[query_id] = variant.id
                return variant

        return exp.variants[-1]

    def log_result(self, query_id: str, variant_id: str, experiment_id: str = "rag-config-v1",
                   latency_ms: float = 0, confidence_score: float = 0,
                   answer_correct: bool = False, retrieval_accurate: bool = False,
                   is_hallucination: bool = False):
        """Log the result of a query for a specific variant."""
        result = QueryResult(
            query_id=query_id,
            variant_id=variant_id,
            latency_ms=latency_ms,
            confidence_score=confidence_score,
            answer_correct=answer_correct,
            retrieval_accurate=retrieval_accurate,
            is_hallucination=is_hallucination,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

        if experiment_id not in self.results:
            self.results[experiment_id] = []
        self.results[experiment_id].append(result)
        self._save_state()

    def get_variant_metrics(self, experiment_id: str, variant_id: str) -> Dict[str, Any]:
        """Calculate aggregated metrics for a variant."""
        results = [r for r in self.results.get(experiment_id, []) if r.variant_id == variant_id]
        if not results:
            return {"sample_size": 0}

        latencies = [r.latency_ms for r in results]
        confidences = [r.confidence_score for r in results]
        correct = sum(1 for r in results if r.answer_correct)
        retrieval = sum(1 for r in results if r.retrieval_accurate)
        hallucinations = sum(1 for r in results if r.is_hallucination)

        return {
            "sample_size": len(results),
            "avg_latency_ms": round(sum(latencies) / len(latencies)),
            "p95_latency_ms": round(sorted(latencies)[int(len(latencies) * 0.95) - 1] if latencies else 0),
            "avg_confidence": round(sum(confidences) / len(confidences), 3),
            "accuracy_rate": round(correct / len(results), 3),
            "retrieval_rate": round(retrieval / len(results), 3),
            "hallucination_rate": round(hallucinations / len(results), 3),
        }

    def get_report(self, experiment_id: str = "rag-config-v1") -> Dict[str, Any]:
        """Generate a full A/B test report with statistical comparison."""
        exp = self.experiments.get(experiment_id)
        if not exp:
            return {"error": f"Experiment {experiment_id} not found"}

        variant_reports = {}
        for variant in exp.variants:
            metrics = self.get_variant_metrics(experiment_id, variant.id)
            variant_reports[variant.id] = {
                "name": variant.name,
                "description": variant.description,
                "is_control": variant.is_control,
                "metrics": metrics,
            }

        control = next((v for v in exp.variants if v.is_control), None)
        treatment = next((v for v in exp.variants if not v.is_control), None)

        winner = None
        if control and treatment:
            control_m = self.get_variant_metrics(experiment_id, control.id)
            treatment_m = self.get_variant_metrics(experiment_id, treatment.id)

            if control_m["sample_size"] >= exp.min_samples and treatment_m["sample_size"] >= exp.min_samples:
                acc_diff = treatment_m["accuracy_rate"] - control_m["accuracy_rate"]
                lat_diff = treatment_m["avg_latency_ms"] - control_m["avg_latency_ms"]

                if acc_diff > 0.02 or (acc_diff > 0 and lat_diff < 0):
                    winner = treatment.id
                elif acc_diff < -0.02:
                    winner = control.id

        return {
            "experiment_id": experiment_id,
            "name": exp.name,
            "status": exp.status,
            "created_at": exp.created_at,
            "variants": variant_reports,
            "winner": winner,
            "min_samples": exp.min_samples,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def stop_experiment(self, experiment_id: str):
        """Stop an experiment (no new assignments)."""
        if experiment_id in self.experiments:
            self.experiments[experiment_id].status = "completed"
            self._save_state()


# Singleton
ab_manager = ABTestManager()
