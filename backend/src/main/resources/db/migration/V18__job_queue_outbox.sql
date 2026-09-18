-- V18: Generic durable job queue + outbox + idempotency + DLQ (Plan 02).
-- Distinct from V16 document_ingestion_jobs (ingestion-specific): these are
-- the cross-cutting ops tables shared by every long-running workflow
-- (retraining, indexing, agent jobs). Audit trail lives in V9 and is not
-- repeated here. Flyway has no down migration by design; staging rollback
-- is DROP TABLE of the four tables below.

CREATE TABLE IF NOT EXISTS jobs (
    job_id           VARCHAR(64)  PRIMARY KEY,
    kind             VARCHAR(64)  NOT NULL DEFAULT '',
    status           VARCHAR(32)  NOT NULL DEFAULT 'queued',
    attempt          INT          NOT NULL DEFAULT 0,
    lease_expires_at TIMESTAMPTZ,
    input_ref        TEXT         NOT NULL DEFAULT '',
    result_ref       TEXT         NOT NULL DEFAULT '',
    error_class      VARCHAR(64)  NOT NULL DEFAULT '',
    created_at       TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at       TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_jobs_status
    ON jobs (status);

-- Atomic lease claim pattern: at most one RUNNING holder per job.
CREATE UNIQUE INDEX IF NOT EXISTS uq_jobs_single_running
    ON jobs (job_id)
    WHERE status = 'RUNNING';

CREATE TABLE IF NOT EXISTS outbox_events (
    event_id      VARCHAR(64)  PRIMARY KEY,
    destination   VARCHAR(128) NOT NULL DEFAULT '',
    payload       TEXT         NOT NULL DEFAULT '',
    version       VARCHAR(32)  NOT NULL DEFAULT 'v1',
    attempts      INT          NOT NULL DEFAULT 0,
    next_retry_at TIMESTAMPTZ,
    delivered_at  TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_outbox_next_retry
    ON outbox_events (next_retry_at)
    WHERE delivered_at IS NULL;

CREATE TABLE IF NOT EXISTS idempotency_keys (
    caller_scope VARCHAR(128) NOT NULL,
    idem_key     VARCHAR(128) NOT NULL,
    fingerprint  TEXT         NOT NULL DEFAULT '',
    status       VARCHAR(32)  NOT NULL DEFAULT 'pending',
    response     TEXT         NOT NULL DEFAULT '',
    expires_at   TIMESTAMPTZ,
    PRIMARY KEY (caller_scope, idem_key)
);

CREATE TABLE IF NOT EXISTS dead_letters (
    job_id          VARCHAR(64)  PRIMARY KEY,
    input_ref       TEXT         NOT NULL DEFAULT '',
    diagnosis       TEXT         NOT NULL DEFAULT '',
    owner           VARCHAR(128) NOT NULL DEFAULT '',
    replay_decision VARCHAR(32)  NOT NULL DEFAULT 'pending'
);
