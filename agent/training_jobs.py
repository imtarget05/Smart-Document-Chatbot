"""Asynchronous training-job orchestration (plan 2026-09-18 Task 3).

Airflow (and the admin API) must never claim "a LoRA adapter was trained"
unless a submitted job returns an immutable result with version, checksum,
evaluation metrics, and an artifact URI. This module owns that contract:

  POST /v1/training-jobs           -> {job_id, status}
  GET  /v1/training-jobs/{job_id}  -> {status, adapter_uri, sha256,
                                       metrics, model_version}

Persistence follows the existing JSON-file registry pattern
(agent/model_registry.py) so no new dependency or database is required.
The GPU runner stays external: this service submits and validates.
"""
from __future__ import annotations

import hashlib
import json
import os
import secrets
import urllib.error
import urllib.request
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

# --- statuses (terminal ones never change again) ---------------------------
STATUS_PENDING = "PENDING"
STATUS_RUNNING = "RUNNING"
STATUS_SUCCEEDED = "SUCCEEDED"
STATUS_FAILED = "FAILED"
TERMINAL_STATUSES = frozenset({STATUS_SUCCEEDED, STATUS_FAILED})

JOBS_DIR = Path(os.getenv("TRAINING_JOBS_DIR", "agent/training_jobs"))


class TrainingJobError(RuntimeError):
    """Raised when a job submission or result is not trustworthy."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class TrainingJob:
    """A single training submission and its immutable result."""

    job_id: str
    dataset_uri: str
    status: str = STATUS_PENDING
    requested_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)
    runner_job_id: Optional[str] = None
    callback_token: str = ""
    model_version: Optional[str] = None
    adapter_uri: Optional[str] = None
    sha256: Optional[str] = None
    metrics: Dict[str, float] = field(default_factory=dict)
    failure_reason: Optional[str] = None
    completed_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def result_payload(self) -> Dict[str, Any]:
        """The GET contract: status + immutable result identity."""
        return {
            "job_id": self.job_id,
            "status": self.status,
            "adapter_uri": self.adapter_uri,
            "sha256": self.sha256,
            "metrics": self.metrics,
            "model_version": self.model_version,
            "failure_reason": self.failure_reason,
            "completed_at": self.completed_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TrainingJob":
        known = set(cls.__dataclass_fields__)  # type: ignore[attr-defined]
        return cls(**{k: v for k, v in data.items() if k in known})


class TrainingJobStore:
    """JSON-file persisted job store (one file per job)."""

    def __init__(self, base_dir: Optional[str] = None) -> None:
        self.base_dir = Path(base_dir or JOBS_DIR)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, job_id: str) -> Path:
        safe = "".join(c for c in job_id if c.isalnum() or c in "-_")
        return self.base_dir / f"{safe}.json"

    def save(self, job: TrainingJob) -> None:
        job.updated_at = _now()
        tmp = self._path(job.job_id).with_suffix(".json.tmp")
        tmp.write_text(json.dumps(job.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, self._path(job.job_id))

    def load(self, job_id: str) -> Optional[TrainingJob]:
        path = self._path(job_id)
        if not path.exists():
            return None
        return TrainingJob.from_dict(json.loads(path.read_text(encoding="utf-8")))

    def list_ids(self) -> list[str]:
        return sorted(p.stem for p in self.base_dir.glob("*.json"))


class TrainingRunnerClient:
    """Submits a dataset to the external GPU runner and validates results."""

    def __init__(self, base_url: Optional[str] = None, timeout: float = 30.0) -> None:
        self.base_url = (base_url or os.getenv("TRAINING_RUNNER_URL", "")).strip().rstrip("/")
        self.timeout = timeout

    @property
    def configured(self) -> bool:
        return bool(self.base_url)

    def submit(self, dataset_uri: str, callback_url: str, callback_token: str) -> str:
        """POST the job to the runner and return its remote job id."""
        if not self.configured:
            raise TrainingJobError("TRAINING_RUNNER_URL is not configured")
        payload = json.dumps({
            "dataset_uri": dataset_uri,
            "callback_url": callback_url,
            "callback_token": callback_token,
        }).encode("utf-8")
        req = urllib.request.Request(
            f"{self.base_url}/jobs",
            data=payload,
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                body = json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, ValueError, OSError) as exc:
            raise TrainingJobError(f"runner submission failed: {exc}") from exc
        runner_job_id = body.get("job_id")
        if not runner_job_id:
            raise TrainingJobError("runner did not return a job_id")
        return str(runner_job_id)

    def poll(self, runner_job_id: str) -> Dict[str, Any]:
        """Read the runner's authoritative status for a job."""
        if not self.configured:
            raise TrainingJobError("TRAINING_RUNNER_URL is not configured")
        req = urllib.request.Request(f"{self.base_url}/jobs/{runner_job_id}", method="GET")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, ValueError, OSError) as exc:
            raise TrainingJobError(f"runner poll failed: {exc}") from exc


