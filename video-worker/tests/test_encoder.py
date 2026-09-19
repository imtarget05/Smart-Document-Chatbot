"""Vendored encoder-resolution tests (adapted from MAIA tests/test_video.py)."""
from __future__ import annotations

from video_worker.encoder import (
    ffmpeg_available,
    probe_auto_profile,
    resolve_encoder,
)


def test_libx264_profile_is_cpu_and_always_available():
    enc = resolve_encoder("libx264", codec="h264")
    assert enc["profile"] == "libx264"
    assert enc["encoder"] == "libx264"
    assert "-c:v" in enc["video_args"]
    assert enc["hwaccel"] == []


def test_h265_selects_libx265_on_cpu_profile():
    enc = resolve_encoder("libx264", codec="h265")
    assert enc["encoder"] == "libx265"


def test_unknown_profile_degrades_to_libx264():
    enc = resolve_encoder("not-a-real-profile", codec="h264")
    assert enc["profile"] == "libx264"
    assert enc["encoder"] == "libx264"


def test_auto_profile_resolves_to_a_known_profile():
    enc = resolve_encoder("auto", codec="h264")
    assert enc["profile"] in {"videotoolbox", "nvenc", "libx264"}
    # Whatever it resolves to, the encoder must be emitted in the video args.
    assert enc["encoder"] in enc["video_args"]


def test_requested_hw_encoder_missing_falls_back_to_cpu(monkeypatch):
    # Simulate a Linux container without h264_videotoolbox/nvenc available.
    monkeypatch.setattr(
        "video_worker.encoder._available_encoders", lambda ffmpeg_bin: {"libx264"}
    )
    enc = resolve_encoder("videotoolbox", codec="h264")
    assert enc["profile"] == "libx264"
    assert enc["encoder"] == "libx264"


def test_ffmpeg_binary_is_present_in_this_environment():
    assert ffmpeg_available("ffmpeg") is True


def test_probe_auto_profile_is_stable_across_calls():
    assert probe_auto_profile() == probe_auto_profile()