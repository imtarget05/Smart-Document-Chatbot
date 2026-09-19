-- V20: video job lease ownership.
-- V19 recovered expired leases by status alone, which cannot distinguish the
-- worker that legitimately holds a row from a stale one. The video-worker now
-- claims a row with a fresh (worker_id, lease_token); complete/fail are guarded
-- by that token so a resurrected stale worker can never overwrite the result of
-- the worker that actually owns the lease.
ALTER TABLE video_jobs ADD COLUMN IF NOT EXISTS worker_id   VARCHAR(64);
ALTER TABLE video_jobs ADD COLUMN IF NOT EXISTS lease_token VARCHAR(64);

CREATE INDEX IF NOT EXISTS idx_video_jobs_lease_token
    ON video_jobs (lease_token) WHERE lease_token IS NOT NULL;