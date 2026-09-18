"""DB-backed job claims against Flyway V18 tables (Plan 03).

Callers keep the in-memory jobs.py path when DATABASE_URL is unset; this
module is used only with a postgres URL. Error taxonomy: codes starting
with TIMEOUT/GATEWAY_/LOCAL_BUSY/MODEL_LOADING/CONNECTION are retryable
(max 3 attempts, exponential lease backoff); policy_violation/validation/
auth/not-found and exhausted attempts are terminal and move the job to
dead_letters with a safe diagnosis.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone

MAX_ATTEMPTS = 3
RETRYABLE_PREFIXES = (
    "TIMEOUT",
    "GATEWAY_",
    "LOCAL_BUSY",
    "MODEL_LOADING",
    "CONNECTION",
)


def _now():
    return datetime.now(timezone.utc)


def _is_retryable(error: str) -> bool:
    head = error.split(":")[0]
    return head in RETRYABLE_PREFIXES or any(
        error.startswith(p) for p in RETRYABLE_PREFIXES
    )


def enqueue_job(conn, kind, input_ref="{}"):
    job_id = uuid.uuid4().hex[:12]
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO jobs (job_id, kind, status, attempt, input_ref,"
            " created_at, updated_at)"
            " VALUES (%s, %s, 'queued', 0, %s, now(), now())",
            (job_id, kind, input_ref),
        )
    conn.commit()
    return job_id


def claim_job(conn, kind, lease_seconds=60):
    """Atomically claim one queued job (or an expired lease). One winner."""
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE jobs SET status='running', attempt=attempt+1,"
            " lease_expires_at=%s, updated_at=now()"
            " WHERE job_id = (SELECT job_id FROM jobs WHERE kind=%s"
            " AND (status='queued'"
            " OR (status='running' AND lease_expires_at < now()))"
            " ORDER BY created_at LIMIT 1 FOR UPDATE SKIP LOCKED)"
            " RETURNING job_id, attempt, input_ref",
            (_now() + timedelta(seconds=lease_seconds), kind),
        )
        row = cur.fetchone()
    conn.commit()
    if row is None:
        return None
    return {"job_id": row[0], "attempt": row[1], "input_ref": row[2]}


def complete_job(conn, job_id, result_ref="{}"):
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE jobs SET status='succeeded', result_ref=%s,"
            " updated_at=now() WHERE job_id=%s",
            (result_ref, job_id),
        )
        cur.execute(
            "INSERT INTO outbox_events (event_id, destination, payload,"
            " version, attempts) VALUES (%s, %s, %s, 'v1', 0)"
            " ON CONFLICT (event_id) DO NOTHING",
            (
                f"job-succeeded:{job_id}",
                "agent-jobs",
                json.dumps({"job_id": job_id, "status": "succeeded"}),
            ),
        )
    conn.commit()


def fail_job(conn, job_id, error, owner="llm-router"):
    """Retryable errors requeue with backoff; terminal errors (or attempts
    exhausted) write a dead_letters row with safe diagnosis + outbox event."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT attempt, input_ref FROM jobs WHERE job_id=%s", (job_id,)
        )
        attempt, input_ref = cur.fetchone()
        if _is_retryable(error) and attempt < MAX_ATTEMPTS:
            cur.execute(
                "UPDATE jobs SET status='queued', error_class=%s,"
                " lease_expires_at=%s, updated_at=now() WHERE job_id=%s",
                (
                    error[:64],
                    _now() + timedelta(seconds=2 ** attempt * 30),
                    job_id,
                ),
            )
        else:
            cur.execute(
                "UPDATE jobs SET status='dead_lettered', error_class=%s,"
                " updated_at=now() WHERE job_id=%s",
                (error[:64], job_id),
            )
            cur.execute(
                "INSERT INTO dead_letters (job_id, input_ref, diagnosis, owner,"
                " replay_decision) VALUES (%s, %s, %s, %s, 'pending')"
                " ON CONFLICT (job_id) DO NOTHING",
                (job_id, input_ref, error[:500], owner),
            )
            cur.execute(
                "INSERT INTO outbox_events (event_id, destination, payload,"
                " version, attempts) VALUES (%s, %s, %s, 'v1', 0)"
                " ON CONFLICT (event_id) DO NOTHING",
                (
                    f"job-dead:{job_id}",
                    "agent-jobs",
                    json.dumps({"job_id": job_id, "diagnosis": error[:500]}),
                ),
            )
    conn.commit()


def replay_job(conn, job_id, operator):
    """Operator-only replay: reset to queued, preserve evidence trail."""
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE dead_letters SET replay_decision='replayed:' || %s"
            " WHERE job_id=%s",
            (operator, job_id),
        )
        cur.execute(
            "UPDATE jobs SET status='queued', attempt=0, updated_at=now()"
            " WHERE job_id=%s",
            (job_id,),
        )
    conn.commit()


def find_job_by_idempotency_key(conn, idempotency_key):
    """Return the existing job_id for a replayed submit key, else None."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT response FROM idempotency_keys"
            " WHERE caller_scope='agent_jobs' AND idem_key=%s"
            " AND status='completed'",
            (idempotency_key,),
        )
        row = cur.fetchone()
    if row is None:
        return None
    return json.loads(row[0]).get("job_id")


def record_job_idempotency_key(conn, idempotency_key, job_id):
    """Map a submit key to its job for future replay dedupe."""
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO idempotency_keys (caller_scope, idem_key, fingerprint,"
            " status, response, expires_at)"
            " VALUES ('agent_jobs', %s, '', 'completed', %s, NULL)"
            " ON CONFLICT (caller_scope, idem_key) DO NOTHING",
            (idempotency_key, json.dumps({"job_id": job_id})),
        )
    conn.commit()
