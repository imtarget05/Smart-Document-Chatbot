-- V16: Durable document ingestion jobs (ADR-004).
-- Replaces the fire-and-forget CompletableFuture workflow call with a
-- persistent job table so the llm-router document workflow survives
-- restarts and retries with exponential backoff. DEAD jobs act as the
-- durable dead-letter queue and can be replayed via /admin/ingestion-jobs.

CREATE TABLE IF NOT EXISTS document_ingestion_jobs (
    id            BIGSERIAL PRIMARY KEY,
    document_id   BIGINT       NOT NULL,
    job_type      VARCHAR(32)  NOT NULL DEFAULT 'WORKFLOW',
    status        VARCHAR(16)  NOT NULL DEFAULT 'PENDING',
    attempts      INT          NOT NULL DEFAULT 0,
    max_attempts  INT          NOT NULL DEFAULT 3,
    next_run_at   TIMESTAMPTZ  NOT NULL DEFAULT now(),
    last_error    TEXT,
    payload       VARCHAR(512),
    created_at    TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_ingestion_jobs_claim
    ON document_ingestion_jobs (status, next_run_at);

CREATE INDEX IF NOT EXISTS idx_ingestion_jobs_document
    ON document_ingestion_jobs (document_id);

-- At most one active (PENDING/RUNNING) job per document+type:
-- DB-level idempotency for duplicate enqueue attempts.
CREATE UNIQUE INDEX IF NOT EXISTS uq_ingestion_jobs_active
    ON document_ingestion_jobs (document_id, job_type)
    WHERE status IN ('PENDING', 'RUNNING');
