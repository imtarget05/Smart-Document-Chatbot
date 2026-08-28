"""Async job queue cho document/agent processing (Phase 4).

- Mặc định: in-memory dict (đủ cho single-instance dev).
- Nếu set REDIS_URL: dùng Redis hash cho job state (multi-instance ready).
"""

from __future__ import annotations

import asyncio
import os
import time
import uuid
from typing import Any, Dict, Optional

REDIS_URL = os.getenv("REDIS_URL", "")
_redis = None
if REDIS_URL:
    try:
        import redis.asyncio as aioredis
        _redis = aioredis.from_url(REDIS_URL, decode_responses=True)
    except Exception:
        _redis = None

JOBS_KEY = "sdc:agent:jobs"
JOB_TTL = 3600  # 1h

# In-memory fallback
_jobs: Dict[str, Dict[str, Any]] = {}


def new_job_id() -> str:
    return uuid.uuid4().hex[:12]


async def create_job(job_type: str, payload: Dict[str, Any]) -> str:
    job_id = new_job_id()
    job = {
        "job_id": job_id,
        "type": job_type,
        "status": "queued",
        "result": None,
        "error": None,
        "created_at": time.time(),
        "updated_at": time.time(),
    }
    if _redis is not None:
        try:
            await _redis.hset(JOBS_KEY, job_id, job_json(job))
            await _redis.expire(JOBS_KEY, JOB_TTL)
            return job_id
        except Exception:
            pass
    _jobs[job_id] = job
    return job_id


def job_json(job: Dict[str, Any]) -> str:
    import json
    return json.dumps(job, ensure_ascii=False)


async def update_job(job_id: str, **fields: Any) -> None:
    job = await get_job(job_id)
    if job is None:
        return
    job.update(fields, updated_at=time.time())
    if _redis is not None:
        try:
            await _redis.hset(JOBS_KEY, job_id, job_json(job))
            return
        except Exception:
            pass
    _jobs[job_id] = job


async def get_job(job_id: str) -> Optional[Dict[str, Any]]:
    if _redis is not None:
        try:
            raw = await _redis.hget(JOBS_KEY, job_id)
            if raw:
                import json
                return json.loads(raw)
        except Exception:
            pass
    return _jobs.get(job_id)


async def run_job(job_id: str, coro_factory) -> None:
    """Chạy job coroutine, tự update status queued -> running -> done/failed."""
    await update_job(job_id, status="running")
    try:
        result = await coro_factory()
        await update_job(job_id, status="done", result=result)
    except Exception as exc:
        await update_job(job_id, status="failed", error=str(exc))


async def wait_for_job(job_id: str, poll_seconds: float = 0.5,
                       timeout: float = 300.0) -> Optional[Dict[str, Any]]:
    """Poll job tới khi done/failed (dùng cho WebSocket stream)."""
    waited = 0.0
    while waited < timeout:
        job = await get_job(job_id)
        if job is None or job.get("status") in ("done", "failed"):
            return job
        await asyncio.sleep(poll_seconds)
        waited += poll_seconds
    return await get_job(job_id)