"""Worker behaviour tests with a fake ffmpeg (offline, no external services).

Covers the queue state machine the worker depends on: complete on success,
exponential-backoff retry then DEAD after max attempts, expired-lease recovery,
and that a stale lease token can never overwrite a newer owner's result.
"""
from __future__ import annotations

from datetime import timedelta

from video_worker import worker as worker_module
from video_worker.config import Settings
from video_worker.pipeline import PipelineError
from video_worker.storage import LocalStorage
from video_worker.store import (
    STATUS_COMPLETED,
    STATUS_DEAD,
    STATUS_PENDING,
    STATUS_RUNNING,
    InMemoryJobStore,
    JobRecord,
    _utcnow,
)
from video_worker.worker import VideoWorker


def _settings(tmp_path, **overrides) -> Settings:
    base = dict(
        database_url="",
        storage_provider="local",
        storage_dir=str(tmp_path / "storage"),
        encoder_profile="libx264",
        max_attempts=2,
        base_backoff_seconds=1,
        lease_seconds=60,
    )
    base.update(overrides)
    return Settings(**base)


def _enqueue_real_source(store: InMemoryJobStore, storage: LocalStorage) -> JobRecord:
    src = storage.root / "video-in" / "src.mp4"
    src.parent.mkdir(parents=True, exist_ok=True)
    src.write_bytes(b"fake-source-bytes")
    return store.add(JobRecord(
        id=0, owner_username="alice", source_hash="sha-1", job_type="TRANSCODE",
        source_key="video-in/src.mp4", preset='{"job_type": "transcode", "resolution": "480p"}',
    ))


def test_step_completes_job_and_records_output(tmp_path, monkeypatch):
    settings = _settings(tmp_path)
    store = InMemoryJobStore()
    storage = LocalStorage(settings.storage_dir)
    record = _enqueue_real_source(store, storage)

    def fake_run(args, *, timeout_sec=0):
        with open(args[-1], "wb") as fh:
            fh.write(b"encoded-output")
        return args

    monkeypatch.setattr(worker_module, "run_ffmpeg", fake_run)
    worker = VideoWorker(settings, store, storage, worker_id="w1")

    assert worker.step() is True
    assert record.status == STATUS_COMPLETED
    assert record.output_key is not None and "outputs/" in record.output_key
    assert record.metadata_json and "output" in record.metadata_json
    assert record.lease_token is None
    assert (storage.root / record.output_key).exists()


def test_step_returns_false_when_queue_empty(tmp_path):
    settings = _settings(tmp_path)
    worker = VideoWorker(settings, InMemoryJobStore(), LocalStorage(settings.storage_dir))
    assert worker.step() is False


def test_failure_retries_with_backoff_then_goes_dead(tmp_path, monkeypatch):
    settings = _settings(tmp_path)
    store = InMemoryJobStore()
    storage = LocalStorage(settings.storage_dir)
    record = _enqueue_real_source(store, storage)

    def boom(args, *, timeout_sec=0):
        raise PipelineError("ffmpeg exited 1: boom")

    monkeypatch.setattr(worker_module, "run_ffmpeg", boom)
    worker = VideoWorker(settings, store, storage, worker_id="w1")

    assert worker.step() is True
    assert record.status == STATUS_PENDING
    assert record.attempts == 1
    assert record.next_run_at > _utcnow()
    assert "boom" in (record.last_error or "")

    record.next_run_at = _utcnow() - timedelta(seconds=1)
    assert worker.step() is True
    assert record.status == STATUS_DEAD
    assert record.attempts == 2


def test_missing_source_key_fails_the_job(tmp_path):
    settings = _settings(tmp_path)
    store = InMemoryJobStore()
    storage = LocalStorage(settings.storage_dir)
    record = store.add(JobRecord(
        id=0, owner_username="alice", source_hash="sha-1", job_type="TRANSCODE",
        source_key=None,
    ))
    worker = VideoWorker(settings, store, storage, worker_id="w1")

    assert worker.step() is True
    assert record.status == STATUS_PENDING  # retry, not silent success
    assert "source_key" in (record.last_error or "")


def test_stale_lease_token_cannot_complete_a_newer_owners_job(tmp_path):
    settings = _settings(tmp_path)
    store = InMemoryJobStore()
    storage = LocalStorage(settings.storage_dir)
    record = _enqueue_real_source(store, storage)

    first = store.claim("w1", lease_seconds=1)
    assert first is not None
    record.lease_expires_at = _utcnow() - timedelta(seconds=1)
    assert store.requeue_expired() == 1
    second = store.claim("w2", lease_seconds=60)
    assert second is not None and second.lease_token != first.lease_token

    # the resurrected first worker must NOT be able to commit
    assert store.complete(first.id, first.lease_token, output_key="stale", metadata={}) is False
    assert store.complete(second.id, second.lease_token, output_key="fresh", metadata={}) is True
    assert record.output_key == "fresh"
    assert record.status == STATUS_COMPLETED


def test_requeue_expired_only_touches_expired_running_rows(tmp_path):
    settings = _settings(tmp_path)
    store = InMemoryJobStore()
    storage = LocalStorage(settings.storage_dir)
    expired = _enqueue_real_source(store, storage)
    live = store.add(JobRecord(
        id=0, owner_username="bob", source_hash="sha-2", job_type="TRANSCODE",
        source_key="video-in/src.mp4",
    ))

    store.claim("w1", lease_seconds=1)
    expired.lease_expires_at = _utcnow() - timedelta(seconds=1)
    store.claim("w2", lease_seconds=600)  # keeps its lease

    assert store.requeue_expired() == 1
    assert expired.status == STATUS_PENDING
    assert live.status == STATUS_RUNNING


def test_readiness_rejects_r2_without_credentials(tmp_path):
    settings = _settings(tmp_path, storage_provider="r2")
    problems = settings.readiness_errors()
    assert any("R2_" in p for p in problems)


def test_backoff_is_exponential():
    from video_worker.store import backoff_seconds

    assert backoff_seconds(1, 30) == 30
    assert backoff_seconds(2, 30) == 120
    assert backoff_seconds(3, 30) == 480