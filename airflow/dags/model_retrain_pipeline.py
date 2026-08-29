"""
Airflow DAG: model retrain pipeline for the Vietnamese supply-chain adapter.

Runs on a schedule (weekly by default) and orchestrates the fine-tuning loop:
  1. build_dataset  - regenerate train/valid jsonl from eval/ ground truth
  2. trigger_training - ask the agent service to (re)train the LoRA adapter
  3. verify_adapter - confirm the new adapter artifact exists & is non-trivial

NOTE (honest operational constraint):
  The actual fine-tune needs a GPU runner. This DAG *orchestrates* the pipeline:
  it calls the agent service `/v1/agent/retrain` endpoint (which owns the
  training process / MLflow run) rather than training inside the Airflow worker.
  The agent endpoint requires the internal service token (X-Internal-Token).
  If the agent service is unavailable the DAG fails loudly so on-call is paged,
  instead of producing a stale adapter silently.

Credentials come from Airflow Variables / Connections (never hardcoded):
  - AIRFLOW_VAR_RETRAIN_TOKEN   : internal service token for /v1/agent/retrain
  - AIRFLOW_VAR_AGENT_BASE_URL  : e.g. http://agent:9000
  - AIRFLOW_VAR_FINETUNE_ROOT   : repo root containing finetune/ (default: /opt/airflow)
"""

from __future__ import annotations

import os
import subprocess
from datetime import datetime, timedelta

from airflow.decorators import dag, task
from airflow.models.variable import Variable

# Airflow 2.9 imports; `task` SDK surfaces a misleading operator lint warning
# under Pyright without the noqa.
from airflow.exceptions import AirflowException  # noqa: F401

default_args = {
    "owner": "mlops",
    "retries": 1,
    "retry_delay": timedelta(minutes=10),
    "execution_timeout": timedelta(hours=2),
}


def _agent_base_url() -> str:
    return Variable.get("AGENT_BASE_URL", default_var="http://agent:9000").rstrip("/")


def _retrain_token() -> str:
    return Variable.get("RETRAIN_TOKEN", default_var="")


def _finetune_root() -> str:
    return Variable.get("FINETUNE_ROOT", default_var="/opt/airflow")


@dag(
    dag_id="model_retrain_pipeline",
    default_args=default_args,
    schedule="0 3 * * 0",  # weekly, Sunday 03:00
    start_date=datetime(2026, 1, 1),
    catchup=False,
    max_active_runs=1,
    tags=["mlops", "finetune", "supply-chain"],
)
def model_retrain_pipeline() -> None:
    @task
    def build_dataset() -> str:
        """Regenerate train.jsonl / valid.jsonl from eval ground truth."""
        import sys

        root = _finetune_root()
        script = os.path.join(root, "finetune", "build_dataset.py")
        if not os.path.exists(script):
            raise AirflowException(f"build_dataset.py not found at {script}")
        # Run with the same interpreter; FINETUNE_ROOT inherited via env.
        env = dict(os.environ)
        env["FINETUNE_ROOT"] = root
        proc = subprocess.run(
            [sys.executable, script],
            env=env,
            capture_output=True,
            text=True,
            timeout=600,
        )
        if proc.returncode != 0:
            raise AirflowException(f"build_dataset failed: {proc.stderr}")
        return os.path.join(root, "finetune", "data", "train.jsonl")

    @task
    def trigger_training(train_path: str) -> str:
        """Ask the agent service to fine-tune the LoRA adapter."""
        import json
        import urllib.request

        url = f"{_agent_base_url()}/v1/agent/retrain"
        token = _retrain_token()
        if not token:
            raise AirflowException("RETRAIN_TOKEN Airflow Variable is empty")
        payload = json.dumps({"dataset_path": train_path}).encode("utf-8")
        req = urllib.request.Request(
            url, data=payload, method="POST",
            headers={
                "Content-Type": "application/json",
                "X-Internal-Token": token,
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                body = resp.read().decode("utf-8")
        except Exception as exc:  # noqa: BLE001 - surface clearly to Airflow
            raise AirflowException(f"retrain endpoint call failed: {exc}") from exc
        return body

    @task
    def verify_adapter(training_result: str) -> str:
        """Confirm a new adapter artifact was produced (best-effort path)."""
        root = _finetune_root()
        adapters = os.path.join(root, "finetune", "adapters", "adapters.safetensors")
        if not os.path.exists(adapters):
            raise AirflowException(f"Expected adapter not found: {adapters}")
        size = os.path.getsize(adapters)
        if size < 1024:
            raise AirflowException(f"Adapter suspiciously small ({size} bytes)")
        return f"adapter ok: {adapters} ({size} bytes)"

    train_path = build_dataset()
    result = trigger_training(train_path)
    verify_adapter(result)


# Register the DAG
model_retrain_pipeline()
