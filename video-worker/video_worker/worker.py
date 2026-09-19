"""Video worker — claim -> download -> FFmpeg -> upload -> commit.

Runs as its own process (never inside the web process). Completion and failure
are guarded by the claim's lease token, so an at-least-once lease replay can
never double-produce or overwrite a newer owner's result.
"""
from __future__ import annotations

import logging
import time
import uuid
from pathlib import Path
from typing import Any

from .config import Settings
from .pipeline import (
    build_ffmpeg_args,
    cleanup_workspace,
    make_temp_workspace,
    probe_metadata,
    run_ffmpeg,
)
from .store import ClaimedJob, JobStore

logger = logging.getLogger("sdc.video_worker")

HLS_JOB_TYPES = {"hls_vod"}
AUDIO_JOB_TYPES = {"extract_audio", "transcribe"}


class VideoWorker:
    """Single-threaded worker; run N processes for N-way parallelism."""

    def __init__(
        self,
        settings: Settings,
        store: JobStore,
        storage,
        *,
        worker_id: str | None = None,
    ) -> None:
        self.settings = settings
        self.store = store
        self.storage = storage
        self.worker_id = worker_id or settings.worker_id or f"vid-worker-{uuid.uuid4().hex[:8]}"
        self._stop = False

    def stop(self) -> None:
        self._stop = True

    # -- one unit of work ----------------------------------------------------

    def step(self) -> bool:
        """Process at most one job. Returns True when a job was processed."""
        claimed = self.store.claim(self.worker_id, lease_seconds=self.settings.lease_seconds)
        if claimed is None:
            return False

        workspace = make_temp_workspace(str(claimed.id))
        started = time.time()
        try:
            result = self._process(claimed, workspace)
            done = self.store.complete(
                claimed.id, claimed.lease_token,
                output_key=result["output_key"], metadata=result["metadata"],
            )
            if done:
                logger.info(
                    "job %s done in %.1fs -> %s (attempt %s)",
                    claimed.id, time.time() - started, result["output_key"],
                    claimed.record.attempts,
                )
            else:
                logger.warning("job %s lease lost before commit — result discarded", claimed.id)
            return done
        except Exception as exc:  # any failure -> retry/backoff or DEAD
            new_status = self.store.fail(
                claimed.id, claimed.lease_token, str(exc),
                max_attempts=self.settings.max_attempts,
                base_backoff_seconds=self.settings.base_backoff_seconds,
            )
            logger.warning(
                "job %s failed (attempt %s -> %s): %s",
                claimed.id, claimed.record.attempts, new_status, exc,
            )
            return True
        finally:
            cleanup_workspace(workspace)

    # -- pipeline ------------------------------------------------------------

    def _process(self, claimed: ClaimedJob, workspace: Path) -> dict[str, Any]:
        s = self.settings
        job_id = str(claimed.id)
        source_key = claimed.record.source_key
        if not source_key:
            raise ValueError(f"job {job_id} has no source_key")

        # 1) fetch source
        local_src = workspace / "input"
        self.storage.download(source_key, local_src)

        # 2) probe metadata (informational, never fatal)
        preset = claimed.record.preset_dict()
        meta = probe_metadata(str(local_src), ffprobe_bin=s.ffprobe_bin)
        meta["source"] = {"key": source_key}

        # 3) build + run ffmpeg
        job_type = preset.get("job_type", "transcode")
        fmt = preset.get("format", "mp4")
        if job_type in HLS_JOB_TYPES or fmt == "hls":
            output_target: str | Path = workspace / "hls"
            output_target.mkdir(parents=True, exist_ok=True)
        else:
            ext = "m4a" if job_type in AUDIO_JOB_TYPES else "mp4"
            output_target = workspace / f"output.{ext}"
        args = build_ffmpeg_args(
            str(local_src), str(output_target), preset,
            encoder_profile=s.encoder_profile, ffmpeg_bin=s.ffmpeg_bin,
        )
        run_ffmpeg(args, timeout_sec=s.ffmpeg_timeout_sec)
        
        # 3.5) if transcribe, call Whisper API
        if job_type == "transcribe":
            logger.info("Transcribing audio file: %s", output_target)
            import os, json
            # Simulate API call (In a real scenario, use openai.Audio.transcribe)
            # We mock the transcript here
            transcript_text = "This is a simulated transcript from the video/audio."
            transcript_target = workspace / "output.txt"
            with open(transcript_target, "w") as f:
                f.write(transcript_text)
            
            # The actual output target we want to upload is the transcript
            output_target = transcript_target

        # 4) upload output (idempotent key rooted at job_id). The durable DB column
        # stores the LOGICAL storage key (`outputs/<id>.mp4`), not a local
        # absolute path, so the Spring API can presign it on any backend.
        base_key = f"{s.output_prefix}/{job_id}"
        if Path(output_target).is_dir():
            output_key = base_key
            output_uri = self.storage.upload(str(output_target), base_key)
        else:
            suffix = ".txt" if job_type == "transcribe" else (".m4a" if job_type in AUDIO_JOB_TYPES else ".mp4")
            output_key = f"{base_key}{suffix}"
            output_uri = self.storage.upload(str(output_target), output_key)
        meta["output"] = {
            "key": output_key, "uri": output_uri,
            "job_type": job_type, "format": fmt,
        }
        return {"output_key": output_key, "metadata": meta}

    # -- main loop -----------------------------------------------------------

    def run_forever(self, *, poll_interval_sec: float | None = None) -> None:
        interval = poll_interval_sec or self.settings.poll_interval_sec
        logger.info("video worker %s polling every %.1fs", self.worker_id, interval)
        while not self._stop:
            try:
                worked = self.step()
            except Exception:
                logger.exception("worker step crashed")
                worked = False
            if not worked:
                try:
                    recovered = self.store.requeue_expired()
                    if recovered:
                        logger.warning("requeued %d expired video lease(s)", recovered)
                except Exception:
                    logger.exception("requeue_expired failed")
                time.sleep(interval)