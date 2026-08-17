# Self-Hosting Guide

## 1. Overview

Smart Document Chatbot can be self-hosted for internal engineering teams.

Target deployment shape:

- React frontend
- Java Spring Boot backend
- Python FastAPI agent service (LangGraph orchestration)
- PostgreSQL
- Qdrant
- Ollama via LLM router (or OpenAI-compatible provider)
- Prometheus + Grafana (optional)
- n8n workflow automation (optional)
- reverse proxy (Nginx or similar)

This guide describes the recommended setup path for the full production stack in `docker/docker-compose.yml`.

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

Backend examples (see `.env.example` at repo root):

```env
DATABASE_URL=jdbc:postgresql://postgres:5432/smart_doc_chatbot
POSTGRES_USER=postgres
POSTGRES_PASSWORD=replace-with-strong-secret
POSTGRES_DB=smart_doc_chatbot
JWT_SECRET=replace-with-random-48-char-secret
INTERNAL_SERVICE_TOKEN=replace-with-random-48-char-secret
QDRANT_HOST=qdrant
QDRANT_PORT=6333
QDRANT_API_KEY=
OLLAMA_BASE_URL=http://ollama:11434
LOCAL_CHAT_MODEL_SIMPLE=qwen2.5:7b
LOCAL_CHAT_MODEL_COMPLEX=qwen2.5:7b
LOCAL_EMBED_MODEL=nomic-embed-text
LLM_CHAT_MODEL=qwen2.5:7b
LLM_EMBEDDING_MODEL=nomic-embed-text
LLM_TEMPERATURE=0.3
AGENT_RATE_LIMIT_RPM=30
```

Do not commit production secrets to source control. Generate secrets with `openssl rand -base64 48`.

---

## 4. Deployment Topology

```text
Users
  │
  ▼
Reverse Proxy / Load Balancer
  ├─ Frontend (React)
  ├─ Backend API (Spring Boot)
  ├─ Agent Service (FastAPI)
  └─ LLM Router (Ollama)
        ├─ PostgreSQL
        ├─ Qdrant
        └─ n8n (optional)
```

Recommendation:
- keep frontend and backend stateless
- keep DB and Qdrant on persistent volumes
- isolate internal network between services

---

## 5. Local-to-Production Path

### Stage 1 — Local Development
- run frontend locally (`npm run dev`)
- run backend locally (`mvn spring-boot:run`)
- run PostgreSQL, Qdrant, and Ollama in Docker
- use local Ollama models (qwen2.5:7b + nomic-embed-text)

### Stage 2 — Single Host
- `docker compose up -d` with the production compose file
- reverse proxy in front (Nginx config included under `docker/`)
- persistent volumes
- environment variables via `.env` or secret injection

### Stage 3 — Managed/Internal Platform
- deploy via Kubernetes manifests under `k8s/` (ArgoCD GitOps)
- separate DB and vector DB
- attach monitoring (Prometheus/Grafana) and backup policies
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

## Option A — Local Ollama
Use for:
- local/private deployment
- internal testing
- lower external dependency

## Option B — OpenAI-Compatible API
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

Current stack already provides:
- Spring Boot Actuator health endpoint (`/api/actuator/health`)
- Prometheus scrape target configured in `docker/monitoring/prometheus.yml`
- Grafana dashboards
- AOP-based audit logging for sensitive actions

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
- production Docker Compose stack (`docker/docker-compose.yml` + dev/monitoring/mlops variants)
- Kubernetes manifests + ArgoCD GitOps under `k8s/`
- GitHub Actions CI/CD pipeline
- RBAC (ADMIN / ENGINEER / VIEWER) + audit logging
- agentic CRAG pipeline with Ollama LLM router
- RAG evaluation harness (`eval/`, `agent/benchmark`)

Still pending for complete self-hosted stack:
- wiring the evaluation API to the eval pipeline end-to-end
- connector coverage beyond Gmail / Google Drive / SharePoint / Slack (REST API, SQL read-only)
- Prometheus endpoint fully exposed via Spring Boot Actuator (scrape config exists in `docker/monitoring`)

This means the repo is deployment-ready in structure, with feature completeness still expanding.