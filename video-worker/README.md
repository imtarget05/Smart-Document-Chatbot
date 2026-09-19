# SDC video-worker

Separate Python process that consumes the durable `video_jobs` queue
(Flyway `V19`/`V20`, ADR-004 pattern) and runs **FFmpeg outside the web
process**, uploading the result to object storage.

This is the SDC side of the MAIA video pipeline plan (`S5`/`S6`, DoD 11–15).
The Java backend owns the durable state and the HTTP surface; this worker owns
execution.

## Flow

```
video_jobs (Postgres/Neon)
   │  claim: SELECT ... FOR UPDATE SKIP LOCKED  (+ lease_token, worker_id)
   ▼
download source (R2/local) ──► ffprobe ──► ffmpeg ──► upload outputs/<id>*
   │
   ▼
complete  WHERE id = ? AND status='RUNNING' AND lease_token = ?   → COMPLETED
   │ else on error: attempts+1, exponential backoff → PENDING | DEAD
```

- **Idempotent enqueue**: one active job per `(owner_username, source_hash,
  job_type)` (partial unique index) — enforced in the DB, not just the API.
- **Crash recovery**: only a `RUNNING` row whose `lease_expires_at` has passed is
  requeued; a live long encode keeps renewing its lease and is never disturbed.
- **Lease ownership**: `complete`/`fail` are guarded by the claim's
  `lease_token`, so a resurrected stale worker can never overwrite the result of
  the worker that actually owns the row.
- **DEAD = durable DLQ**, replayable via `POST /admin/video-jobs/{id}/replay`.

## Vendored core

`video_worker/encoder.py` and `video_worker/pipeline.py` are vendored from MAIA
(see `PROVENANCE.md` for commit, SHA-256 and the one deliberate bug fix:
`force_divisible_by=2`, without which 1280x720 → 480p fails with an odd width).

## Configuration

| Env | Default | Meaning |
|---|---|---|
| `VIDEO_DATABASE_URL` (or `NEON_DATABASE_URL`/`DATABASE_URL`) | local PG | queue database |
| `STORAGE_PROVIDER` / `VIDEO_STORAGE_PROVIDER` | `local` | `local` or `r2` |
| `VIDEO_STORAGE_DIR` | `storage/video` | local backend root |
| `R2_ACCOUNT_ID`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `R2_BUCKET_NAME`, `R2_ENDPOINT` | — | Cloudflare R2 |
| `VIDEO_ENCODER_PROFILE` | `auto` | `auto`/`videotoolbox`/`nvenc`/`libx264` |
| `VIDEO_LEASE_SECONDS` | `900` | claim lease |
| `VIDEO_MAX_ATTEMPTS` | `3` | attempts before DEAD |
| `VIDEO_BASE_BACKOFF_SECONDS` | `30` | backoff base (×4 per attempt) |
| `VIDEO_OUTPUT_PREFIX` | `outputs` | output key prefix |

The worker **refuses to start** when the database is unreachable or when `r2` is
selected without credentials (`readiness_errors()`), instead of degrading
silently.

## Run

```bash
pip install -r requirements.txt
python -m video_worker            # honours VIDEO_CONCURRENCY
python -m video_worker 4          # 4 worker threads in this process
# or horizontally: several container replicas (the DB claim is SKIP LOCKED)
```

## Test

```bash
python -m pytest tests -q
```

Covers encoder resolution, ffmpeg argument building, the full queue state
machine (complete / backoff / DEAD / expired-lease / stale lease token) with a
fake ffmpeg, and **real-ffmpeg** end-to-end tests that assert a playable
`854x480 h264` artifact is produced (skipped only when ffmpeg is absent).

## Still to do (plan DoD 13–15)

- Spring `POST/GET /api/video/*` + `/admin/video-jobs/{id}/replay`.
- R2 pre-signed URLs for source upload / output download in the backend.
- JUnit controller tests (this worker is already covered by pytest).