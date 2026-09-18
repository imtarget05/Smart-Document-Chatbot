"""
Airflow DAG: model retrain pipeline for the Vietnamese supply-chain adapter.

Orchestrates the fine-tuning loop against the agent service contract:
  1. build_dataset    - regenerate train/valid jsonl from eval/ ground truth
  2. submit_training  - POST /v1/training-jobs -> {job_id, status}
  3. poll_training    - GET /v1/training-jobs/{job_id} until terminal
  4. verify_result    - validate adapter URI, SHA-256, version, quality gate
                        and reject stale artifacts from earlier DAG runs

NOTE (honest operational constraint):
  The actual fine-tune needs a GPU runner. This DAG *orchestrates*: the agent
  service owns the runner call and the immutable result. Airflow never
  inspects a pre-existing adapter file to declare success — it validates the
  result returned for *this* job id.

Credentials come from Airflow Variables (never hardcoded):
  - AIRFLOW_VAR_RETRAIN_TOKEN   : internal service token (X-Internal-Token)
  - AIRFLOW_VAR_AGENT_BASE_URL  : e.g. http://agent:9000
  - AIRFLOW_VAR_FINETUNE_ROOT   : project root mounted at /opt/smartdoc
"""

from __future__ import annotations

import json
import os
import subprocess
import time
from datetime import datetime, timedelta

from airflow.decorators import dag, task
from airflow.exceptions import AirflowException
from airflow.models.variable import Variable

default_args = {
    "owner": "mlops",
    "retries": 1,
    "retry_delay": timedelta(minutes=10),
    "execution_timeout": timedelta(hours=2),
}

# Quality gate for the candidate adapter (mirrors agent/model_registry.py).
QUALITY_THRESHOLD = {
    "retrieval_accuracy": 0.75,
    "answer_correctness": 0.70,
    "hallucination_rate": 0.20,
}
POLL_INTERVAL_SEC = 30
POLL_MAX_ATTEMPTS = 60


def _agent_base_url() -> str:
    return Variable.get("AGENT_BASE_URL", default_var="http://agent:9000").rstrip("/")


def _retrain_token() -> str:
    return Variable.get("RETRAIN_TOKEN", default_var="")


def _finetune_root() -> str:
    return Variable.get("FINETUNE_ROOT", default_var="/opt/smartdoc")


def _post_json(url: str, payload: dict, token: str) -> dict:
    import urllib.request

    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={"Content-Type": "application/json", "X-Internal-Token": token},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _get_json(url: str, token: str) -> dict:
    import urllib.request

    req = urllib.request.Request(
        url, method="GET", headers={"X-Internal-Token": token}
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


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
    def submit_training(train_path: str) -> dict:
        """Submit POST /v1/training-jobs with the internal token in the JSON contract."""
        token = _retrain_token()
        if not token:
            raise AirflowException("RETRAIN_TOKEN Airflow Variable is empty")
        url = f"{_agent_base_url()}/v1/training-jobs"
        request_payload = {"dataset_uri": train_path, "token": token}
        try:
            body = _post_json(url, request_payload, token)
        except Exception as exc:  # noqa: BLE001 - surface clearly to Airflow
            raise AirflowException(f"training job submission failed: {exc}") from exc
        job_id = body.get("job_id")
        if not job_id:
            raise AirflowException(f"no job_id returned: {body}")
        return {"job_id": job_id, "status": body.get("status"), "submitted_at": time.time()}

    @task
    def poll_training(submission: dict) -> dict:
        """Poll to terminal status; a pending job waits rather than passing."""
        token = _retrain_token()
        job_id = submission["job_id"]
        url = f"{_agent_base_url()}/v1/training-jobs/{job_id}"
        last: dict = {}
        for _ in range(POLL_MAX_ATTEMPTS):
            try:
                last = _get_json(url, token)
            except Exception as exc:  # noqa: BLE001
                raise AirflowException(f"polling {job_id} failed: {exc}") from exc
            status = str(last.get("status", "")).upper()
            if status == "SUCCEEDED":
                return last
            if status == "FAILED":
                raise AirflowException(
                    f"training job {job_id} FAILED: {last.get('failure_reason')}"
                )
            time.sleep(POLL_INTERVAL_SEC)
        raise AirflowException(f"training job {job_id} did not reach terminal state")

    @task
    def verify_adapter(result: dict) -> str:
        """Validate the immutable result of *this* job: URI, SHA-256, gate."""
        if str(result.get("status", "")).upper() != "SUCCEEDED":
            raise AirflowException(f"job not succeeded: {result.get('status')}")
        for key in ("adapter_uri", "sha256", "model_version"):
            if not result.get(key):
                raise AirflowException(f"result missing {key}: {result}")
        digest = str(result["sha256"])
        if len(digest) != 64:
            raise AirflowException(f"invalid adapter checksum: {digest!r}")
        metrics = result.get("metrics") or {}
        failures = []
        for metric, threshold in QUALITY_THRESHOLD.items():
            if metric not in metrics:
                failures.append(f"{metric}: missing")
                continue
            value = float(metrics[metric])
            if metric == "hallucination_rate":
                if value > threshold:
                    failures.append(f"{metric}: {value:.2%} > {threshold:.2%}")
            elif value < threshold:
                failures.append(f"{metric}: {value:.2%} < {threshold:.2%}")
        if failures:
            raise AirflowException(f"quality gate failed: {failures}")
        return (
            f"adapter ok: {result['adapter_uri']} "
            f"(version={result['model_version']}, sha256={digest[:12]}…)"
        )

    train_path = build_dataset()
    submission = submit_training(train_path)
    result = poll_training(submission)
    verify_adapter(result)


# Register the DAG
model_retrain_pipeline()
