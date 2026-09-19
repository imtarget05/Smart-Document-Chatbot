-- V19: Durable video jobs (MAIA video pipeline V1 — SDC side, ADR-004 pattern).
-- Mirrors document_ingestion_jobs (V16): idempotent enqueue via a partial
-- unique index, PENDING -> RUNNING -> COMPLETED | DEAD, exponential backoff,
-- DEAD replayable via /admin/video-jobs/{id}/replay.
--
-- The video-worker (Python, separate process) claims rows with
-- SELECT ... FOR UPDATE SKIP LOCKED and runs FFmpeg OUTSIDE the web process;
-- lease_expires_at (set by the worker when it claims a row) is the crash
-- recovery signal so a long encode is never requeued while still alive.

CREATE TABLE IF NOT EXISTS video_jobs (
    id               BIGSERIAL    PRIMARY KEY,
    owner_username   VARCHAR(128) NOT NULL,
    source_hash      VARCHAR(128) NOT NULL,
    job_type         VARCHAR(32)  NOT NULL DEFAULT 'TRANSCODE',
    status           VARCHAR(16)  NOT NULL DEFAULT 'PENDING',
    attempts         INT          NOT NULL DEFAULT 0,
    max_attempts     INT          NOT NULL DEFAULT 3,
    next_run_at      TIMESTAMPTZ  NOT NULL DEFAULT now(),
    lease_expires_at TIMESTAMPTZ,
    last_error       TEXT,
    source_key       VARCHAR(512),
    output_key       VARCHAR(512),
    preset           VARCHAR(64),
    metadata_json    TEXT,
    payload          VARCHAR(512),
    created_at       TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at       TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_video_jobs_claim
    ON video_jobs (status, next_run_at);

CREATE INDEX IF NOT EXISTS idx_video_jobs_owner
    ON video_jobs (owner_username);

-- Idempotent enqueue: at most one active (PENDING/RUNNING) job per
-- (owner, source content, job type) — same DB-level guarantee as V16.
CREATE UNIQUE INDEX IF NOT EXISTS uq_video_jobs_active
    ON video_jobs (owner_username, source_hash, job_type)
    WHERE status IN ('PENDING', 'RUNNING');