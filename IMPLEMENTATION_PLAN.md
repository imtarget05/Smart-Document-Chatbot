# Engineering Intelligence Copilot — Implementation Plan

## 1. Repository Assessment

### Current State
| Component | Technology | Status |
|-----------|-----------|--------|
| Backend | Java Spring Boot | Working — auth, doc CRUD, chat, RAG, SSE streaming |
| Agent Service | Python FastAPI + LangGraph | Working — orchestrator → 6 specialist agents (RAG, Report, Compare, Research, Action, Engineering) |
| Frontend | React + Vite + Tailwind | Working — basic chat, upload, doc list, agent chat |
| Vector DB | Qdrant (Docker) | Configured |
| Database | PostgreSQL | Configured |
| LLM | Ollama / OpenAI-compatible | Configured via env |
| Monitoring | Prometheus + Grafana | Docker Compose defined |
| Infra | Docker Compose, k8s manifests | Partial |

### Key Gaps vs Spec
1. **Backend language**: Spec requires Python FastAPI; current is Java Spring Boot
2. **Frontend pages**: Only chat + upload; missing Dashboard, Knowledge Base, Data Sources, 8D Cases, Evaluation Lab, Audit Logs, Settings
3. **8D Problem Solving**: Agent has engineering node but no structured 8D workflow/persistence
4. **Test Report Summarization**: No dedicated agent mode
5. **Data Ingestion Pipeline**: Basic file upload only; no API/DB/SharePoint sources
6. **Evaluation System**: eval/ directory exists but not integrated into UI
7. **Audit Logs**: No structured audit trail
8. **RBAC**: Basic JWT auth, no role-based access
9. **Memory Management**: No tiered memory (conversation/preference/long-term)
10. **CI/CD**: No GitHub Actions workflow
11. **Documentation**: Missing ARCHITECTURE.md, SECURITY.md, DEMO_GUIDE.md, SELF_HOSTING_GUIDE.md, INTERVIEW_TALKING_POINTS.md

## 2. Architecture Decision

**Approach**: Build new Python FastAPI backend as primary backend per spec. Existing Java backend preserved in `legacy-backend/` for reference. Existing Python agent patterns reused and expanded.

```
┌─────────────────────────────────────────────────────────┐
│                    Frontend (React)                       │
│  Dashboard │ AI Workspace │ KB │ Sources │ 8D │ Eval │ Audit │
└──────────────────────┬──────────────────────────────────┘
                       │ REST + SSE
┌──────────────────────▼──────────────────────────────────┐
│              Python FastAPI Backend                       │
│  ┌─────────┐ ┌──────────┐ ┌──────────┐ ┌────────────┐  │
│  │ Auth/   │ │ Ingestion│ │ Chat/    │ │ Evaluation │  │
│  │ RBAC    │ │ Pipeline │ │ Agent    │ │ Framework  │  │
│  └─────────┘ └──────────┘ └──────────┘ └────────────┘  │
│  ┌─────────┐ ┌──────────┐ ┌──────────┐ ┌────────────┐  │
│  │ 8D Case │ │ Audit    │ │ Tools    │ │ Observa-   │  │
│  │ Manager │ │ Logger   │ │ Layer    │ │ bility     │  │
│  └─────────┘ └──────────┘ └──────────┘ └────────────┘  │
│                                                          │
│  Agent Orchestrator (LangGraph / LangChain)              │
│  ┌────────┐┌──────────┐┌────────┐┌───────┐              │
│  │Knowledge││Doc       ││Test Rpt││8D     │              │
│  │Q&A     ││Analyzer  ││Summary ││Solver │              │
│  └────────┘└──────────┘└────────┘└───────┘              │
└──────────────────────┬──────────────────────────────────┘
          ┌────────────┼────────────┐
          ▼            ▼            ▼
    ┌──────────┐ ┌──────────┐ ┌──────────┐
    │PostgreSQL│ │  Qdrant  │ │  Redis   │
    │          │ │          │ │(optional)│
    └──────────┘ └──────────┘ └──────────┘
```

## 3. Module Implementation Plan

### Phase 1: Core Infrastructure
- [x] Create IMPLEMENTATION_PLAN.md
- [ ] Set up new project structure
- [ ] Python FastAPI backend skeleton (config, DB, migrations)
- [ ] Auth system (JWT, RBAC: Admin/Engineer/Viewer)
- [ ] Health/ready/metrics endpoints
- [ ] Docker Compose (postgres, qdrant, backend, frontend)
- [ ] .env.example

