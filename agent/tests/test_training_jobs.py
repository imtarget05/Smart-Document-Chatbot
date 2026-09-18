"""Training-job orchestration tests (plan 2026-09-18 Task 3).

Covers: submission identity, pending/running/succeeded/failed states, missing
result checksum, runner failure, candidate registration, and the explicit
promote/rollback rollout contract. Uses a deterministic fake runner.
"""
from __future__ import annotations

import pytest

from pathlib import Path

import json
import sys

ROOT = Path(__file__).resolve().parents[2]
import training_jobs as tj  # noqa: E402


class FakeRunner:
    """Deterministic runner double: records submissions, scripted failures."""

    def __init__(self, submit_error: str | None = None, poll_status: str = "SUCCEEDED"):
        self.submit_error = submit_error
        self.poll_status = poll_status
        self.submissions: list[dict] = []

    @property
    def configured(self) -> bool:
        return True

    def submit(self, dataset_uri: str, callback_url: str, callback_token: str) -> str:
        if self.submit_error:
            raise tj.TrainingJobError(self.submit_error)
        self.submissions.append({
            "dataset_uri": dataset_uri,
            "callback_url": callback_url,
            "callback_token": callback_token,
        })
        return "runner-job-1"

    def poll(self, runner_job_id: str) -> dict:
        return {"job_id": runner_job_id, "status": self.poll_status}


@pytest.fixture()
def store(tmp_path):
    return tj.TrainingJobStore(base_dir=str(tmp_path / "jobs"))


def _valid_result(**overrides) -> dict:
    result = {
        "model_version": "v2026.09.18",
        "adapter_uri": "s3://adapters/lora-t4/adapter_model.safetensors",
        "sha256": "a" * 64,
        "metrics": {
            "retrieval_accuracy": 0.82,
            "answer_correctness": 0.74,
            "hallucination_rate": 0.11,
        },
    }
    result.update(overrides)
    return result


# --- submission -----------------------------------------------------------
def test_submit_persists_job_and_runner_identity(store):
    """A submission persists a job row and records the runner's job id."""
    runner = FakeRunner()
    job = tj.submit_training_job("s3://datasets/train.jsonl", store=store, runner=runner)

    assert job.status == tj.STATUS_RUNNING
    assert job.runner_job_id == "runner-job-1"
    assert job.callback_token
    reloaded = store.load(job.job_id)
    assert reloaded is not None and reloaded.runner_job_id == "runner-job-1"
    assert runner.submissions[0]["dataset_uri"] == "s3://datasets/train.jsonl"


def test_submit_requires_dataset_uri(store):
    with pytest.raises(tj.TrainingJobError, match="dataset_uri"):
        tj.submit_training_job("", store=store, runner=FakeRunner())


def test_submit_without_configured_runner_fails_the_job(store):
    """An unconfigured runner must fail loudly, never silently 'succeed'."""

    class Unconfigured:
        configured = False

    with pytest.raises(tj.TrainingJobError, match="TRAINING_RUNNER_URL"):
        tj.submit_training_job("s3://datasets/train.jsonl", store=store, runner=Unconfigured())


def test_runner_submission_failure_marks_job_failed(store):
    """A runner failure is durable evidence, not an accepted job."""
    runner = FakeRunner(submit_error="runner unavailable")

    with pytest.raises(tj.TrainingJobError):
        tj.submit_training_job("s3://datasets/train.jsonl", store=store, runner=runner)

    jobs = [store.load(job_id) for job_id in store.list_ids()]
    assert jobs and jobs[-1].status == tj.STATUS_FAILED
    assert "runner unavailable" in (jobs[-1].failure_reason or "")


# --- result validation ----------------------------------------------------
def test_missing_checksum_result_is_rejected(store):
    runner = FakeRunner()
    job = tj.submit_training_job("s3://datasets/train.jsonl", store=store, runner=runner)

    updated = tj.apply_runner_result(job, _valid_result(sha256=""), store=store)

    assert updated.status == tj.STATUS_FAILED
    assert updated.failure_reason == "missing_result_field:sha256"
    assert updated.adapter_uri is None


def test_missing_metrics_is_rejected(store):
    runner = FakeRunner()
    job = tj.submit_training_job("s3://datasets/train.jsonl", store=store, runner=runner)

    updated = tj.apply_runner_result(job, _valid_result(metrics={}), store=store)

    assert updated.status == tj.STATUS_FAILED
    assert updated.failure_reason == "missing_result_metrics"


