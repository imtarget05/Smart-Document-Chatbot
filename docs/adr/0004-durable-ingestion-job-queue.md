# ADR 0004: Durable Ingestion Job Queue (DB-backed, no broker)

Status: Accepted

## Context

The upload path fired the llm-router document workflow with
`CompletableFuture.runAsync` — fire-and-forget inside the JVM. Three failure
modes were unhandled:

1. **Restart/crash loses work.** A backend redeploy mid-ingestion silently
   dropped the workflow step; the document stayed without `workflow_result`
   forever, with no record that anything was owed.
2. **No retry.** The llm-router is a separate service (rolling deploys, cold
   starts, upstream LLM outages). A transient 5xx during that window was
   terminal.
3. **The "DLQ" was a `ConcurrentHashMap`.** `ChatDlqService` retained failures
   only in memory (max 1000, lost on restart, no replay path) — the name
   promised durability the data structure could not deliver.

The tempting fix is a message broker (RabbitMQ/Kafka). But the workload is one
HTTP call per human document upload — low volume, single producer, single
consumer pool — and the deployment target (Render free tier) runs one instance.
A broker adds an always-on dependency to solve a demonstrated problem that
PostgreSQL already solves.

## Decision

Persist ingestion jobs in PostgreSQL (`document_ingestion_jobs`, Flyway V16)
and process them in-process:

- **Idempotent enqueue**: at most one active (PENDING/RUNNING) job per
  `(document_id, job_type)`, enforced by a partial unique index — duplicate
  enqueues are impossible at the DB level, not just in application code.
- **Claim with `SELECT ... FOR UPDATE SKIP LOCKED`** (Hibernate lock-timeout
  `-2`) in a short REQUIRES_NEW transaction, so the design scales to multiple
  instances without re-work. Work executes OUTSIDE the claim transaction.
- **Crash recovery by lease timeout**: a RUNNING row not updated within
  `ingestion-jobs.stale-running-minutes` is requeued automatically — no job
  can be stranded by a dead worker.
- **Retry with exponential backoff** (30s → 2m → 8m), then
  **DEAD** — a durable dead-letter state stored in the same table, replayable
  per-job by an admin via `POST /admin/ingestion-jobs/{id}/replay`.
- **Idempotent work**: a document that already carries `workflow_result` is a
  no-op, so replays never double-process.
- Service split (`DocumentJobService` = enqueue/poll/replay,
  `DocumentJobExecutor` = claim/execute) so REQUIRES_NEW boundaries cross a
  real Spring proxy instead of self-invocation.

## Consequences

- No new infrastructure: the queue lives in the database we already run
  (Neon PostgreSQL), gets backups/monitoring for free, and survives deploys.
- At-least-once semantics: the executor must stay idempotent (it is, via the
  `workflow_result` guard). Any future job type added to this table must be
  idempotent too.
- The in-memory `ChatDlqService` for SSE chat failures remains in-memory by
  design — chat retries are user-driven and transient; it is no longer
  presented as the ingestion DLQ.
- Migration trigger to a real broker: multiple worker *types*, fan-out to
  independent consumers, throughput beyond ~10 jobs/s, or a second service
  needing the same queue. Until then a broker would be cargo-cult
  engineering.
