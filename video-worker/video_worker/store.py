"""Durable job store for the video queue (V19/V20, ADR-004 pattern).

Claim / complete / fail are guarded by a per-claim ``lease_token`` so a worker
whose lease expired can never overwrite the result produced by the worker that
currently owns the row.

``PostgresJobStore`` is the production implementation (same Neon database as the
Spring backend); ``InMemoryJobStore`` mirrors the exact semantics for tests.
"""
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Protocol

STATUS_PENDING = "PENDING"
STATUS_RUNNING = "RUNNING"
STATUS_COMPLETED = "COMPLETED"
STATUS_DEAD = "DEAD"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def backoff_seconds(attempts: int, base_seconds: int) -> int:
    """Exponential backoff (ADR-004 style: 30s -> 2m -> 8m with base 30)."""
    attempt = max(attempts, 1)
    return base_seconds * (4 ** (attempt - 1))


@dataclass
class JobRecord:
    """One video_jobs row."""

    id: int
    owner_username: str
    source_hash: str
    job_type: str
    status: str = STATUS_PENDING
    attempts: int = 0
    max_attempts: int = 3
    next_run_at: datetime | None = None
    lease_expires_at: datetime | None = None
    source_key: str | None = None
    output_key: str | None = None
    preset: str | None = None
    metadata_json: str | None = None
    payload: str | None = None
    last_error: str | None = None
    lease_token: str | None = None
    worker_id: str | None = None

    def preset_dict(self) -> dict[str, Any]:
        if not self.preset:
            return {}
        try:
            loaded = json.loads(self.preset)
        except (TypeError, ValueError):
            return {}
        return loaded if isinstance(loaded, dict) else {}


@dataclass
class ClaimedJob:
    """A job handed to the executor, with its lease token for completion."""

    record: JobRecord
    lease_token: str
    worker_id: str = ""

    @property
    def id(self) -> int:
        return self.record.id


class JobStore(Protocol):
    def claim(self, worker_id: str, *, lease_seconds: int) -> ClaimedJob | None: ...
    def complete(self, job_id: int, lease_token: str, *, output_key: str,
                 metadata: dict[str, Any]) -> bool: ...
    def fail(self, job_id: int, lease_token: str, error: str, *,
             max_attempts: int, base_backoff_seconds: int) -> str: ...
    def requeue_expired(self) -> int: ...
    def available(self) -> bool: ...


_COLUMNS = (
    "id, owner_username, source_hash, job_type, status, attempts, max_attempts, "
    "next_run_at, lease_expires_at, source_key, output_key, preset, metadata_json, "
    "payload, last_error, lease_token, worker_id"
)

# Explicitly qualified: the claim CTE also exposes ``id``, so unqualified
# RETURNING columns would be ambiguous on real PostgreSQL.
_RETURNING_V = ", ".join(f"v.{c.strip()}" for c in _COLUMNS.split(","))


class PostgresJobStore:
    """Production store against the shared Neon/Postgres ``video_jobs`` table."""

    def __init__(self, dsn: str) -> None:
        self.dsn = dsn

    def _connect(self):
        import psycopg
        from psycopg.rows import dict_row

        return psycopg.connect(self.dsn, row_factory=dict_row)

    @staticmethod
    def _record(row: dict[str, Any]) -> JobRecord:
        return JobRecord(
            id=row["id"], owner_username=row["owner_username"],
            source_hash=row["source_hash"], job_type=row["job_type"],
            status=row["status"], attempts=row["attempts"],
            max_attempts=row["max_attempts"], next_run_at=row["next_run_at"],
            lease_expires_at=row["lease_expires_at"], source_key=row["source_key"],
            output_key=row["output_key"], preset=row["preset"],
            metadata_json=row["metadata_json"], payload=row["payload"],
            last_error=row["last_error"], lease_token=row["lease_token"],
            worker_id=row["worker_id"],
        )

    def claim(self, worker_id: str, *, lease_seconds: int) -> ClaimedJob | None:
        token = uuid.uuid4().hex
        sql = f"""
            WITH claimed AS (
                SELECT id FROM video_jobs
                WHERE status = 'PENDING' AND next_run_at <= now()
                ORDER BY next_run_at, id
                FOR UPDATE SKIP LOCKED
                LIMIT 1
            )
            UPDATE video_jobs v
               SET status = 'RUNNING',
                   attempts = attempts + 1,
                   lease_expires_at = now() + make_interval(secs => %(lease)s),
                   lease_token = %(token)s,
                   worker_id = %(worker)s,
                   updated_at = now()
              FROM claimed
             WHERE v.id = claimed.id
         RETURNING {_RETURNING_V}
        """
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, {"lease": lease_seconds, "token": token,
                                  "worker": worker_id})
                row = cur.fetchone()
        if row is None:
            return None
        return ClaimedJob(record=self._record(row), lease_token=token, worker_id=worker_id)

    def complete(self, job_id: int, lease_token: str, *, output_key: str,
                 metadata: dict[str, Any]) -> bool:
        sql = """
            UPDATE video_jobs
               SET status = 'COMPLETED', output_key = %(out)s,
                   metadata_json = %(meta)s, last_error = NULL,
                   lease_token = NULL, worker_id = NULL, lease_expires_at = NULL,
                   updated_at = now()
             WHERE id = %(id)s AND status = 'RUNNING' AND lease_token = %(token)s
        """
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, {"out": output_key, "meta": json.dumps(metadata),
                                  "id": job_id, "token": lease_token})
                return cur.rowcount == 1

    def fail(self, job_id: int, lease_token: str, error: str, *,
             max_attempts: int, base_backoff_seconds: int) -> str:
        sql = """
            UPDATE video_jobs
               SET status = CASE WHEN attempts >= %(maxa)s THEN 'DEAD' ELSE 'PENDING' END,
                   next_run_at = CASE WHEN attempts >= %(maxa)s THEN next_run_at
                                      ELSE now() + make_interval(secs => %(backoff)s) END,
                   last_error = %(err)s,
                   lease_token = NULL, worker_id = NULL, lease_expires_at = NULL,
                   updated_at = now()
             WHERE id = %(id)s AND status = 'RUNNING' AND lease_token = %(token)s
         RETURNING status
        """
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT attempts, max_attempts FROM video_jobs WHERE id = %s",
                            (job_id,))
                row = cur.fetchone()
                attempts = row["attempts"] if row else max_attempts
                backoff = backoff_seconds(attempts, base_backoff_seconds)
                cur.execute(sql, {"maxa": max_attempts, "backoff": backoff,
                                  "err": error[:2000], "id": job_id, "token": lease_token})
                updated = cur.fetchone()
        if updated is None:
            return STATUS_RUNNING
        return updated["status"]

    def requeue_expired(self) -> int:
        sql = """
            UPDATE video_jobs
               SET status = 'PENDING', lease_token = NULL, worker_id = NULL,
                   lease_expires_at = NULL, updated_at = now()
             WHERE status = 'RUNNING'
               AND lease_expires_at IS NOT NULL AND lease_expires_at < now()
        """
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(sql)
                return cur.rowcount

    def available(self) -> bool:
        try:
            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
                    cur.fetchone()
            return True
        except Exception:
            return False


