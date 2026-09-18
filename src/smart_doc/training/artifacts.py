"""Remote artifact uploader for Smart-Doc training jobs.

Primary backend is S3 via boto3; bucket comes from the ARTIFACT_BUCKET
env var. Explicit local-cache fallback (file:// URL) when boto3 is
unavailable or the S3 upload fails (e.g. no credentials).
"""

import os


def upload_artifact(data: bytes, key: str) -> str:
    """Upload training artifact bytes to remote storage.

    Returns an ``s3://{bucket}/{key}`` URL on success, or an explicit
    ``file://`` local-cache path when S3 is unavailable.
    """
    bucket = os.getenv("ARTIFACT_BUCKET", "default-bucket")
    key = key.lstrip("/")
    try:
        import boto3

        s3 = boto3.client("s3")
        s3.put_object(Bucket=bucket, Key=key, Body=data)
        return f"s3://{bucket}/{key}"
    except Exception:
        # EXPLICIT FALLBACK: no boto3 / no credentials / upload failed.
        # Local cache so training jobs never depend on local-only storage
        # silently; the file:// scheme marks the result as non-remote.
        cache_dir = os.getenv("ARTIFACT_LOCAL_CACHE", "/tmp/smart-doc-artifacts")
        os.makedirs(cache_dir, exist_ok=True)
        safe_key = key.replace("/", "_")
        path = os.path.join(cache_dir, safe_key)
        body = data if isinstance(data, (bytes, bytearray)) else str(data).encode()
        with open(path, "wb") as f:
            f.write(body)
        return f"file://{path}"
