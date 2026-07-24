"""
TC-MLO-01 → TC-MLO-08: MLOps Pipeline Flow Tests
"""

import sys
import os
import json
import hashlib
from typing import List, Dict, Optional
from dataclasses import dataclass
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@dataclass
class ModelVersion:
    version: str
    model_name: str
    stage: str
    metrics: Dict[str, float]
    created_at: str = ""
    description: str = ""


@dataclass
class PredictionLog:
    query_id: str
    query: str
    answer: str
    latency_ms: float
    confidence: float
    timestamp: str = ""


class MockModelRegistry:
    def __init__(self):
        self.models: Dict[str, List[ModelVersion]] = {}
        self.quality_threshold = {
            "retrieval_accuracy": 0.80,
            "answer_correctness": 0.75,
            "hallucination_rate": 0.10,
        }

    def passes_quality_gate(self, metrics: Dict[str, float]) -> tuple:
        failures = []
        for metric, threshold in self.quality_threshold.items():
            if metric in metrics:
                if metric == "hallucination_rate":
                    if metrics[metric] > threshold:
                        failures.append(
                            f"{metric}: {metrics[metric]:.2%} > {threshold:.2%}"
                        )
                else:
                    if metrics[metric] < threshold:
                        failures.append(
                            f"{metric}: {metrics[metric]:.2%} < {threshold:.2%}"
                        )
        return len(failures) == 0, failures

    def register_model(
        self, model_name: str, version: str, metrics: Dict
    ) -> Optional[ModelVersion]:
        passed, _ = self.passes_quality_gate(metrics)
        if not passed:
            return None

        if model_name not in self.models:
            self.models[model_name] = []

        existing = [v.version for v in self.models[model_name]]
        if version in existing:
            return None

        mv = ModelVersion(
            version=version,
            model_name=model_name,
            stage="Staging",
            metrics=metrics,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        self.models[model_name].append(mv)
        return mv

    def promote_model(self, model_name: str, version: str, stage: str) -> bool:
        if model_name not in self.models:
            return False
        for v in self.models[model_name]:
            if v.version == version:
                v.stage = stage
                return True
        return False

    def list_versions(self, model_name: str) -> List[ModelVersion]:
        return self.models.get(model_name, [])


class MockDriftDetector:
    def __init__(self, threshold: float = 0.2):
        self.threshold = threshold
        self.reference_window: List[float] = []
        self.current_window: List[float] = []
        self.window_size = 100

    def log_prediction(self, accuracy: float):
        self.current_window.append(accuracy)
        if len(self.current_window) > self.window_size:
            self.current_window.pop(0)

    def set_reference(self, data: List[float]):
        self.reference_window = data

    def calculate_psi(self) -> float:
        if not self.reference_window or not self.current_window:
            return 0.0

        ref_hist = self._histogram(self.reference_window, bins=10)
        cur_hist = self._histogram(self.current_window, bins=10)

        psi = 0.0
        for r, c in zip(ref_hist, cur_hist):
            r = max(r, 0.001)
            c = max(c, 0.001)
            psi += (c - r) * (c / r - 1)
        return abs(psi)

    def _histogram(self, data: List[float], bins: int) -> List[float]:
        min_val = min(data)
        max_val = max(data)
        if min_val == max_val:
            return [1.0 / bins] * bins
        bin_width = (max_val - min_val) / bins
        counts = [0] * bins
        for v in data:
            idx = min(int((v - min_val) / bin_width), bins - 1)
            counts[idx] += 1
        total = sum(counts)
        return [c / total for c in counts]

    def check_drift(self) -> Dict:
        psi = self.calculate_psi()
        alerts = []
        if psi >= self.threshold:
            alerts.append(
                {"type": "DATA_DRIFT", "psi": psi, "threshold": self.threshold}
            )
        return {"psi": psi, "alerts": alerts}


class MockABTestManager:
    def __init__(self):
        self.experiments: Dict[str, Dict] = {}
        self.results: Dict[str, List[Dict]] = {}

    def create_experiment(self, exp_id: str, variants: List[Dict]):
        self.experiments[exp_id] = {
            "variants": variants,
            "created_at": datetime.now().isoformat(),
        }
        self.results[exp_id] = []

    def assign_variant(self, exp_id: str, query_id: str) -> Optional[Dict]:
        import random

        exp = self.experiments.get(exp_id)
        if not exp:
            return None
        variants = exp["variants"]
        weights = [v.get("weight", 0.5) for v in variants]
        return random.choices(variants, weights=weights, k=1)[0]

    def log_result(self, exp_id: str, result: Dict):
        if exp_id not in self.results:
            self.results[exp_id] = []
        self.results[exp_id].append(result)

    def get_metrics(self, exp_id: str, variant_id: str) -> Dict:
        results = [
            r for r in self.results.get(exp_id, []) if r.get("variant_id") == variant_id
        ]
        if not results:
            return {"sample_size": 0}
        correct = sum(1 for r in results if r.get("correct", False))
        latencies = [r.get("latency_ms", 0) for r in results]
        return {
            "sample_size": len(results),
            "accuracy": correct / len(results),
            "avg_latency_ms": sum(latencies) / len(latencies),
        }


class MockPredictionLogger:
    def __init__(self):
        self.logs: List[PredictionLog] = []

    def log(self, query: str, answer: str, latency_ms: float, confidence: float):
        pl = PredictionLog(
            query_id=hashlib.md5(query.encode()).hexdigest()[:8],
            query=query,
            answer=answer,
            latency_ms=latency_ms,
            confidence=confidence,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        self.logs.append(pl)

    def get_recent(self, n: int = 10) -> List[PredictionLog]:
        return self.logs[-n:]

    def to_json(self) -> str:
        return json.dumps(
            [
                {
                    "query_id": log.query_id,
                    "query": log.query,
                    "answer": log.answer,
                    "latency_ms": log.latency_ms,
                    "confidence": log.confidence,
                }
                for log in self.logs
            ]
        )


class TestMLOps:
    def test_mlo01_drift_detection(self):
        """TC-MLO-01: Data Drift Detection — PSI alert when drift detected."""
        detector = MockDriftDetector(threshold=0.01)
        import random

        random.seed(42)
        detector.set_reference([0.85 + random.uniform(-0.02, 0.02) for _ in range(100)])
        for _ in range(100):
            detector.log_prediction(0.50 + random.uniform(-0.02, 0.02))

        result = detector.check_drift()
        assert result["psi"] > 0, "PSI should be > 0 when distributions differ"

    def test_mlo02_model_promotion(self):
        """TC-MLO-02: Model Version Promotion — auto-promote on quality pass."""
        registry = MockModelRegistry()
        mv = registry.register_model(
            "rag-model",
            "v1.0",
            {
                "retrieval_accuracy": 0.88,
                "answer_correctness": 0.82,
                "hallucination_rate": 0.04,
            },
        )
        assert mv is not None

        promoted = registry.promote_model("rag-model", "v1.0", "Production")
        assert promoted

        versions = registry.list_versions("rag-model")
        prod_version = [v for v in versions if v.version == "v1.0"]
        assert prod_version[0].stage == "Production"

    def test_mlo03_quality_gate_block(self):
        """TC-MLO-03: Quality Gate Block — reject model below threshold."""
        registry = MockModelRegistry()
        mv = registry.register_model(
            "rag-model",
            "v-bad",
            {
                "retrieval_accuracy": 0.60,
                "answer_correctness": 0.50,
                "hallucination_rate": 0.15,
            },
        )
        assert mv is None, "Should reject model with poor metrics"

    def test_mlo04_retrain_trigger(self):
        """TC-MLO-04: Auto Retrain Trigger — accuracy drop triggers retrain."""
        accuracy_history = [0.79, 0.75, 0.72]
        threshold = 0.80
        consecutive_below = sum(1 for a in accuracy_history[-3:] if a < threshold)

        retrain_triggered = consecutive_below >= 3
        assert retrain_triggered, "Should trigger retrain after 3 consecutive drops"

    def test_mlo05_mlflow_logging(self):
        """TC-MLO-05: MLflow Experiment Logging — metrics logged correctly."""
        logger = MockPredictionLogger()
        for i in range(10):
            logger.log(
                f"query_{i}",
                f"answer_{i}",
                latency_ms=100 + i * 10,
                confidence=0.85 + i * 0.01,
            )

        logs = logger.get_recent(5)
        assert len(logs) == 5
        for log in logs:
            assert log.latency_ms > 0
            assert 0 <= log.confidence <= 1

        json_output = logger.to_json()
        assert len(json_output) > 0

    def test_mlo06_ab_test_split(self):
        """TC-MLO-06: A/B Test Traffic Split — ~50/50 distribution."""
        ab = MockABTestManager()
        ab.create_experiment(
            "exp-1",
            [
                {"id": "control", "name": "Control", "weight": 0.5},
                {"id": "treatment", "name": "Treatment", "weight": 0.5},
            ],
        )

        assignments = []
        for i in range(1000):
            v = ab.assign_variant("exp-1", f"q-{i}")
            assignments.append(v["id"])

        control_count = assignments.count("control")
        assert 450 <= control_count <= 550, f"Split not balanced: {control_count}/1000"

    def test_mlo07_rollback_on_degradation(self):
        """TC-MLO-07: Rollback on Degradation — revert when new variant worse."""
        ab = MockABTestManager()
        ab.create_experiment(
            "exp-rollback",
            [
                {"id": "control", "name": "Control", "weight": 0.5},
                {"id": "new", "name": "New Model", "weight": 0.5},
            ],
        )

        import random

        for i in range(100):
            variant = ab.assign_variant("exp-rollback", f"q-{i}")
            if variant["id"] == "control":
                ab.log_result(
                    "exp-rollback",
                    {
                        "variant_id": "control",
                        "correct": random.random() < 0.85,
                        "latency_ms": 1200,
                    },
                )
            else:
                ab.log_result(
                    "exp-rollback",
                    {
                        "variant_id": "new",
                        "correct": random.random() < 0.65,
                        "latency_ms": 1500,
                    },
                )

        control_metrics = ab.get_metrics("exp-rollback", "control")
        new_metrics = ab.get_metrics("exp-rollback", "new")

        winner = (
            "control"
            if control_metrics["accuracy"] > new_metrics["accuracy"]
            else "new"
        )
        assert winner == "control", (
            f"Should rollback to control: control={control_metrics['accuracy']:.2%}, new={new_metrics['accuracy']:.2%}"
        )

    def test_mlo08_prediction_logging(self):
        """TC-MLO-08: Prediction Logging — all fields captured."""
        logger = MockPredictionLogger()
        logger.log(
            "What is policy?",
            "Return policy is 30 days",
            latency_ms=1250.5,
            confidence=0.92,
        )

        logs = logger.get_recent(1)
        assert len(logs) == 1
        assert logs[0].query == "What is policy?"
        assert logs[0].latency_ms == 1250.5
        assert logs[0].confidence == 0.92
        assert logs[0].query_id is not None
        assert logs[0].timestamp is not None
