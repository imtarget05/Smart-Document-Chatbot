"""Real-ffmpeg end-to-end: the worker must actually produce a playable video.

This is the SDC-side counterpart of MAIA's
``tests/test_video.py::test_real_ffmpeg_transcode_end_to_end``: it synthesizes a
real source clip, runs the worker's claim -> download -> ffmpeg -> upload path,
and ffprobes the artifact the worker uploaded. Skipped only when ffmpeg is
absent.
"""
from __future__ import annotations

import shutil
import subprocess

import pytest

from video_worker.config import Settings
from video_worker.pipeline import probe_metadata
from video_worker.storage import LocalStorage
from video_worker.store import STATUS_COMPLETED, InMemoryJobStore, JobRecord
from video_worker.worker import VideoWorker

FFMPEG = shutil.which("ffmpeg")
requires_ffmpeg = pytest.mark.skipif(FFMPEG is None, reason="ffmpeg not installed")


def _synth_source(path) -> None:
    subprocess.run(
        [
            FFMPEG, "-hide_banner", "-loglevel", "error", "-y",
            "-f", "lavfi", "-i", "testsrc=duration=1:size=1280x720:rate=24",
            "-f", "lavfi", "-i", "sine=duration=1",
            "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-shortest", str(path),
        ],
        check=True,
        capture_output=True,
    )


def _settings(tmp_path) -> Settings:
    return Settings(
        database_url="",
        storage_provider="local",
        storage_dir=str(tmp_path / "storage"),
        encoder_profile="libx264",
        max_attempts=2,
        lease_seconds=120,
    )


@requires_ffmpeg
def test_worker_transcodes_real_video_end_to_end(tmp_path):
    settings = _settings(tmp_path)
    storage = LocalStorage(settings.storage_dir)

    src = storage.root / "video-in" / "real_in.mp4"
    src.parent.mkdir(parents=True, exist_ok=True)
    _synth_source(src)

    store = InMemoryJobStore()
    record = store.add(JobRecord(
        id=0, owner_username="alice", source_hash="sha-real", job_type="TRANSCODE",
        source_key="video-in/real_in.mp4",
        preset='{"job_type": "transcode", "resolution": "480p"}',
    ))

    worker = VideoWorker(settings, store, storage, worker_id="w-real")
    assert worker.step() is True
    assert record.status == STATUS_COMPLETED, record.last_error

    out = storage.root / record.output_key
    assert out.exists() and out.stat().st_size > 0
    meta = probe_metadata(str(out))
    # 1280x720 -> 480p must be 854x480 (even), never the odd 853x480 that
    # libx264 rejects — this is the regression the fix guards.
    assert meta.get("width") == 854 and meta.get("height") == 480
    assert meta.get("codec") == "h264"
    assert meta.get("duration_sec") == 1.0


@requires_ffmpeg
def test_worker_extracts_real_audio_end_to_end(tmp_path):
    settings = _settings(tmp_path)
    storage = LocalStorage(settings.storage_dir)

    src = storage.root / "video-in" / "real_in.mp4"
    src.parent.mkdir(parents=True, exist_ok=True)
    _synth_source(src)

    store = InMemoryJobStore()
    record = store.add(JobRecord(
        id=0, owner_username="alice", source_hash="sha-audio", job_type="EXTRACT_AUDIO",
        source_key="video-in/real_in.mp4", preset='{"job_type": "extract_audio"}',
    ))
    worker = VideoWorker(settings, store, storage, worker_id="w-audio")

    assert worker.step() is True
    assert record.status == STATUS_COMPLETED, record.last_error
    out = storage.root / record.output_key
    assert out.exists() and out.suffix == ".m4a" and out.stat().st_size > 0