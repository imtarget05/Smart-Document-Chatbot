"""DB-backed claims against V18 tables: SQL correctness via a recording
fake; live behavior covered by the integration test below."""
import pytest

from app import db_jobs


class RecordingConn:
    def __init__(self, fetch=None):
        self.statements = []
        self._fetch = fetch

    def cursor(self):
        return self

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def execute(self, sql, params=None):
        self.statements.append((sql, params))
        return self

    def fetchone(self):
        return self._fetch

    def commit(self):
        pass


def test_claim_uses_atomic_where_clause():
    conn = RecordingConn(fetch=("job-1", 1, "{}"))
    claimed = db_jobs.claim_job(conn, kind="agent_invoke", lease_seconds=60)
    sql = conn.statements[0][0]
    assert "UPDATE jobs" in sql
    assert "queued" in sql and "status" in sql
    assert "lease_expires_at" in sql
    assert claimed["job_id"] == "job-1"


def test_fail_terminal_moves_to_dlq():
    conn = RecordingConn(fetch=(3, "{}"))
    db_jobs.fail_job(conn, "job-9", "policy_violation: confidential to cloud")
    sqls = [s for s, _ in conn.statements]
    assert any("dead_letters" in s for s in sqls)
    assert any("dead_lettered" in s for s in sqls)


def test_fail_retryable_requeues():
    conn = RecordingConn(fetch=(1, "{}"))
    db_jobs.fail_job(conn, "job-3", "TIMEOUT: ollama slow")
    sqls = [s for s, _ in conn.statements]
    assert any("dead_letters" in s for s in sqls) is False
    assert any("'queued'" in s for s in sqls)


def test_find_returns_job_id_on_hit():
    import json

    conn = RecordingConn(fetch=(json.dumps({"job_id": "abc123"}),))
    assert db_jobs.find_job_by_idempotency_key(conn, "k-1") == "abc123"
    assert "idempotency_keys" in conn.statements[0][0]


def test_find_returns_none_on_miss():
    conn = RecordingConn(fetch=None)
    assert db_jobs.find_job_by_idempotency_key(conn, "missing") is None


def test_record_writes_mapping():
    conn = RecordingConn()
    db_jobs.record_job_idempotency_key(conn, "k-9", "job-9")
    sql, params = conn.statements[0]
    assert "idempotency_keys" in sql
    assert params[0] == "k-9"


@pytest.mark.integration
def test_claim_roundtrip_on_neon():
    import os

    url = os.environ.get("DATABASE_URL", "")
    if not url.startswith(("postgresql://", "postgres://")):
        pytest.skip("needs Neon DATABASE_URL")
    import psycopg

    with psycopg.connect(url) as conn:
        job_id = db_jobs.enqueue_job(conn, kind="agent_invoke", input_ref="{}")
        claimed = db_jobs.claim_job(conn, kind="agent_invoke")
        assert claimed is not None
        db_jobs.complete_job(conn, claimed["job_id"], result_ref="{}")
        assert claimed["job_id"] == job_id
