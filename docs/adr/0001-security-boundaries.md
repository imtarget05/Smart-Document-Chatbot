# ADR 0001: Authentication and Tenant Boundaries

Status: Accepted

## Context

The application stores user documents and chat histories. Authentication without object ownership still permits an authenticated user to enumerate another user's document IDs or session histories. ETL and metrics endpoints also expose sensitive capability or operational data.

## Decision

- JWTs use a configured base64 signing secret, rather than a new random key at each startup.
- `Document` and `ChatMessage` persist `owner_username`; all browser-facing reads, deletes and RAG retrievals filter by the authenticated user.
- Airflow callbacks and the Prometheus endpoint require `INTERNAL_SERVICE_TOKEN` through a dedicated service authentication filter.
- Only health, API docs and authentication endpoints are public.
- Production startup fails on known development secrets or the default database password.
- Uploads accept only PDF, DOCX and TXT and validate extension/content-type consistency.

## Consequences

Existing rows migrate with owner `legacy` and are deliberately not visible to normal accounts until explicitly migrated to an owner. Production deployments must rotate and distribute `JWT_SECRET` and `INTERNAL_SERVICE_TOKEN`. A metrics scraper without the internal token now receives `401`/`403`.