def submit_training_job(
    dataset_uri: str,
    store: Optional[TrainingJobStore] = None,
    runner: Optional[TrainingRunnerClient] = None,
) -> TrainingJob:
    """Create a job row, submit it to the runner, and persist runner identity."""
    if not dataset_uri:
        raise TrainingJobError("dataset_uri is required")
    store = store or TrainingJobStore()
    runner = runner or TrainingRunnerClient()
    job = TrainingJob(
        job_id=f"TJ-{uuid.uuid4().hex[:12].upper()}",
        dataset_uri=dataset_uri,
        callback_token=secrets.token_urlsafe(24),
    )
    store.save(job)
    if not runner.configured:
        job.status = STATUS_FAILED
        job.failure_reason = "TRAINING_RUNNER_URL is not configured"
        job.completed_at = _now()
        store.save(job)
        raise TrainingJobError(str(job.failure_reason))
    try:
        runner_job_id = runner.submit(
            dataset_uri=dataset_uri,
            callback_url=f"/v1/training-jobs/{job.job_id}/callback",
            callback_token=job.callback_token,
        )
    except TrainingJobError as exc:
        job.status = STATUS_FAILED
        job.failure_reason = str(exc)
        job.completed_at = _now()
        store.save(job)
        raise
    job.runner_job_id = runner_job_id
    job.status = STATUS_RUNNING
    store.save(job)
    return job


# --- result validation -----------------------------------------------------
REQUIRED_RESULT_FIELDS = ("model_version", "adapter_uri", "sha256")


def validate_training_result(result: Dict[str, Any]) -> tuple[bool, str]:
    """Reject a result that cannot prove a *new* adapter was produced."""
    for key in REQUIRED_RESULT_FIELDS:
        if not result.get(key):
            return False, f"missing_result_field:{key}"
    digest = str(result.get("sha256", ""))
    if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest.lower()):
        return False, "invalid_result_checksum"
    metrics = result.get("metrics") or {}
    if not isinstance(metrics, dict) or not metrics:
        return False, "missing_result_metrics"
    return True, ""


def apply_runner_result(
    job: TrainingJob,
    result: Dict[str, Any],
    store: Optional[TrainingJobStore] = None,
) -> TrainingJob:
    """Validate and persist an immutable runner result for one specific job."""
    store = store or TrainingJobStore()
    if job.status in TERMINAL_STATUSES:
        return job
    ok, reason = validate_training_result(result)
    if not ok:
        job.status = STATUS_FAILED
        job.failure_reason = reason
        job.completed_at = _now()
        store.save(job)
        return job
    job.status = STATUS_SUCCEEDED
    job.model_version = str(result["model_version"])
    job.adapter_uri = str(result["adapter_uri"])
    job.sha256 = str(result["sha256"]).lower()
    job.metrics = {k: float(v) for k, v in (result.get("metrics") or {}).items()}
    job.completed_at = _now()
    store.save(job)
    return job


def result_fingerprint(job: TrainingJob) -> str:
    """Stable digest of a job's immutable result (stale-artifact detection)."""
    blob = json.dumps({
        "job_id": job.job_id,
        "runner_job_id": job.runner_job_id,
        "adapter_uri": job.adapter_uri,
        "sha256": job.sha256,
        "model_version": job.model_version,
        "completed_at": job.completed_at,
    }, sort_keys=True)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def register_candidate_from_job(job: TrainingJob) -> Optional[str]:
    """Register a SUCCEEDED job as a CANDIDATE version (never Production).

    Training completion alone must not change serving traffic; promotion is
    a separate, explicit, reversible action (`promote_candidate`).
    """
    if job.status != STATUS_SUCCEEDED:
        raise TrainingJobError("only a SUCCEEDED job can register a candidate")
    from model_registry import registry

    version = job.model_version or f"candidate-{job.job_id}"
    mv = registry.register_model(
        model_name="rag-retriever",
        version=version,
        metrics=job.metrics,
        config={
            "adapter_uri": job.adapter_uri,
            "sha256": job.sha256,
            "job_id": job.job_id,
        },
        description=f"Training job {job.job_id} candidate (not served)",
        force=True,
    )
    if mv is None:
        return None
    registry.set_stage("rag-retriever", version, "Candidate")
    return mv.version