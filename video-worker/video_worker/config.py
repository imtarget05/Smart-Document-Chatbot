"""Worker configuration (env-driven, no pydantic dependency)."""
from __future__ import annotations

import os
from dataclasses import dataclass, field


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


def _float_env(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except ValueError:
        return default


def _default_database_url() -> str:
    # Same Neon database the Spring backend and agent use. Accept the worker's
    # own override first, then the common SDC names, then a local default.
    return (
        os.getenv("VIDEO_DATABASE_URL")
        or os.getenv("NEON_DATABASE_URL")
        or os.getenv("DATABASE_URL")
        or "postgresql://postgres:postgres@localhost:5432/smart_doc_chatbot"
    )


@dataclass
class Settings:
    """Runtime settings for one worker process."""

    # ── queue ────────────────────────────────────────────────────────────────
    database_url: str = field(default_factory=_default_database_url)
    lease_seconds: int = _int_env("VIDEO_LEASE_SECONDS", 900)
    max_attempts: int = _int_env("VIDEO_MAX_ATTEMPTS", 3)
    base_backoff_seconds: int = _int_env("VIDEO_BASE_BACKOFF_SECONDS", 30)
    poll_interval_sec: float = _float_env("VIDEO_POLL_INTERVAL_SEC", 5.0)
    worker_id: str = os.getenv("VIDEO_WORKER_ID", "")
    concurrency: int = _int_env("VIDEO_CONCURRENCY", 1)

    # ── storage (aligned with the SDC backend env names) ─────────────────────
    storage_provider: str = os.getenv("VIDEO_STORAGE_PROVIDER", os.getenv("STORAGE_PROVIDER", "local"))
    storage_dir: str = os.getenv("VIDEO_STORAGE_DIR", "storage/video")
    r2_account_id: str = os.getenv("R2_ACCOUNT_ID", "")
    r2_access_key_id: str = os.getenv("R2_ACCESS_KEY_ID", "")
    r2_secret_access_key: str = os.getenv("R2_SECRET_ACCESS_KEY", "")
    r2_bucket_name: str = os.getenv("R2_BUCKET_NAME", "smart-doc-video")
    r2_endpoint: str = os.getenv("R2_ENDPOINT", "")
    output_prefix: str = os.getenv("VIDEO_OUTPUT_PREFIX", "outputs")
    input_prefix: str = os.getenv("VIDEO_INPUT_PREFIX", "video-in")

    # ── ffmpeg ───────────────────────────────────────────────────────────────
    encoder_profile: str = os.getenv("VIDEO_ENCODER_PROFILE", "auto")
    ffmpeg_bin: str = os.getenv("VIDEO_FFMPEG_BIN", "ffmpeg")
    ffprobe_bin: str = os.getenv("VIDEO_FFPROBE_BIN", "ffprobe")
    ffmpeg_timeout_sec: float = _float_env("VIDEO_FFMPEG_TIMEOUT_SEC", 3600.0)

    def r2_endpoint_url(self) -> str:
        """Resolve the S3 endpoint for Cloudflare R2."""
        if self.r2_endpoint:
            return self.r2_endpoint
        if self.r2_account_id:
            return f"https://{self.r2_account_id}.r2.cloudflarestorage.com"
        return ""

    def readiness_errors(self) -> list[str]:
        """Fail fast instead of silently degrading in production."""
        problems: list[str] = []
        if not self.database_url:
            problems.append("VIDEO_DATABASE_URL/NEON_DATABASE_URL is required")
        if self.storage_provider == "r2":
            if not self.r2_endpoint_url():
                problems.append("R2_ENDPOINT or R2_ACCOUNT_ID is required for r2 storage")
            if not self.r2_access_key_id or not self.r2_secret_access_key:
                problems.append("R2_ACCESS_KEY_ID/R2_SECRET_ACCESS_KEY are required for r2 storage")
            if not self.r2_bucket_name:
                problems.append("R2_BUCKET_NAME is required for r2 storage")
        elif self.storage_provider != "local":
            problems.append(f"unknown storage provider: {self.storage_provider}")
        return problems


settings = Settings()