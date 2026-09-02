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
┌─────────────────────────────────────────────────────────────────┐
│ Frontend (React + TS, Vite) → Cloudflare Pages                  │
│ smart-doc-chatbot.pages.dev  • _redirects SPA • _headers       │
└─────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼ (CORS)
┌─────────────────────────────────────────────────────────────────┐
│ Backend (Spring Boot 3.2, Render Singapore)                     │
│ JWT + CSRF + RateLimit (fail-closed) + Audit + SSO/Keycloak    │
│ Langfuse Cloud (https://cloud.langfuse.com) — no-op when off    │
└─────────────────────────────────────────────────────────────────┘
                    │                           │
              Neon PG │                           │ LLM Router (FastAPI, Render)
     (Neon 512MB+Qdrant Cloud+R2 10GB free)     │  Task Routing • Circuit breaker
                                                │
                                    ┌─────────┴─────────┐
                                    ▼                   ▼
                          ┌─────────────┐       ┌─────────────┐
                          │   Ollama    │       │  Cloudflare  │
                          │  (Local)    │       │  Workers AI  │
                          │ qwen3:8b    │       │ llama-3.3-70b│
                          └─────────────┘       └─────────────┘
Local fallback: docker-compose.dev.yml (pgvector:5434/qdrant:6333/redis:6379 + Keycloak:8180)
```

> **Note:** Production chat uses **PostgreSQL lexical search**. Qdrant hybrid search + BM25 + RRF is available in the experimental Python agent service only. **SSO prod disabled until Keycloak public URL ready** (`SSO_OIDC_ENABLED=false` on Render).

## ✨ Key Features

### 🧠 AI/ML Capabilities
- **Corrective RAG (CRAG)**: Auto-corrects low-confidence retrievals
- **5-Layer Hallucination Defense**: Confidence gate → Lexical support → Retrieval scoring → Abstention → Eval heuristic
- **Vietnamese Legal NLP**: Điều/Khoản/Điểm structure detection
- **Multi-LLM Support**: Ollama (local) + Cloudflare Workers AI (cloud)
- **Prompt Injection Defense**: Blocks direct, role-play, and homoglyph attacks

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
- **Database Migrations** (Flyway 14)
- **Monitoring** (Langfuse Cloud + Prometheus + Grafana)
- **Automated Testing** (254 backend + 54 frontend tests)

## ⚠️ Known Limitations

- **Retrieval accuracy varies significantly by document** (9.68%–96.8% across 5 production runs). The median is ~71%.
- **Hallucination rate is 3-10%**, not 0%. Every eval run shows 1-3 hallucination cases.
- **Production chat uses PostgreSQL lexical search**, not Qdrant hybrid search. Qdrant is only in the experimental Python agent service.
- **Evaluation uses keyword matching**, not semantic similarity (semantic metric added but not yet calibrated).
- **SSO disabled on Render until Keycloak public URL ready** — local Keycloak `http://localhost:8180` works, prod `SSO_OIDC_ENABLED=false` (enable with `https://smartdoc-keycloak.onrender.com/realms/smartdoc`).

## ✅ What's Genuinely Implemented

- Full-stack app: Spring Boot + React + TypeScript + Python
- JWT auth, CSRF, RBAC, account lockout, audit logging
- CRAG corrective loop with query reformulation
- Hybrid search + BM25 + RRF (Python agent)
- Docker Compose with 11 services, healthchecks, monitoring
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
- Java 17+
- Node.js 20+
- Docker & Docker Compose
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
# Then create realm/client: see PLAN_HYBRID_PROD.md
```

### 3. Start Backend
```bash
cd backend
export JAVA_HOME=/opt/homebrew/opt/openjdk@17
mvn spring-boot:run
```

### 4. Start Frontend
```bash
cd frontend
npm install
npm run dev
```

### 5. Access
- Frontend local: http://localhost:3000 — prod: https://smart-doc-chatbot.pages.dev
- Backend local: http://localhost:8080/api — prod: https://smart-doc-backend-h4mt.onrender.com/api
- API Docs: http://localhost:8080/api/swagger-ui.html — prod: https://smart-doc-backend-h4mt.onrender.com/api/swagger-ui.html
- Keycloak local: http://localhost:8180 (admin/admin, realm smartdoc)

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
| Automated Tests | 308+ passing (254 backend + 54 frontend) |
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
├── backend/              # Spring Boot API (254 tests)
│   ├── src/main/java/    # Java source
│   ├── src/test/         # Unit + Flyway integration (local fallback)
│   └── src/main/resources/db/migration/  # Flyway V1..V14
├── frontend/             # React + TypeScript (54 tests)
│   ├── src/              # components, pages, context
│   ├── public/_redirects # SPA fallback for Cloudflare Pages
│   ├── wrangler.toml     # Pages project smart-doc-chatbot
│   └── dist/             # vite build (VITE_API_URL prod)
├── llm-router/           # Python FastAPI LLM router (Cloudflare Workers AI)
├── agent/                # Python LangGraph agent + HITL (experimental)
├── eval/                 # Evaluation pipeline (31 Q, keyword + LLM judge)
├── docker/               # Docker Compose (prod/dev/local/monitoring) + Dockerfile.keycloak
├── render.yaml           # Render blueprint (backend, router, agent, keycloak, supply-chain)
├── .github/workflows/    # CI/CD + Pages auto deploy
├── docs/                 # Production/eval guides
├── n8n-workflows/        # Automation workflows
└── scripts/              # Load test, smoke test
```

## 🔧 Configuration (hybrid)

| Variable | Description | Default (local) | Prod (Render/Pages) |
|----------|-------------|---------|-----|
| `LLM_BASE_URL` | LLM Router URL | http://localhost:8001 | `https://smart-doc-llm-router.onrender.com` (fromService) |
| `VITE_API_URL` | Frontend → Backend | `/api` (vite proxy) | `https://smart-doc-backend-h4mt.onrender.com/api` |
| `CORS_ALLOWED_ORIGINS` | Allowed origins | `http://localhost:3000` | `https://smart-doc-chatbot.pages.dev` |
| `LANGFUSE_*` | Langfuse Cloud | empty (no-op) | `pk-lf-...`/`sk-lf-...` `https://cloud.langfuse.com` |
| `SSO_OIDC_*` | Keycloak SSO | `http://localhost:8180/realms/smartdoc` (dev) | `false` on Render until `smartdoc-keycloak.onrender.com` ready |
| `JWT_SECRET` | JWT signing key | (required, `openssl rand -base64 48`) | same, sync:false |
| `NEON_DATABASE_URL` | Neon PG | `jdbc:postgresql://localhost:5432/smart_doc_chatbot` | `...neon.tech?sslmode=require` |

## 📚 Documentation

- [Production Guide](docs/PRODUCTION_GUIDE.md)
- [Fine-Tuning Guide](docs/FINE_TUNE_GUIDE.md)
- [API Documentation](http://localhost:8080/api/swagger-ui.html)

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
