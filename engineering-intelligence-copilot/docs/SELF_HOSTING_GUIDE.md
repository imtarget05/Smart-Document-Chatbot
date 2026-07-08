# Self-Hosting Guide

## 1. Overview

Engineering Intelligence Copilot can be self-hosted for internal engineering teams.

Target deployment shape:

- React frontend
- FastAPI backend
- PostgreSQL
- Qdrant
- optional Ollama or OpenAI-compatible provider
- reverse proxy (Nginx or similar)

This guide describes recommended setup path even though full new-stack Docker Compose is not finished yet.

---

## 2. Core Components

## Required
- frontend web app
- backend API
- PostgreSQL
- Qdrant

## Optional
- Ollama for local model hosting
- Prometheus + Grafana
- Redis for cache / background jobs
- object storage for uploaded files

---

## 3. Recommended Environment Variables

Backend examples:

```env
EIC_APP_NAME=Engineering Intelligence Copilot API
EIC_ENVIRONMENT=production
EIC_DEBUG=false
EIC_DATABASE_URL=postgresql+psycopg://user:password@postgres:5432/engineering_copilot
EIC_QDRANT_URL=http://qdrant:6333
EIC_QDRANT_COLLECTION=engineering_knowledge
EIC_LLM_PROVIDER=mock
EIC_LLM_MODEL=llama3.1:8b
EIC_EMBEDDING_PROVIDER=mock
EIC_EMBEDDING_MODEL=nomic-embed-text
EIC_JWT_SECRET_KEY=replace-with-strong-secret
EIC_ACCESS_TOKEN_EXPIRE_MINUTES=60
```

Frontend examples:
- backend API base URL
- auth config
- feature flags if needed

Do not commit production secrets to source control.

---

## 4. Deployment Topology

```text
Users
  │
  ▼
Reverse Proxy / Load Balancer
  ├─ Frontend
  └─ Backend API
        ├─ PostgreSQL
        ├─ Qdrant
        └─ LLM / Embedding Provider
```

Recommendation:
- keep frontend and backend stateless
- keep DB and Qdrant on persistent volumes
- isolate internal network between services

---

## 5. Local-to-Production Path

### Stage 1 — Local Development
- run frontend locally
- run backend locally
- run PostgreSQL and Qdrant in Docker
- use mock provider or local Ollama

### Stage 2 — Single Host
- Docker Compose on one VM
- reverse proxy in front
- persistent volumes
- environment variables via `.env` or secret injection

### Stage 3 — Managed/Internal Platform
- separate DB and vector DB
- deploy app services independently
- attach monitoring and backup policies
- enforce TLS and centralized secrets

---

## 6. Infrastructure Checklist

- [ ] PostgreSQL reachable
- [ ] Qdrant reachable
- [ ] backend env vars configured
- [ ] frontend API base URL configured
- [ ] reverse proxy routes set
- [ ] persistent volumes mounted
- [ ] backups enabled
- [ ] TLS configured
- [ ] secrets injected securely
- [ ] logs centralized

---

## 7. Reverse Proxy Guidance

Proxy should:
- serve frontend
- route `/api/*` to backend
- apply HTTPS
- set secure headers
- optionally rate-limit public endpoints

Avoid exposing internal-only service ports directly to internet if not needed.

---

## 8. Database Guidance

### PostgreSQL
Use for:
- users
- roles
- documents
- sessions
- audit logs
- 8D cases
- evaluation runs

Recommendations:
- dedicated DB user
- regular backups
- connection pooling
- restrict external access

### Qdrant
Use for:
- chunk embeddings
- semantic metadata filtering
- knowledge search

Recommendations:
- persist volume
- protect network exposure
- snapshot backup strategy if used in production

---

## 9. LLM Provider Options

## Option A — Mock Provider
Use for:
- backend startup validation
- demo without model dependency
- CI or smoke tests

## Option B — Ollama
Use for:
- local/private deployment
- internal testing
- lower external dependency

## Option C — OpenAI-Compatible API
Use for:
- stronger hosted models
- managed inference
- faster prototyping if policy allows

Choose based on:
- privacy requirements
- latency
- cost
- quality expectations

---

## 10. Observability

Recommended:
- health endpoint checks
- readiness checks
- request logs
- latency and error metrics
- audit logs for AI operations
- container/service monitoring

Current new backend already provides:
- `/health`
- `/ready`
- `/metrics` placeholder

---

## 11. Backup and Recovery

Minimum backup scope:
- PostgreSQL data
- Qdrant snapshots or backup process
- uploaded files if stored locally
- deployment config excluding secrets in plain text

Recovery plan should verify:
- DB restore works
- vector index restore works
- backend reconnects successfully
- frontend can reach API after restore

---

## 12. Security Notes

Before production:
- set strong JWT secret
- disable debug
- use HTTPS
- restrict CORS
- enable RBAC
- validate uploads
- audit sensitive actions
- review connector permissions
- rotate credentials regularly

See also:
- `docs/SECURITY.md`

---

## 13. Current Status

Implemented now:
- new backend scaffold
- config loading
- API v1 root router
- health/ready/metrics endpoints
- architecture/demo/security/interview docs

Still pending for complete self-hosted stack:
- production Docker Compose for new Python-first stack
- migrations and DB models
- auth + RBAC
- ingestion APIs
- retrieval and agent endpoints
- frontend integration for new backend

This means current guide is deployment-ready in structure, but not full production-ready in feature completeness.