"""
MLflow experiment tracking for Smart Document Chatbot.

Provides functions to log evaluation runs, retrieval experiments,
and compare different ML pipeline configurations.
"""

import os
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "mlruns")
EXPERIMENT_NAME = os.getenv("MLFLOW_EXPERIMENT_NAME", "smart-doc-chatbot")

try:
    import mlflow
    from mlflow.tracking import MlflowClient
    MLFLOW_AVAILABLE = True
except ImportError:
    MLFLOW_AVAILABLE = False
    mlflow = None
    MlflowClient = None
    logger.warning("mlflow not installed. Tracking calls will be no-ops.")


def _get_client() -> Optional["MlflowClient"]:
    """Get or create MLflow client with configured tracking URI."""
    if not MLFLOW_AVAILABLE:
        return None
    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    return MlflowClient()


def _get_git_commit() -> str:
    """Get current git commit hash for reproducibility."""
    try:
        import subprocess
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=5
        )
        return result.stdout.strip() if result.returncode == 0 else "unknown"
    except Exception:
        return "unknown"


def _ensure_experiment() -> Optional[str]:
    """Ensure the experiment exists and return its ID."""
    if not MLFLOW_AVAILABLE:
        return None
    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    experiment = mlflow.get_experiment_by_name(EXPERIMENT_NAME)
    if experiment is None:
        return mlflow.create_experiment(
            EXPERIMENT_NAME,
            tags={"project": "smart-doc-chatbot"}
        )
    return experiment.experiment_id


def log_eval_run(
    metrics: Dict[str, float],
    params: Optional[Dict[str, Any]] = None,
    artifacts: Optional[Dict[str, str]] = None,
    run_name: Optional[str] = None,
) -> Optional[str]:
    """
    Log an evaluation run with all metrics and parameters.

    Args:
        metrics: Dictionary of metric_name -> value
        params: Dictionary of parameter_name -> value
        artifacts: Dictionary of artifact_name -> file_path
        run_name: Optional name for the run

    Returns:
        Run ID if successful, None otherwise
    """
    if not MLFLOW_AVAILABLE:
        logger.warning("MLflow not available. Skipping log_eval_run.")
        return None

    experiment_id = _ensure_experiment()
    if experiment_id is None:
        return None

    if run_name is None:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        run_name = f"eval_{timestamp}"

    tags = {
        "git_commit": _get_git_commit(),
        "run_type": "evaluation",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    with mlflow.start_run(experiment_id=experiment_id, run_name=run_name, tags=tags):
        if params:
            for key, value in params.items():
                mlflow.log_param(str(key), value)

        for key, value in metrics.items():
            mlflow.log_metric(str(key), value)

        if artifacts:
            for name, path in artifacts.items():
                if os.path.isdir(path):
                    mlflow.log_artifacts(path, artifact_path=name)
                elif os.path.isfile(path):
                    mlflow.log_artifact(path, artifact_path=name)

        run_id = mlflow.active_run().info.run_id
        logger.info(f"Logged eval run: {run_id}")
        return run_id


def log_retrieval_experiment(
    chunk_size: int,
    top_k: int,
    embedding_model: str,
    metrics: Dict[str, float],
    additional_params: Optional[Dict[str, Any]] = None,
) -> Optional[str]:
    """
    Log a retrieval tuning experiment.

    Args:
        chunk_size: Document chunk size used
        top_k: Number of top results retrieved
        embedding_model: Name of the embedding model
        metrics: Dictionary of metric_name -> value
        additional_params: Optional additional parameters

    Returns:
        Run ID if successful, None otherwise
    """
    params = {
        "chunk_size": chunk_size,
        "top_k": top_k,
        "embedding_model": embedding_model,
    }
    if additional_params:
        params.update(additional_params)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    run_name = f"retrieval_cs{chunk_size}_k{top_k}_{timestamp}"

    return log_eval_run(
        metrics=metrics,
        params=params,
        run_name=run_name,
    )


def compare_runs(run_ids: List[str]) -> Dict[str, Any]:
    """
    Compare different experiment runs side-by-side.

    Args:
        run_ids: List of MLflow run IDs to compare

    Returns:
        Dictionary with run comparison data
    """
    client = _get_client()
    if client is None:
        return {"error": "MLflow not available"}

    runs_data = {}
    for run_id in run_ids:
        try:
            run = client.get_run(run_id)
            runs_data[run_id] = {
                "run_name": run.data.tags.get("run_name", run_id),
                "metrics": dict(run.data.metrics),
                "params": dict(run.data.params),
                "tags": dict(run.data.tags),
                "status": run.info.status,
                "start_time": run.info.start_time,
            }
        except Exception as e:
            runs_data[run_id] = {"error": str(e)}

    all_metrics = set()
    for data in runs_data.values():
        if "metrics" in data:
            all_metrics.update(data["metrics"].keys())

    comparison = {}
    for metric in sorted(all_metrics):
        comparison[metric] = {
            run_id: data.get("metrics", {}).get(metric, None)
            for run_id, data in runs_data.items()
        }

    return {
        "runs": runs_data,
        "comparison": comparison,
    }


def get_best_run(
    metric: str,
    mode: str = "max",
    experiment_id: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    Get the best run by a given metric.

    Args:
        metric: Metric name to optimize
        mode: "max" for maximize, "min" for minimize
        experiment_id: Optional experiment ID (uses default if not provided)

    Returns:
        Dictionary with best run info
    """
    if not MLFLOW_AVAILABLE:
        logger.warning("MLflow not available. Cannot get best run.")
        return None

    client = _get_client()
    if client is None:
        return None

    if experiment_id is None:
        experiment_id = _ensure_experiment()
    if experiment_id is None:
        return None

    order = "DESC" if mode == "max" else "ASC"
    runs = client.search_runs(
        experiment_ids=[experiment_id],
        filter_string="",
        run_view_type=mlflow.entities.ViewType.ACTIVE_ONLY,
        order_by=[f"metrics.{metric} {order}"],
        max_results=1,
    )

    if not runs:
        return None

    best = runs[0]
    return {
        "run_id": best.info.run_id,
        "run_name": best.data.tags.get("run_name", best.info.run_id),
        "metrics": dict(best.data.metrics),
        "params": dict(best.data.params),
        "metric_value": best.data.metrics.get(metric),
    }
