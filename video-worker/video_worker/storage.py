"""Storage backends for the video worker.

Interface adapted from MAIA ``src/maia/video/storage.py``; the object store is
Cloudflare R2 (S3-compatible) instead of MinIO, matching the SDC backend's
``STORAGE_PROVIDER=r2`` choice.

Import of ``boto3`` is deferred so offline/dev/tests work without the SDK.
"""
from __future__ import annotations

import shutil
from pathlib import Path
from typing import Protocol
from urllib.parse import quote

from .config import Settings


class StorageError(RuntimeError):
    """Raised when an upload/download/presign operation fails."""


class Storage(Protocol):
    """Minimal object-storage interface used by the worker."""

    def upload(self, local_path: str | Path, key: str) -> str: ...
    def download(self, uri: str, local_path: str | Path) -> Path: ...
    def presign_download(self, key: str, *, expires_sec: int = 900) -> str: ...
    def presign_upload(self, key: str, *, expires_sec: int = 900) -> str: ...
    def delete(self, key: str) -> None: ...
    def list_output_keys(self, job_id: str) -> list[str]: ...


def _bucket_key(uri: str) -> tuple[str | None, str]:
    """Split ``s3://bucket/key`` into (bucket, key); raw key -> (None, key)."""
    if uri.startswith("s3://"):
        rest = uri[len("s3://"):]
        bucket, _, key = rest.partition("/")
        return bucket or None, key
    return None, uri


class LocalStorage:
    """Folder backend rooted at ``VIDEO_STORAGE_DIR`` — dev/test only."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _resolve(self, key: str) -> Path:
        # prevent path traversal: keys are relative names only
        rel = key.lstrip("/").replace("..", "_")
        return self.root / rel

    def upload(self, local_path: str | Path, key: str) -> str:
        src = Path(local_path)
        dst = self._resolve(key)
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.is_dir():
            if dst.exists():
                shutil.rmtree(dst, ignore_errors=True)
            shutil.copytree(src, dst)
        else:
            shutil.copy2(src, dst)
        return str(dst)

    def download(self, uri: str, local_path: str | Path) -> Path:
        if uri.startswith("s3://"):
            raise StorageError("local backend cannot download s3:// uris")
        src = Path(uri) if Path(uri).is_absolute() else self._resolve(uri)
        if not src.exists():
            raise StorageError(f"not found in local storage: {uri}")
        dst = Path(local_path)
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.is_dir():
            shutil.copytree(src, dst, dirs_exist_ok=True)
        else:
            shutil.copy2(src, dst)
        return dst

    def presign_download(self, key: str, *, expires_sec: int = 900) -> str:
        _, rel = _bucket_key(key)
        return f"local://{quote(rel)}"

    def presign_upload(self, key: str, *, expires_sec: int = 900) -> str:
        raise NotImplementedError("local backend does not support presigned upload")

    def delete(self, key: str) -> None:
        target = self._resolve(key)
        if target.is_dir():
            shutil.rmtree(target, ignore_errors=True)
        elif target.exists():
            target.unlink()

    def list_output_keys(self, job_id: str) -> list[str]:
        base = self._resolve(f"outputs/{job_id}")
        if base.is_dir():
            return [str(p) for p in sorted(base.rglob("*")) if p.is_file()]
        return [str(base)] if base.exists() else []


class R2Storage:
    """Cloudflare R2 backend (S3 API via boto3)."""

    def __init__(self, settings: Settings) -> None:
        try:
            import boto3
            from botocore.config import Config as BotoConfig
        except ImportError as exc:  # pragma: no cover - env-specific
            raise StorageError(
                "STORAGE_PROVIDER=r2 requires boto3 (pip install boto3)"
            ) from exc
        self.bucket = settings.r2_bucket_name
        self.client = boto3.client(
            "s3",
            endpoint_url=settings.r2_endpoint_url(),
            aws_access_key_id=settings.r2_access_key_id,
            aws_secret_access_key=settings.r2_secret_access_key,
            region_name="auto",
            config=BotoConfig(signature_version="s3v4"),
        )

    def upload(self, local_path: str | Path, key: str) -> str:
        src = Path(local_path)
        if src.is_dir():
            for f in sorted(src.rglob("*")):
                if f.is_file():
                    self.client.upload_file(str(f), self.bucket, f"{key}/{f.relative_to(src)}")
        else:
            self.client.upload_file(str(src), self.bucket, key)
        return f"s3://{self.bucket}/{key}"

    def download(self, uri: str, local_path: str | Path) -> Path:
        bucket, key = _bucket_key(uri)
        dst = Path(local_path)
        dst.parent.mkdir(parents=True, exist_ok=True)
        self.client.download_file(bucket or self.bucket, key, str(dst))
        return dst

    def presign_download(self, key: str, *, expires_sec: int = 900) -> str:
        bucket, k = _bucket_key(key)
        if bucket is None and k.startswith(f"{self.bucket}/"):
            k = k[len(self.bucket) + 1:]
        return self.client.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket or self.bucket, "Key": k},
            ExpiresIn=expires_sec,
        )

    def presign_upload(self, key: str, *, expires_sec: int = 900) -> str:
        return self.client.generate_presigned_url(
            "put_object",
            Params={"Bucket": self.bucket, "Key": key},
            ExpiresIn=expires_sec,
        )

    def delete(self, key: str) -> None:
        _, k = _bucket_key(key)
        paginator = self.client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=self.bucket, Prefix=k):
            objs = [{"Key": o["Key"]} for o in page.get("Contents", [])]
            if objs:
                self.client.delete_objects(Bucket=self.bucket, Delete={"Objects": objs})

    def list_output_keys(self, job_id: str) -> list[str]:
        prefix = f"outputs/{job_id}"
        keys: list[str] = []
        paginator = self.client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=self.bucket, Prefix=prefix):
            keys.extend(o["Key"] for o in page.get("Contents", []))
        return keys


def build_storage(settings: Settings) -> Storage:
    """Factory honoring ``STORAGE_PROVIDER`` (local default, r2 production)."""
    if settings.storage_provider == "r2":
        return R2Storage(settings)
    return LocalStorage(settings.storage_dir)