"""
MLflow Model Registry for Smart Document Chatbot.

Manages model versions, quality gates, and deployment stages.
Registered models are stored in MLflow with metadata about
evaluation metrics, training data, and configuration.

Usage:
    from agent.model_registry import registry

    # Register a new model version after eval passes
    registry.register_model(
        model_name="rag-retriever",
        version="1.0.0",
        metrics={"retrieval_accuracy": 0.85, "hallucination_rate": 0.10},
        config={"chunk_size": 512, "embedding_model": "nomic-embed-text"},
        artifact_path=None
    )

    # Get the current production model
    prod_model = registry.get_model("rag-retriever", stage="Production")
"""

import os
import json
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://mlflow:5000")
REGISTRY_DIR = os.getenv("MODEL_REGISTRY_DIR", "model_registry")
QUALITY_THRESHOLD = {
    "retrieval_accuracy": 0.75,
    "answer_correctness": 0.70,
    "hallucination_rate": 0.20,
}


class ModelVersion:
    """Represents a single model version with metadata."""

    def __init__(self, version: str, model_name: str, stage: str = "None",
                 metrics: Optional[Dict[str, float]] = None,
                 config: Optional[Dict[str, Any]] = None,
                 created_at: Optional[str] = None,
                 mlflow_run_id: Optional[str] = None,
                 description: str = ""):
        self.version = version
        self.model_name = model_name
        self.stage = stage
        self.metrics = metrics or {}
        self.config = config or {}
        self.created_at = created_at or datetime.now(timezone.utc).isoformat()
        self.mlflow_run_id = mlflow_run_id
        self.description = description

    def to_dict(self) -> Dict[str, Any]:
        return {
            "version": self.version,
            "model_name": self.model_name,
            "stage": self.stage,
            "metrics": self.metrics,
            "config": self.config,
            "created_at": self.created_at,
            "mlflow_run_id": self.mlflow_run_id,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ModelVersion":
        return cls(**data)


class ModelRegistry:
    """Local model registry backed by JSON files + optional MLflow logging."""

    def __init__(self, registry_dir: Optional[str] = None):
        self.registry_dir = Path(registry_dir or REGISTRY_DIR)
        self.registry_dir.mkdir(parents=True, exist_ok=True)

    def _get_model_path(self, model_name: str) -> Path:
        return self.registry_dir / f"{model_name}.json"

    def _load_versions(self, model_name: str) -> List[Dict[str, Any]]:
        path = self._get_model_path(model_name)
        if not path.exists():
            return []
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _save_versions(self, model_name: str, versions: List[Dict[str, Any]]):
        path = self._get_model_path(model_name)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(versions, f, indent=2, ensure_ascii=False)

    def passes_quality_gate(self, metrics: Dict[str, float]) -> tuple[bool, List[str]]:
        """Check if metrics pass the quality threshold for registration."""
        failures = []
        for metric, threshold in QUALITY_THRESHOLD.items():
            if metric in metrics:
                if metric == "hallucination_rate":
                    if metrics[metric] > threshold:
                        failures.append(f"{metric}: {metrics[metric]:.2%} > {threshold:.2%}")
                else:
                    if metrics[metric] < threshold:
                        failures.append(f"{metric}: {metrics[metric]:.2%} < {threshold:.2%}")
        return len(failures) == 0, failures

    def register_model(self, model_name: str, version: str,
                       metrics: Optional[Dict[str, float]] = None,
                       config: Optional[Dict[str, Any]] = None,
                       mlflow_run_id: Optional[str] = None,
                       description: str = "",
                       force: bool = False) -> Optional[ModelVersion]:
        """Register a new model version. Returns None if quality gate fails."""
        if metrics and not force:
            passed, failures = self.passes_quality_gate(metrics)
            if not passed:
                logger.warning(f"Quality gate FAILED for {model_name} v{version}: {failures}")
                return None

        versions = self._load_versions(model_name)
        existing_versions = [v["version"] for v in versions]
        if version in existing_versions:
            logger.warning(f"Model {model_name} v{version} already exists. Use force=True to overwrite.")
            if not force:
                return None
            versions = [v for v in versions if v["version"] != version]

        mv = ModelVersion(
            version=version,
            model_name=model_name,
            stage="Staging",
            metrics=metrics or {},
            config=config or {},
            mlflow_run_id=mlflow_run_id,
            description=description,
        )

        versions.append(mv.to_dict())
        self._save_versions(model_name, versions)

        logger.info(f"Model registered: {model_name} v{version} (stage=Staging)")
        return mv

    def promote_model(self, model_name: str, version: str, stage: str) -> bool:
        """Promote a model version to a new stage (Staging/Production/Archived)."""
        versions = self._load_versions(model_name)
        found = False
        for v in versions:
            if v["version"] == version:
                v["stage"] = stage
                found = True
            elif v["model_name"] == model_name and v.get("stage") == stage and stage == "Production":
                v["stage"] = "Archived"
        if found:
            self._save_versions(model_name, versions)
            logger.info(f"Model promoted: {model_name} v{version} → {stage}")
        return found

    def get_model(self, model_name: str, stage: str = "Production") -> Optional[ModelVersion]:
        """Get the current model version for a given stage."""
        versions = self._load_versions(model_name)
        for v in reversed(versions):
            if v.get("stage") == stage:
                return ModelVersion.from_dict(v)
        return None

    def list_versions(self, model_name: str) -> List[ModelVersion]:
        """List all versions of a model."""
        versions = self._load_versions(model_name)
        return [ModelVersion.from_dict(v) for v in versions]

    def compare_versions(self, model_name: str, v1: str, v2: str) -> Dict[str, Any]:
        """Compare two model versions side-by-side."""
        versions = self._load_versions(model_name)
        v1_data = next((v for v in versions if v["version"] == v1), None)
        v2_data = next((v for v in versions if v["version"] == v2), None)
        if not v1_data or not v2_data:
            return {"error": "Version not found"}
        return {
            "v1": v1_data,
            "v2": v2_data,
            "metric_diff": {
                k: v2_data["metrics"].get(k, 0) - v1_data["metrics"].get(k, 0)
                for k in set(list(v1_data["metrics"].keys()) + list(v2_data["metrics"].keys()))
            }
        }


# Singleton
registry = ModelRegistry()