def test_valid_result_succeeds_with_immutable_identity(store):
    runner = FakeRunner()
    job = tj.submit_training_job("s3://datasets/train.jsonl", store=store, runner=runner)

    updated = tj.apply_runner_result(job, _valid_result(), store=store)

    assert updated.status == tj.STATUS_SUCCEEDED
    assert updated.model_version == "v2026.09.18"
    assert updated.sha256 == "a" * 64
    assert updated.metrics["retrieval_accuracy"] == 0.82
    payload = updated.result_payload()
    for key in ("status", "adapter_uri", "sha256", "metrics", "model_version"):
        assert key in payload


def test_terminal_job_result_is_immutable(store):
    """A second callback cannot rewrite a terminal job's result."""
    runner = FakeRunner()
    job = tj.submit_training_job("s3://datasets/train.jsonl", store=store, runner=runner)
    first = tj.apply_runner_result(job, _valid_result(), store=store)

    second = tj.apply_runner_result(
        first, _valid_result(model_version="v9999", sha256="b" * 64), store=store
    )

    assert second.model_version == "v2026.09.18"
    assert second.sha256 == "a" * 64


def test_result_fingerprint_distinguishes_jobs(store):
    """Stale-artifact detection needs a per-job fingerprint."""
    runner = FakeRunner()
    job_a = tj.apply_runner_result(
        tj.submit_training_job("s3://d/a.jsonl", store=store, runner=runner),
        _valid_result(), store=store,
    )
    job_b = tj.apply_runner_result(
        tj.submit_training_job("s3://d/b.jsonl", store=store, runner=runner),
        _valid_result(), store=store,
    )

    assert tj.result_fingerprint(job_a) != tj.result_fingerprint(job_b)


def test_validate_training_result_rejects_bad_checksum_format():
    ok, reason = tj.validate_training_result(_valid_result(sha256="not-a-hex-digest"))
    assert ok is False
    assert reason == "invalid_result_checksum"


# --- candidate registration ----------------------------------------------
def _fresh_registry(tmp_path, monkeypatch):
    """Point the global registry at an isolated directory."""
    import importlib

    import model_registry as mr

    importlib.reload(mr)
    reg = mr.ModelRegistry(str(tmp_path / "registry"))
    monkeypatch.setattr(mr, "registry", reg)
    return mr, reg


def test_candidate_registration_never_changes_production(tmp_path, monkeypatch):
    """A succeeded job registers a Candidate; Production stays untouched."""
    mr, reg = _fresh_registry(tmp_path, monkeypatch)
    store = tj.TrainingJobStore(base_dir=str(tmp_path / "jobs"))
    job = tj.apply_runner_result(
        tj.submit_training_job("s3://d/train.jsonl", store=store, runner=FakeRunner()),
        _valid_result(), store=store,
    )

    version = tj.register_candidate_from_job(job)

    assert version == "v2026.09.18"
    candidate = reg.get_model("rag-retriever", stage="Candidate")
    assert candidate is not None and candidate.version == version
    assert reg.get_model("rag-retriever", stage="Production") is None


def test_candidate_registration_requires_succeeded_job(store):
    runner = FakeRunner()
    job = tj.submit_training_job("s3://d/train.jsonl", store=store, runner=runner)

    with pytest.raises(tj.TrainingJobError, match="SUCCEEDED"):
        tj.register_candidate_from_job(job)


# --- promote / rollback ---------------------------------------------------
def test_promote_then_rollback_is_reversible(tmp_path, monkeypatch):
    """Promotion is explicit and rollback returns to the prior approved version."""
    mr, reg = _fresh_registry(tmp_path, monkeypatch)

    reg.register_model("rag-retriever", "v1", metrics={"retrieval_accuracy": 0.8})
    reg.set_stage("rag-retriever", "v1", "Production")
    reg.register_model("rag-retriever", "v2", metrics={"retrieval_accuracy": 0.9})
    reg.set_stage("rag-retriever", "v2", "Candidate")

    assert reg.get_model("rag-retriever", stage="Production").version == "v1"
    assert reg.promote_model("rag-retriever", "v2", "Production") is True
    assert reg.get_model("rag-retriever", stage="Production").version == "v2"

    assert reg.rollback("rag-retriever", "v1") is True
    assert reg.get_model("rag-retriever", stage="Production").version == "v1"


def test_promote_unknown_version_returns_false(tmp_path):
    import model_registry as mr

    reg = mr.ModelRegistry(str(tmp_path / "registry"))
    assert reg.set_stage("rag-retriever", "nope", "Production") is False
    assert reg.rollback("rag-retriever", "nope") is False


def test_job_json_files_are_plain_json(store):
    """Persistence must stay JSON (no pickle / no executable payloads)."""
    runner = FakeRunner()
    job = tj.submit_training_job("s3://d/train.jsonl", store=store, runner=runner)

    parsed = json.loads(store._path(job.job_id).read_text(encoding="utf-8"))
    assert parsed["job_id"] == job.job_id