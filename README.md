# 🤖 Smart Document Chatbot — Enterprise RAG Platform

[![CI/CD](https://github.com/imtarget05/Smart-Document-Chatbot/actions/workflows/ci.yml/badge.svg)](https://github.com/imtarget05/Smart-Document-Chatbot/actions)
[![Java 17](https://img.shields.io/badge/Java-17-ED8B00?logo=openjdk)](https://openjdk.org/)
[![React 18](https://img.shields.io/badge/React-18-61DAFB?logo=react)](https://react.dev/)
[![Spring Boot](https://img.shields.io/badge/Spring%20Boot-3.2-6DB33F?logo=spring)](https://spring.io/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.x-3178C6?logo=typescript)](https://www.typescriptlang.org/)
[![Python 3.11](https://img.shields.io/badge/Python-3.11-3776AB?logo=python)](https://python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> **AI-powered document Q&A system** with Corrective RAG (CRAG) architecture for accurate, hallucination-free answers.

## 🎯 What It Does

Smart Document Chatbot is an enterprise-grade RAG (Retrieval-Augmented Generation) platform that allows users to:

1. **Upload** legal documents (PDF, DOCX, TXT)
2. **Ask questions** in natural language (Vietnamese/English)
3. **Get accurate answers** with source citations
4. **Trust the output** — Hallucination mitigation through 5-layer verification

## 🏗️ Architecture (Hybrid: Cloudflare Pages + Render + Local Fallback)

```
┌────────────────────────────────────────────────────────────────────────┐
│           Frontend (React 18 + TS, Vite) — Port 80 / 5173              │
│       Cloudflare Pages: smart-doc-chatbot.pages.dev • Local: :5173     │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ HTTP / REST / SSE / CORS
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│             Backend (Spring Boot 3.2) — Port 8080                      │
│   JWT + CSRF + RateLimit (fail-closed) + Audit + SSO/Keycloak          │
│   CRAG Engine • PostgreSQL Lexical Search • Langfuse Tracing           │
└───────────┬───────────────────────┬────────────────────────────┬───────┘
            │                       │                            │
      Database/Auth           LLM Queries                Agent Delegation
            │                       │                            │
            ▼                       ▼                            ▼
┌───────────────────────┐ ┌───────────────────┐ ┌────────────────────────┐
│ Data & Auth Stores    │ │ LLM Router        │ │ Agent (FastAPI)        │
│ • Neon PG / Postgres  │ │ (FastAPI) — :8001 │ │ Port 9000              │
│   (Port 5432/5434)    │ │ Gateway / Proxy   │ │ LangGraph Orchestration│
│ • Qdrant (Port 6333)  │ │ Prompt Compressor │ │ HITL Approval Gate     │
│ • Redis (Port 6379)   │ │ Response Cache    │ │ Qdrant Hybrid Search   │
│ • Keycloak (Port 8180)│ │ Circuit Breaker   │ └───────────┬────────────┘
└───────────────────────┘ └─────────┬─────────┘             │
                                    │                       │ Tools API
                                    │                       ▼
                                    │           ┌────────────────────────┐
                                    │           │ Supply Chain API       │
                                    │           │ (FastAPI) — Port 8020  │
                                    │           │ /forecast, /route,     │
                                    │           │ /supplier-risk         │
                                    │           └────────────────────────┘
                                    ▼
                     ┌─────────────────────────────┐
                     │ LLM Inference Providers     │
                     │ • Cloudflare Workers AI     │
                     │   (@cf/meta/llama-3.3-70b)  │
                     │ • Local Ollama (:11434)     │
                     │   (llama3.2 / qwen3:8b)     │
                     └─────────────────────────────┘

Local fallback: docker-compose.dev.yml (pgvector:5434/qdrant:6333/redis:6379 + Keycloak:8180)
```

> **Note:** Production chat uses **PostgreSQL lexical search**. Qdrant hybrid search + BM25 + RRF is available in the Python agent service (`agent/`, port 9000). **SSO prod disabled until Keycloak public URL ready** (`SSO_OIDC_ENABLED=false` on Render).

## ✨ Key Features

### 🧠 AI/ML Capabilities
- **Corrective RAG (CRAG)**: Auto-corrects low-confidence retrievals
- **5-Layer Hallucination Defense**: Confidence gate → Lexical support → Retrieval scoring → Abstention → Eval heuristic
- **Vietnamese Legal NLP**: Điều/Khoản/Điểm structure detection
- **Multi-LLM Support**: Ollama (local) + Cloudflare Workers AI (cloud)
- **Prompt Injection Defense**: Blocks direct, role-play, and homoglyph attacks

### 🤖 Agent Mode (default ON)
- **Default agent-first**: backend `ChatService.java` uses `agentMode = !"rag".equalsIgnoreCase(mode)`
  for both `/chat/ask` and `/chat/ask-stream`; `mode=rag` forces plain RAG, otherwise the
  request delegates to the agent (LangGraph, port 9000) with automatic CRAG/RAG fallback.
- **Frontend default ON**: `ChatPage.tsx` uses `useState(true)` for the Agent Mode toggle.
- **Resilience**: `ChatDedupService` (5s/30s idempotency window), `ChatDlqService`
  (DLQ, max 1000 events), `SseStreamManager` (bounded thread pool + graceful shutdown);
  constructor chaining keeps backward compatibility for existing callers.

### 🔒 Security
- **JWT Authentication** with refresh tokens
- **CSRF Protection** (double-submit cookie pattern)
- **Role-Based Access Control** (ADMIN, ENGINEER, USER)
- **Rate Limiting** (Redis-backed sliding window)
- **Audit Logging** (immutable trail)
- **SSO/OIDC Integration** (Keycloak, Azure AD, Okta)

### 👤 Human-in-the-Loop Governance
- **HITL approval gate** (`agent/hitl.py` + LangGraph `hitl_gate` node): every
  orchestrated real-world action (email, Jira, Notion, webhook) **pauses** for
  human approval before execution — the LLM cannot act unilaterally.
- **Approval queue API**: `GET /api/v1/agent/approvals` (pending queue),
  `POST /agent/approvals/{id}/approve` (resume + execute the exact paused
  request), `POST /agent/approvals/{id}/reject` (nothing executes).
- **TTL expiry** of stale approvals (`HITL_APPROVAL_TTL_SECONDS`, default 1h),
  on/off switch (`HITL_REQUIRE_APPROVAL`, default on).
- Verified by `agent/tests/test_hitl.py` (store lifecycle, TTL expiry,
  graph routing, full approve/reject API flow).

### 🛠️ DevOps
- **CI/CD Pipeline** (GitHub Actions — CI + CD + Pages auto)
- **Hybrid Deploy**: Cloudflare Pages (frontend) + Render (backend/llm-router/agent/Keycloak)
- **Docker Compose** (full stack — prod/dev/local/monitoring)
- **Database Migrations** (Flyway V1..V15 — V15 `drop_n8n_analytics` removes the n8n-workflows tables; `n8n-workflows/` directory deleted)
- **Monitoring** (Langfuse Cloud + Prometheus + Grafana)
- **Automated Testing** (backend 291/291, chat module 43/43, agent 61/61, llm-router 80/80, eval grader 26/26, supply-chain api 9/9, frontend `tsc` 0 errors)

## ⚠️ Known Limitations

- **Retrieval accuracy varies significantly by document** (9.68%–96.8% across 5 production runs). The median is ~71%.
- **Hallucination rate is 3-10%**, not 0%. Every eval run shows 1-3 hallucination cases.
- **Production chat uses PostgreSQL lexical search**, not Qdrant hybrid search. Qdrant is only in the Python agent service (`agent/`, port 9000).
- **Evaluation uses keyword matching**, not semantic similarity (semantic metric added but not yet calibrated).
- **SSO disabled on Render until Keycloak public URL ready** — local Keycloak `http://localhost:8180` works, prod `SSO_OIDC_ENABLED=false` (enable with `https://smartdoc-keycloak.onrender.com/realms/smartdoc`).

## ✅ What's Genuinely Implemented

- Full-stack app: Spring Boot + React + TypeScript + Python
- JWT auth, CSRF, RBAC, account lockout, audit logging
- CRAG corrective loop with query reformulation
- Hybrid search + BM25 + RRF (Python agent)
- Docker Compose with full microservices, healthchecks, monitoring
- CI/CD pipeline with tests, security scan, eval
- Prompt injection defense
- Legal document parsing with OCR fallback
- Streaming SSE
- LangGraph multi-agent orchestration
- GraphRAG memory prototype
- MLflow experiment tracking
- LoRA fine-tuning pipeline
- LLM-judge evaluation

## 🚀 Quick Start

### Prerequisites
- Java 17+ (backend `mvn compile` green on JDK 17)
- Node.js 20+ (frontend requires `npm ci` — `node_modules/` is not committed)
- Docker & Docker Compose
- Python 3.11+ (requires `prometheus_client`; `pyrightconfig.json` `extraPaths` covers `eval/tests`)
- Ollama (optional, for local LLM)

### 1. Clone & Setup
```bash
git clone https://github.com/imtarget05/Smart-Document-Chatbot.git
cd Smart-Document-Chatbot
cp .env.example .env
# Edit .env: CLOUDFLARE_*, R2_*, JWT_SECRET (openssl rand -base64 48)
```

### 2. Start Infrastructure (local hybrid fallback)
```bash
make local-infra-up          # pgvector:5434, qdrant:6333, redis:6379
# Keycloak local (SSO dev)
docker run -d --name smartdoc-keycloak -p 8180:8080 -e KEYCLOAK_ADMIN=admin -e KEYCLOAK_ADMIN_PASSWORD=admin quay.io/keycloak/keycloak:24.0.5 start-dev
# Then create realm/client: see docs/reports/PLAN_HYBRID_PROD.md
```

### 3. Start Backend (Spring Boot — Port 8080)
```bash
cd backend
export JAVA_HOME=/opt/homebrew/opt/openjdk@17
mvn spring-boot:run
```

### 4. Start Python Microservices & Frontend
```bash
# LLM Router (FastAPI — Port 8001)
cd llm-router && uvicorn app.main:app --host 0.0.0.0 --port 8001

# Agent Service (FastAPI LangGraph — Port 9000)
cd agent && uvicorn main:app --host 0.0.0.0 --port 9000

# Supply Chain API (FastAPI — Port 8020)
cd supply-chain-module && uvicorn api.main:create_app --factory --host 0.0.0.0 --port 8020

# Frontend (React 18 + Vite — Port 5173 / 3000)
cd frontend
npm ci
npm run dev
```

### 5. Access & Port Reference
- **Frontend React**: http://localhost:5173 (Vite dev) or http://localhost:3000 (Docker dev) — prod: https://smart-doc-chatbot.pages.dev
- **Backend Spring Boot**: http://localhost:8080/api — prod: https://smart-doc-backend-h4mt.onrender.com/api
- **Backend Swagger UI**: http://localhost:8080/api/swagger-ui.html
- **Agent Service (FastAPI)**: http://localhost:9000 — API docs: http://localhost:9000/docs
- **LLM Router (FastAPI)**: http://localhost:8001 — API docs: http://localhost:8001/docs
- **Supply Chain API (FastAPI)**: http://localhost:8020 — API docs: http://localhost:8020/docs
- **Keycloak SSO**: http://localhost:8180 (admin/admin, realm: `smartdoc`)

### 6. Deploy (Hybrid, free-tier)
- **Frontend Pages**: `CLOUDFLARE_API_TOKEN` Pages:Edit + `wrangler pages deploy frontend/dist --project-name=smart-doc-chatbot`
  or auto via `.github/workflows/pages.yml` (push main → `VITE_API_URL=https://smart-doc-backend-h4mt.onrender.com/api`)
- **Backend/Router**: Render autoDeploy on push (Singapore) — set `NEON_DATABASE_URL`, `QDRANT_HOST/API_KEY`, `R2_*`, `JWT_SECRET` in dashboard
- **Langfuse Cloud**: set `LANGFUSE_PUBLIC_KEY=pk-lf-...` / `SECRET=sk-lf-...` (cloud.langfuse.com) — no-op when empty
- **SSO prod**: currently `SSO_OIDC_ENABLED=false` on Render (localhost Keycloak not reachable). Enable with `ISSUER=https://smartdoc-keycloak.onrender.com/realms/smartdoc` after Keycloak service healthy

## 📊 Performance Metrics

| Metric | Value |
|--------|-------|
| Retrieval Accuracy (keyword) | 9.68%–96.8% (varies by document) |
| Retrieval Accuracy (semantic) | Measured via cosine similarity |
| Hallucination Rate | 3.2%–9.7% (1-3 cases per 31 questions) |
| Avg Latency | ~1.9s (production) |
| P95 Latency | ~2.7s (production) |
| Automated Tests | backend 291/291, chat 43/43, agent 61/61, llm-router 80/80, eval grader 26/26, supply-chain api 9/9, frontend tsc 0 errors |
| Evaluation Dataset | 31 Vietnamese legal questions |
| Frontend | https://smart-doc-chatbot.pages.dev (Cloudflare Pages) |
| Backend | https://smart-doc-backend-h4mt.onrender.com (Render, Singapore) |

## 🧪 Testing

```bash
# Backend tests
cd backend && mvn test

# Frontend tests
cd frontend && npm test

# Load test (100 users)
python scripts/load_test.py --users 100 --duration 60

# Eval pipeline
python eval/eval.py --base-url http://localhost:8080/api --token $JWT --document-id 1 --questions eval/questions.json
```

## 📁 Project Structure

```
Smart-Document-Chatbot/
├── backend/              # Spring Boot API — Port 8080 (291 tests; ChatDedupService, ChatDlqService, SseStreamManager)
│   ├── src/main/java/    # Java source (controllers, CRAG, security, services)
│   ├── src/test/         # Unit + Flyway integration tests (incl. chat module 43 tests)
│   └── src/main/resources/db/migration/  # Flyway migrations V1..V15 (V15 drops n8n analytics)
├── frontend/             # React + TypeScript — Port 80 / 5173 (tsc 0 errors; Agent Mode default ON)
│   ├── src/              # Components, pages (ChatPage agentMode=true), contexts, services
│   ├── public/_redirects # SPA fallback for Cloudflare Pages
│   ├── wrangler.toml     # Pages project smart-doc-chatbot
│   └── dist/             # Vite build output
├── agent/                # Python LangGraph agent — Port 9000 (61 tests; main.py 1424→254 dòng, `uvicorn main:app`)
│   ├── routers/          # health, chat, hitl, a2a, mcp, actions, memory, admin
│   └── state.py          # Shared agent state models
├── llm-router/           # Python FastAPI LLM Router & Gateway — Port 8001 (80 tests)
├── supply-chain-module/  # Deterministic supply chain API tools — Port 8020 (Dockerfile single port 8020; 9 api tests)
│   └── _archive/         # Archived Streamlit dashboard (dashboard_app.py)
├── eval/                 # Evaluation pipeline (grader 26 tests, 31 Q, LLM judge)
│   └── tests/            # test_grader.py
├── docker/               # Docker Compose (prod/dev/local/monitoring) + Keycloak
├── render.yaml           # Render blueprint (backend, router, agent, keycloak, supply-chain)
├── .github/workflows/    # CI/CD + Pages auto deploy
├── docs/                 # Architecture ADRs, operational runbooks, fine-tuning guides
│   └── reports/          # Audit & planning reports (PLAN_HYBRID_PROD, AUDIT_REPORT, etc.)
└── scripts/              # Load test, benchmark, smoke test scripts (cleaned; no n8n-workflows/, test-results/, ipynb/mlruns)
```

## 🔧 Configuration (hybrid)

| Variable | Description | Default (local) | Prod (Render/Pages) |
|----------|-------------|---------|-----|
| `LLM_BASE_URL` | LLM Router URL | `http://localhost:8001` | `https://smart-doc-llm-router.onrender.com` (fromService) |
| `AGENT_BASE_URL` | Agent Service URL | `http://localhost:9000` | `http://agent:9000` (internal network) |
| `SUPPLY_CHAIN_API_URL` | Supply Chain API URL | `http://localhost:8020` | `http://supply-chain:8020` (internal network) |
| `VITE_API_URL` | Frontend → Backend | `/api` (vite proxy) | `https://smart-doc-backend-h4mt.onrender.com/api` |
| `CORS_ALLOWED_ORIGINS` | Allowed origins | `http://localhost:5173,http://localhost:3000` | `https://smart-doc-chatbot.pages.dev` |
| `LANGFUSE_*` | Langfuse Cloud | empty (no-op) | `pk-lf-...`/`sk-lf-...` `https://cloud.langfuse.com` |
| `SSO_OIDC_*` | Keycloak SSO | `http://localhost:8180/realms/smartdoc` (dev) | `false` on Render until `smartdoc-keycloak.onrender.com` ready |
| `JWT_SECRET` | JWT signing key | (required, `openssl rand -base64 48`) | same, sync:false |
| `NEON_DATABASE_URL` | Neon PG | `jdbc:postgresql://localhost:5432/smart_doc_chatbot` | `...neon.tech?sslmode=require` |

## 📚 Documentation

### Core Guides & Architecture
- [Production Guide](docs/PRODUCTION_GUIDE.md) — Production architecture, security runbooks, deployment
- [Agent Architecture](docs/agent_architecture.md) — Multi-agent LangGraph workflow & HITL design
- [Architecture Decision Records (ADRs)](docs/adr/0001-security-boundaries.md) — Security boundaries, supply chain routing, fallback strategies
- [Evaluation Guide](docs/EVALUATION.md) — Test dataset, metrics (keyword/semantic), LLM judge
- [Observability Guide](docs/OBSERVABILITY.md) — Distributed tracing with Langfuse across Spring & Python
- [Langfuse Integration](docs/LANGFUSE_INTEGRATION.md) — Phase 2 Langfuse integration details
- [Performance & Benchmarks](docs/PERFORMANCE.md) — Latency, throughput, and local vs. cloud benchmarks
- [Fine-Tuning Guide](docs/FINE_TUNE_GUIDE.md) — MLX / LoRA fine-tuning and dataset preparation
- [Disaster Recovery Runbook](docs/DR_RUNBOOK.md) — Incident response and recovery procedures
- [API Documentation](http://localhost:8080/api/swagger-ui.html) — OpenAPI / Swagger interactive docs

### Planning & Audit Reports
- [Hybrid Production Plan](docs/reports/PLAN_HYBRID_PROD.md) — Hybrid Cloudflare + Render architecture plan
- [Audit Report](docs/reports/AUDIT_REPORT.md) — Comprehensive security, code quality, and architecture audit
- [Checklist AI Fix](docs/reports/CHECKLIST_AI_FIX.md) — Step-by-step verification checklist
- [Production Redesign TODO](docs/reports/PRODUCTION_REDESIGN_TODO.md) — Modernization and refactoring roadmap

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing`)
5. Open a Pull Request

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

---

**Built with ❤️ for AI Engineer & Fullstack Developer interviews.**
