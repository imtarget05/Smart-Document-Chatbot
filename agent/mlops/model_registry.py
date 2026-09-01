"""
Model Registry for Smart Document Chatbot.

Manages model versions, quality gates, and deployment stages.
Stores records locally in JSON files with optional MLflow integration.
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

REGISTRY_DIR = os.getenv("MODEL_REGISTRY_DIR", "model_registry")
MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "mlruns")

QUALITY_THRESHOLD = {
    "retrieval_accuracy": 0.75,
    "answer_correctness": 0.70,
    "hallucination_rate": 0.20,
    "faithfulness": 0.70,
}

VALID_STAGES = ["None", "Staging", "Production", "Archived"]


class ModelVersion:
    """Represents a single model version with metadata."""

    def __init__(
        self,
        version: str,
        model_name: str,
        stage: str = "None",
        metrics: Optional[Dict[str, float]] = None,
        config: Optional[Dict[str, Any]] = None,
        created_at: Optional[str] = None,
        mlflow_run_id: Optional[str] = None,
        description: str = "",
    ):
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
    """Local model registry backed by JSON files + optional MLflow integration."""

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
        self,
        name: str,
        version: str,
        metrics: Optional[Dict[str, float]] = None,
        config: Optional[Dict[str, Any]] = None,
        stage: str = "Staging",
        mlflow_run_id: Optional[str] = None,
        description: str = "",
        force: bool = False,
    ) -> Optional[ModelVersion]:
        """
        Register a new model version.

        Args:
            name: Model name (e.g., "rag-retriever")
            version: Semantic version string (e.g., "1.0.0")
            metrics: Evaluation metrics
            config: Model configuration
            stage: Initial stage (default: Staging)
            mlflow_run_id: Associated MLflow run ID
            description: Human-readable description
            force: Bypass quality gate

        Returns:
            ModelVersion if registered, None if quality gate fails
        """
        if metrics and not force:
            passed, failures = self.passes_quality_gate(metrics)
            if not passed:
                logger.warning(
                    f"Quality gate FAILED for {name} v{version}: {failures}"
                )
                return None

        versions = self._load_versions(name)
        existing_versions = [v["version"] for v in versions]
        if version in existing_versions and not force:
            logger.warning(f"Model {name} v{version} already exists. Use force=True to overwrite.")
            return None

        if version in existing_versions and force:
            versions = [v for v in versions if v["version"] != version]

        mv = ModelVersion(
            version=version,
            model_name=name,
            stage=stage,
            metrics=metrics or {},
            config=config or {},
            mlflow_run_id=mlflow_run_id,
            description=description,
        )

        versions.append(mv.to_dict())
        self._save_versions(name, versions)

        logger.info(f"Model registered: {name} v{version} (stage={stage})")
        return mv

    def promote_model(self, name: str, version: str, stage: str) -> bool:
        """
        Promote a model version to a new stage.

        Args:
            name: Model name
            version: Version string
            stage: Target stage (Staging/Production/Archived)

        Returns:
            True if promoted successfully
        """
        if stage not in VALID_STAGES:
            logger.error(f"Invalid stage '{stage}'. Must be one of {VALID_STAGES}")
            return False

        versions = self._load_versions(name)
        found = False
        for v in versions:
            if v["version"] == version:
                v["stage"] = stage
                found = True
            elif stage == "Production" and v.get("stage") == "Production":
                v["stage"] = "Archived"

        if found:
            self._save_versions(name, versions)
            logger.info(f"Model promoted: {name} v{version} -> {stage}")
        return found

    def get_model(self, name: str, stage: str = "Production") -> Optional[ModelVersion]:
        """
        Get the current model version for a given stage.

        Args:
            name: Model name
            stage: Stage to retrieve (default: Production)

        Returns:
            ModelVersion if found, None otherwise
        """
        versions = self._load_versions(name)
        for v in reversed(versions):
            if v.get("stage") == stage:
                return ModelVersion.from_dict(v)
        return None

    def list_versions(self, name: str) -> List[ModelVersion]:
        """List all versions of a model."""
        versions = self._load_versions(name)
        return [ModelVersion.from_dict(v) for v in versions]

    def compare_versions(self, name: str, v1: str, v2: str) -> Dict[str, Any]:
        """Compare two model versions side-by-side."""
        versions = self._load_versions(name)
        v1_data = next((v for v in versions if v["version"] == v1), None)
        v2_data = next((v for v in versions if v["version"] == v2), None)
        if not v1_data or not v2_data:
            return {"error": "Version not found"}
        all_keys = set(
            list(v1_data["metrics"].keys()) + list(v2_data["metrics"].keys())
        )
        return {
            "v1": v1_data,
            "v2": v2_data,
            "metric_diff": {
                k: v2_data["metrics"].get(k, 0) - v1_data["metrics"].get(k, 0)
                for k in all_keys
            },
        }


# Singleton instance
_registry = None


def _get_registry() -> ModelRegistry:
    global _registry
    if _registry is None:
        _registry = ModelRegistry()
    return _registry


def register_model(
    name: str,
    version: str,
    metrics: Optional[Dict[str, float]] = None,
    config: Optional[Dict[str, Any]] = None,
    stage: str = "Staging",
    mlflow_run_id: Optional[str] = None,
    description: str = "",
    force: bool = False,
) -> Optional[ModelVersion]:
    """Module-level convenience function. See ModelRegistry.register_model."""
    return _get_registry().register_model(
        name=name, version=version, metrics=metrics, config=config,
        stage=stage, mlflow_run_id=mlflow_run_id, description=description,
        force=force
    )


def promote_model(name: str, version: str, stage: str) -> bool:
    """Module-level convenience function. See ModelRegistry.promote_model."""
    return _get_registry().promote_model(name=name, version=version, stage=stage)


def get_model(name: str, stage: str = "Production") -> Optional[ModelVersion]:
    """Module-level convenience function. See ModelRegistry.get_model."""
    return _get_registry().get_model(name=name, stage=stage)