### Phase 2: Data & Ingestion
- [ ] Document model + CRUD API
- [ ] File upload with validation (extension, MIME, size, magic bytes)
- [ ] Text extraction (PDF, DOCX, TXT, MD, CSV, JSON)
- [ ] Chunking with metadata enrichment
- [ ] Embedding + Qdrant indexing
- [ ] Duplicate detection (content_hash)
- [ ] Ingestion status tracking
- [ ] REST API source connector
- [ ] Database source connector (read-only SQL)
- [ ] SharePoint mock connector
- [ ] Re-index and delete with vector cleanup

### Phase 3: RAG & Agent
- [ ] LLM provider abstraction (Ollama, OpenAI-compatible, mock)
- [ ] Embedding provider abstraction
- [ ] RAG pipeline (retrieve → rerank → cite)
- [ ] Knowledge Q&A Agent
- [ ] Document Analysis Agent
- [ ] Test Report Summarization Agent
- [ ] 8D Problem Solving Agent
- [ ] Tool layer with safety (schema, validation, timeout, logging)
- [ ] Memory management (conversation, preference, long-term)
- [ ] Citation builder with source tracking
- [ ] Prompt injection detection

### Phase 4: 8D & Evaluation
- [ ] 8D Case model + CRUD + timeline
- [ ] 8D AI suggestion endpoint
- [ ] Evaluation dataset upload
- [ ] Evaluation runner (rule-based metrics)
- [ ] Evaluation comparison
- [ ] Audit log system

### Phase 5: Frontend
- [ ] Project setup (React, TypeScript, Vite, Tailwind, shadcn/ui)
- [ ] Sidebar navigation
- [ ] Dashboard page
- [ ] AI Workspace (chat + agent modes + sources panel)
- [ ] Knowledge Base page
- [ ] Data Sources page
- [ ] 8D Cases page (list, detail, wizard, AI suggest)
- [ ] Evaluation Lab page
- [ ] Audit Logs page
- [ ] Settings page
- [ ] Auth flow (login, register, RBAC)

### Phase 6: Quality & Docs
- [ ] Backend unit tests
- [ ] Backend API tests
- [ ] Frontend component tests
- [ ] Sample data (docs, test reports, incidents, 8D cases, eval dataset)
- [ ] CI workflow (.github/workflows/ci.yml)
- [ ] ARCHITECTURE.md
- [ ] SECURITY.md
- [ ] API.md
- [ ] DEMO_GUIDE.md
- [ ] SELF_HOSTING_GUIDE.md
- [ ] INTERVIEW_TALKING_POINTS.md
- [ ] README.md update

## 4. Data Flow

```
User uploads file
→ Backend validates (ext, MIME, size, magic bytes)
→ Text extraction (PyPDF2/python-docx/etc.)
→ Cleaning + metadata enrichment
→ Recursive chunking (configurable overlap)
→ content_hash dedup check
→ Embedding (configurable provider)
→ Qdrant upsert with metadata
→ PostgreSQL document record update (status: completed)
→ Ingestion report generated

User asks question
→ Intent classification
→ Agent mode selection (or user override)
→ Query validation + prompt injection check
→ Vector retrieval (Qdrant semantic search, top-K)
→ Optional reranking
→ Context assembly (chunked, not full docs)
→ LLM generation with grounding instructions
→ Citation extraction + validation
→ Response + sources + metadata returned
→ Audit log entry created
```

## 5. Technical Risks

| Risk | Mitigation |
|------|-----------|
| No local LLM model downloaded | Mock LLM provider returns template responses for demo |
| Large scope vs time | Prioritize working e2e flow over feature completeness |
| Qdrant not running | Graceful fallback with clear error messages |
| Python dependency conflicts | Pin versions in requirements.txt |
| Frontend complexity | Use shadcn/ui for consistent components |

## 6. Acceptance Checklist

- [ ] `docker compose up --build` starts all services
- [ ] Health endpoint returns 200
- [ ] Demo user can login
- [ ] Upload document → ingestion completes
- [ ] Ask question → grounded answer with citations
- [ ] Document Analysis mode works
- [ ] Test Report Summary mode works
- [ ] 8D case CRUD + AI suggestion works
- [ ] Evaluation run produces metrics
- [ ] Audit logs show activity
- [ ] No hardcoded secrets
- [ ] Tests pass
- [ ] All documentation files exist