class InMemoryJobStore:
    """Test double mirroring the Postgres semantics (lease token, backoff, DLQ)."""

    def __init__(self) -> None:
        self.rows: dict[int, JobRecord] = {}
        self._next_id = 1
        self._now = _utcnow

    def add(self, record: JobRecord) -> JobRecord:
        if not record.id:
            record.id = self._next_id
            self._next_id += 1
        self.rows[record.id] = record
        return record

    def claim(self, worker_id: str, *, lease_seconds: int) -> ClaimedJob | None:
        now = self._now()
        candidates = [
            r for r in self.rows.values()
            if r.status == STATUS_PENDING and (r.next_run_at is None or r.next_run_at <= now)
        ]
        if not candidates:
            return None
        record = sorted(candidates, key=lambda r: (r.next_run_at or now, r.id))[0]
        token = uuid.uuid4().hex
        record.status = STATUS_RUNNING
        record.attempts += 1
        record.lease_token = token
        record.worker_id = worker_id
        record.lease_expires_at = now + timedelta(seconds=lease_seconds)
        return ClaimedJob(record=record, lease_token=token, worker_id=worker_id)

    def complete(self, job_id: int, lease_token: str, *, output_key: str,
                 metadata: dict[str, Any]) -> bool:
        record = self.rows.get(job_id)
        if record is None or record.status != STATUS_RUNNING or record.lease_token != lease_token:
            return False
        record.status = STATUS_COMPLETED
        record.output_key = output_key
        record.metadata_json = json.dumps(metadata)
        record.last_error = None
        record.lease_token = None
        record.worker_id = None
        record.lease_expires_at = None
        return True

    def fail(self, job_id: int, lease_token: str, error: str, *,
             max_attempts: int, base_backoff_seconds: int) -> str:
        record = self.rows.get(job_id)
        if record is None or record.status != STATUS_RUNNING or record.lease_token != lease_token:
            return STATUS_RUNNING
        record.last_error = error[:2000]
        record.lease_token = None
        record.worker_id = None
        record.lease_expires_at = None
        if record.attempts >= max_attempts:
            record.status = STATUS_DEAD
        else:
            record.status = STATUS_PENDING
            record.next_run_at = self._now() + timedelta(
                seconds=backoff_seconds(record.attempts, base_backoff_seconds))
        return record.status

    def requeue_expired(self) -> int:
        now = self._now()
        count = 0
        for record in self.rows.values():
            if (record.status == STATUS_RUNNING and record.lease_expires_at is not None
                    and record.lease_expires_at < now):
                record.status = STATUS_PENDING
                record.lease_token = None
                record.worker_id = None
                record.lease_expires_at = None
                count += 1
        return count

    def available(self) -> bool:
        return True


def build_store(settings) -> JobStore:
    """Factory: Postgres in production, in-memory only when explicitly asked."""
    if getattr(settings, "database_url", ""):
        return PostgresJobStore(settings.database_url)
    return InMemoryJobStore()