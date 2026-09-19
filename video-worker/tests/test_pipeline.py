"""Vendored pipeline/ffmpeg-argument tests (adapted from MAIA tests/test_video.py)."""
from __future__ import annotations

import sys

import pytest

from video_worker.pipeline import (
    PipelineError,
    build_ffmpeg_args,
    compute_idempotency_key,
    probe_metadata,
    run_ffmpeg,
)


def test_transcode_args_scale_and_codec_and_output_last(tmp_path):
    out = str(tmp_path / "out.mp4")
    args = build_ffmpeg_args(
        "in.mp4", out,
        {"job_type": "transcode", "resolution": "720p", "bitrate_kbps": 1200},
        encoder_profile="libx264",
    )
    assert args[-1] == out
    assert "-c:v" in args and "libx264" in args
    assert any("scale=1280:720" in a for a in args)
    assert "1200k" in args
    assert "-c:a" in args and "aac" in args


def test_transcode_scale_forces_even_dimensions(tmp_path):
    # Regression: force_original_aspect_ratio=decrease alone can yield an odd
    # width (1280x720 -> 480p => 853), which libx264 rejects. force_divisible_by
    # must be present so every scaled output stays encodable.
    args = build_ffmpeg_args(
        "in.mp4", str(tmp_path / "o.mp4"),
        {"job_type": "transcode", "resolution": "480p"},
        encoder_profile="libx264",
    )
    scale = next(a for a in args if "scale=" in a)
    assert "force_divisible_by=2" in scale


def test_transcode_without_resolution_has_no_scale_filter(tmp_path):
    args = build_ffmpeg_args(
        "in.mp4", str(tmp_path / "o.mp4"), {"job_type": "transcode"},
        encoder_profile="libx264",
    )
    assert not any("-vf" == a for a in args)


def test_extract_audio_drops_video_and_uses_aac(tmp_path):
    args = build_ffmpeg_args(
        "in.mp4", str(tmp_path / "o.m4a"), {"job_type": "extract_audio"},
        encoder_profile="libx264",
    )
    assert "-vn" in args
    assert "aac" in args
    assert args[-1].endswith("o.m4a")


def test_remux_stream_copies(tmp_path):
    args = build_ffmpeg_args(
        "in.mp4", str(tmp_path / "o.mkv"), {"job_type": "remux"},
        encoder_profile="libx264",
    )
    assert "copy" in args
    assert "-c:v" not in args


def test_hls_vod_writes_playlist_and_not_a_trailing_output(tmp_path):
    args = build_ffmpeg_args(
        "in.mp4", str(tmp_path / "hls"), {"job_type": "hls_vod"},
        encoder_profile="libx264",
    )
    assert "-hls_playlist_type" in args and "vod" in args
    assert "seg_%04d.ts" in " ".join(args)
    assert args[-1].endswith("index.m3u8")


def test_compute_idempotency_key_is_stable_and_order_independent():
    preset = {"job_type": "transcode", "resolution": "720p"}
    reordered = {"resolution": "720p", "job_type": "transcode"}
    assert compute_idempotency_key("sha-1", preset) == compute_idempotency_key("sha-1", reordered)
    assert compute_idempotency_key("sha-1", preset) != compute_idempotency_key("sha-2", preset)


def test_run_ffmpeg_success_and_failure():
    assert run_ffmpeg([sys.executable, "-c", "print('ok')"], timeout_sec=30)
    with pytest.raises(PipelineError):
        run_ffmpeg([sys.executable, "-c", "import sys; sys.exit(3)"], timeout_sec=30)


def test_run_ffmpeg_missing_binary_raises_pipeline_error():
    with pytest.raises(PipelineError):
        run_ffmpeg(["definitely-not-a-binary-xyz"], timeout_sec=5)


def test_probe_metadata_on_non_media_returns_empty(tmp_path):
    junk = tmp_path / "not_media.txt"
    junk.write_text("hello")
    assert probe_metadata(str(junk)) == {}