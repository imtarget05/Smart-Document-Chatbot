"""
MLflow Experiment Tracking for Smart Document Chatbot.

Provides a singleton tracker that logs RAG evaluation runs,
query-level metrics, and model parameters to a local or remote
MLflow Tracking Server.

Usage:
    from agent.mlflow_tracker import tracker

    tracker.start_run(run_name="eval-run-001")
    tracker.log_params({"model": "llama3.2:3b", "chunk_size": 512})
    tracker.log_metrics({"retrieval_accuracy": 0.85, "avg_latency_ms": 1420})
    tracker.end_run()
"""

import os
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://mlflow:5000")
EXPERIMENT_NAME = os.getenv("MLFLOW_EXPERIMENT_NAME", "smart-document-chatbot")


class MLflowTracker:
    """Singleton MLflow tracker for the agent service."""

    def __init__(self):
        self._client = None
        self._run_id: Optional[str] = None
        self._experiment_id: Optional[str] = None
        self._initialized = False

    def _ensure_init(self):
        if self._initialized:
            return
        try:
            import mlflow
            mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
            self._client = mlflow.MlflowClient()
            experiment = mlflow.set_experiment(EXPERIMENT_NAME)
            self._experiment_id = experiment.experiment_id
            self._initialized = True
            logger.info(f"MLflow tracker initialized: uri={MLFLOW_TRACKING_URI}, "
                        f"experiment={EXPERIMENT_NAME} (id={self._experiment_id})")
        except Exception as e:
            logger.warning(f"MLflow init failed (non-fatal): {e}")
            self._initialized = False

    def start_run(self, run_name: Optional[str] = None, tags: Optional[Dict[str, str]] = None):
        self._ensure_init()
        if not self._initialized:
            return
        try:
            import mlflow
            run = mlflow.start_run(experiment_id=self._experiment_id, run_name=run_name, tags=tags)
            self._run_id = run.info.run_id
            logger.info(f"MLflow run started: {self._run_id} ({run_name})")
        except Exception as e:
            logger.warning(f"MLflow start_run failed: {e}")

    def log_params(self, params: Dict[str, Any]):
        if not self._initialized or not self._run_id:
            return
        try:
            import mlflow
            for k, v in params.items():
                mlflow.log_param(k, str(v))
        except Exception as e:
            logger.warning(f"MLflow log_params failed: {e}")

    def log_metrics(self, metrics: Dict[str, float], step: Optional[int] = None):
        if not self._initialized or not self._run_id:
            return
        try:
            import mlflow
            for k, v in metrics.items():
                mlflow.log_metric(k, v, step=step)
        except Exception as e:
            logger.warning(f"MLflow log_metrics failed: {e}")

    def log_artifact(self, local_path: str):
        if not self._initialized or not self._run_id:
            return
        try:
            import mlflow
            mlflow.log_artifact(local_path)
        except Exception as e:
            logger.warning(f"MLflow log_artifact failed: {e}")

    def end_run(self, status: str = "FINISHED"):
        if not self._initialized or not self._run_id:
            return
        try:
            import mlflow
            mlflow.end_run(status=status)
            logger.info(f"MLflow run ended: {self._run_id} (status={status})")
            self._run_id = None
        except Exception as e:
            logger.warning(f"MLflow end_run failed: {e}")

    def get_run_url(self) -> Optional[str]:
        if not self._initialized or not self._run_id:
            return None
        return f"{MLFLOW_TRACKING_URI}/#/experiments/{self._experiment_id}/runs/{self._run_id}"


# Singleton instance
tracker = MLflowTracker()
