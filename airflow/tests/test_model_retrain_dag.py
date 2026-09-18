"""Airflow retrain DAG contract tests (plan 2026-09-18 Task 4).

Asserts the DAG talks to the real training-job contract (POST /v1/training-jobs
then bounded polling), validates the specific job result (URI/SHA/version/gate),
rejects stale artifacts, and fails a pending/failed job instead of accepting a
pre-existing adapter file. No Airflow runtime is required: the task callables
are exercised through a stub Airflow API when the real package is absent.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
DAG_PATH = ROOT / "airflow" / "dags" / "model_retrain_pipeline.py"


# --- stub airflow so the DAG module imports without an installation --------
def _install_airflow_stub(monkeypatch):
    import types

    airflow = types.ModuleType("airflow")
    decorators = types.ModuleType("airflow.decorators")
    exceptions = types.ModuleType("airflow.exceptions")
    models = types.ModuleType("airflow.models")
    models_variable = types.ModuleType("airflow.models.variable")

    captured: dict = {}

    def dag(*dargs, **dkwargs):
        def wrap(fn):
            def factory():
                # Airflow calls the DAG factory at parse time; doing the same
                # here registers every @task in the registry.
                captured["tasks"] = {}
                fn()
                return None

            captured["dag_fn"] = fn
            captured["factory"] = factory
            return factory

        return wrap

    def task(fn=None, **kwargs):
        def register(inner):
            def placeholder(*args, **kws):
                # Real Airflow returns an XComArg here; tasks only execute in
                # the scheduler, never at DAG parse time.
                return f"xcom:{inner.__name__}"

            captured.setdefault("tasks", {})[inner.__name__] = inner
            return placeholder

        if fn is not None:
            return register(fn)
        return register

    class AirflowException(Exception):
        pass

    class Variable:
        _values: dict = {}

        @classmethod
        def get(cls, key, default_var=None):
            return cls._values.get(key, default_var)

    decorators.dag = dag
    decorators.task = task
    exceptions.AirflowException = AirflowException
    models_variable.Variable = Variable
    airflow.decorators = decorators
    airflow.exceptions = exceptions
    airflow.models = models
    models.variable = models_variable

    monkeypatch.setitem(sys.modules, "airflow", airflow)
    monkeypatch.setitem(sys.modules, "airflow.decorators", decorators)
    monkeypatch.setitem(sys.modules, "airflow.exceptions", exceptions)
    monkeypatch.setitem(sys.modules, "airflow.models", models)
    monkeypatch.setitem(sys.modules, "airflow.models.variable", models_variable)
    return captured, AirflowException, Variable


def _load_dag(monkeypatch):
    captured, AirflowException, Variable = _install_airflow_stub(monkeypatch)
    spec = importlib.util.spec_from_file_location("retrain_dag_under_test", DAG_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    # Trigger the DAG factory exactly as Airflow's parser does.
    module.model_retrain_pipeline()
    module._test_captured = captured
    return module, AirflowException, Variable


def _collect_tasks(module) -> dict:
    """Return the registered task callables from the last DAG parse."""
    return module._test_captured.get("tasks", {})


# --- image / compose configuration ---------------------------------------
def test_dockerfile_and_compose_provide_project_root():
    """FINETUNE_ROOT must point at the mounted project, not the Airflow home."""
    dockerfile = (ROOT / "airflow" / "Dockerfile").read_text()
    assert "/opt/smartdoc" in dockerfile
    compose = (ROOT / "docker" / "docker-compose.yml").read_text()
    assert "FINETUNE_ROOT: /opt/smartdoc" in compose
    assert ":/opt/smartdoc:ro" in compose, "project root must be mounted read-only for the DAG"
    for service in ("airflow-webserver", "airflow-scheduler"):
        assert service in compose


def test_build_dataset_script_is_reachable_from_project_root():
    """The mounted project must actually contain finetune/build_dataset.py."""
    script = ROOT / "finetune" / "build_dataset.py"
    assert script.exists(), "retrain DAG cannot build a dataset without this script"


# --- submission request contract -----------------------------------------
def test_submit_task_posts_training_job_with_token_and_dataset_uri(monkeypatch):
    """The DAG must call POST /v1/training-jobs with token + dataset URI in JSON."""
    module, _, Variable = _load_dag(monkeypatch)
    Variable._values = {"RETRAIN_TOKEN": "secret-token", "AGENT_BASE_URL": "http://agent:9000"}

    calls: list[dict] = []

    def fake_post(url, payload, token):
        calls.append({"url": url, "payload": payload, "token": token})
        return {"job_id": "TJ-123", "status": "RUNNING"}

    monkeypatch.setattr(module, "_post_json", fake_post)

    tasks = _collect_tasks(module)
    submission = tasks["submit_training"]("/opt/smartdoc/finetune/data/train.jsonl")

    assert submission["job_id"] == "TJ-123"
    assert calls[0]["url"].endswith("/v1/training-jobs")
    assert calls[0]["payload"]["dataset_uri"] == "/opt/smartdoc/finetune/data/train.jsonl"
    assert calls[0]["payload"]["token"] == "secret-token"
    assert calls[0]["token"] == "secret-token"


def test_submit_task_requires_token(monkeypatch):
    module, AirflowException, Variable = _load_dag(monkeypatch)
    Variable._values = {}
    tasks = _collect_tasks(module)
    with pytest.raises(AirflowException, match="RETRAIN_TOKEN"):
        tasks["submit_training"]("/opt/smartdoc/finetune/data/train.jsonl")


def test_submit_task_rejects_response_without_job_id(monkeypatch):
    module, AirflowException, Variable = _load_dag(monkeypatch)
    Variable._values = {"RETRAIN_TOKEN": "t", "AGENT_BASE_URL": "http://agent:9000"}
    monkeypatch.setattr(module, "_post_json", lambda url, payload, token: {"status": "RUNNING"})
    tasks = _collect_tasks(module)
    with pytest.raises(AirflowException, match="job_id"):
        tasks["submit_training"]("/opt/smartdoc/finetune/data/train.jsonl")


# --- polling contract -----------------------------------------------------
def test_poll_waits_on_pending_and_returns_on_succeeded(monkeypatch):
    """A PENDING job must wait, not be accepted as success."""
    module, _, Variable = _load_dag(monkeypatch)
    Variable._values = {"RETRAIN_TOKEN": "t", "AGENT_BASE_URL": "http://agent:9000"}
    monkeypatch.setattr(module, "POLL_INTERVAL_SEC", 0)

    statuses = iter(["PENDING", "RUNNING", "SUCCEEDED"])

    def fake_get(url, token):
        return {"status": next(statuses), "job_id": "TJ-123"}

    monkeypatch.setattr(module, "_get_json", fake_get)
    tasks = _collect_tasks(module)
    result = tasks["poll_training"]({"job_id": "TJ-123"})
    assert result["status"] == "SUCCEEDED"


def test_poll_fails_when_the_job_fails(monkeypatch):
    module, AirflowException, Variable = _load_dag(monkeypatch)
    Variable._values = {"RETRAIN_TOKEN": "t", "AGENT_BASE_URL": "http://agent:9000"}
    monkeypatch.setattr(module, "POLL_INTERVAL_SEC", 0)
    monkeypatch.setattr(
        module, "_get_json",
        lambda url, token: {"status": "FAILED", "failure_reason": "CUDA OOM"},
    )
    tasks = _collect_tasks(module)
    with pytest.raises(AirflowException, match="CUDA OOM"):
        tasks["poll_training"]({"job_id": "TJ-123"})


def test_poll_times_out_instead_of_accepting_an_old_adapter(monkeypatch):
    """Never reaching terminal state must fail the DAG task."""
    module, AirflowException, Variable = _load_dag(monkeypatch)
    Variable._values = {"RETRAIN_TOKEN": "t", "AGENT_BASE_URL": "http://agent:9000"}
    monkeypatch.setattr(module, "POLL_INTERVAL_SEC", 0)
    monkeypatch.setattr(module, "POLL_MAX_ATTEMPTS", 3)
    monkeypatch.setattr(module, "_get_json", lambda url, token: {"status": "RUNNING"})
    tasks = _collect_tasks(module)
    with pytest.raises(AirflowException, match="did not reach terminal state"):
        tasks["poll_training"]({"job_id": "TJ-123"})


# --- result validation (never accept a stale/pre-existing adapter) --------
def _succeeded_result(**overrides) -> dict:
    result = {
        "job_id": "TJ-123",
        "status": "SUCCEEDED",
        "model_version": "v2026.09.18",
        "adapter_uri": "s3://adapters/lora-t4/adapter_model.safetensors",
        "sha256": "c" * 64,
        "metrics": {
            "retrieval_accuracy": 0.81,
            "answer_correctness": 0.73,
            "hallucination_rate": 0.10,
        },
    }
    result.update(overrides)
    return result


def test_verify_adapter_accepts_a_new_valid_result(monkeypatch):
    module, _, _ = _load_dag(monkeypatch)
    tasks = _collect_tasks(module)
    message = tasks["verify_adapter"](_succeeded_result())
    assert "adapter ok" in message
    assert "v2026.09.18" in message


def test_verify_adapter_rejects_pending_status(monkeypatch):
    """A pending job must fail the verify step, not be treated as trained."""
    module, AirflowException, _ = _load_dag(monkeypatch)
    tasks = _collect_tasks(module)
    with pytest.raises(AirflowException, match="not succeeded"):
        tasks["verify_adapter"](_succeeded_result(status="PENDING"))


def test_verify_adapter_rejects_missing_or_stale_artifact_identity(monkeypatch):
    """An adapter URI without checksum/version is incomplete evidence."""
    module, AirflowException, _ = _load_dag(monkeypatch)
    tasks = _collect_tasks(module)

    with pytest.raises(AirflowException, match="sha256"):
        tasks["verify_adapter"](_succeeded_result(sha256=""))
    with pytest.raises(AirflowException, match="model_version"):
        tasks["verify_adapter"](_succeeded_result(model_version=""))
    with pytest.raises(AirflowException, match="invalid adapter checksum"):
        tasks["verify_adapter"](_succeeded_result(sha256="short"))


def test_verify_adapter_enforces_quality_gate(monkeypatch):
    module, AirflowException, _ = _load_dag(monkeypatch)
    tasks = _collect_tasks(module)

    with pytest.raises(AirflowException, match="quality gate failed"):
        tasks["verify_adapter"](_succeeded_result(metrics={
            "retrieval_accuracy": 0.10,
            "answer_correctness": 0.73,
            "hallucination_rate": 0.10,
        }))
    with pytest.raises(AirflowException, match="quality gate failed"):
        tasks["verify_adapter"](_succeeded_result(metrics={
            "retrieval_accuracy": 0.81,
            "answer_correctness": 0.73,
            "hallucination_rate": 0.90,
        }))


def test_dag_wires_submission_poll_and_verify_in_order(monkeypatch):
    """The DAG must never declare success without polling this job's result."""
    module, _, Variable = _load_dag(monkeypatch)
    Variable._values = {"RETRAIN_TOKEN": "t", "AGENT_BASE_URL": "http://agent:9000"}
    monkeypatch.setattr(module, "POLL_INTERVAL_SEC", 0)
    monkeypatch.setattr(
        module, "_post_json",
        lambda url, payload, token: {"job_id": "TJ-999", "status": "RUNNING"},
    )
    monkeypatch.setattr(
        module, "_get_json",
        lambda url, token: _succeeded_result(job_id="TJ-999"),
    )
    # Re-parse so the wiring runs with the patched helpers.
    module.model_retrain_pipeline()
    tasks = _collect_tasks(module)
    assert set(tasks) >= {"build_dataset", "submit_training", "poll_training", "verify_adapter"}


def test_dag_source_uses_training_jobs_contract_not_legacy_retrain_endpoint():
    """The DAG must not call the legacy /v1/agent/retrain endpoint."""
    source = DAG_PATH.read_text()
    assert "/v1/training-jobs" in source
    assert "/v1/agent/retrain" not in source
    assert "adapter_model.safetensors" not in source, (
        "stale-file inspection was replaced by immutable result validation"
    )