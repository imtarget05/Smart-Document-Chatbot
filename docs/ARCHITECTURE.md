# Smart Document Chatbot — Architecture

## 1. Goal

Smart Document Chatbot helps engineering teams:
- ask grounded questions over internal knowledge
- analyze uploaded engineering documents
- summarize test reports
- generate structured 8D problem-solving drafts
- evaluate response quality and trace system behavior

System designed for:
- local demo with Ollama-backed LLMs (no external API keys)
- self-hosted deployment with PostgreSQL + Qdrant
- safe extension toward enterprise data connectors

---

## 2. High-Level Architecture

```text
React Frontend (Vite + TypeScript + TanStack Query)
  ├─ Dashboard
  ├─ Classic / Agent Chat
  ├─ Knowledge Base
  ├─ Data Sources
  ├─ 8D Cases
  ├─ Evaluation Lab
  ├─ Audit Logs
  ├─ Settings
  └─ Admin Users
        │
        ▼
Java Spring Boot Backend  (/api, context-path)
  ├─ Auth / JWT RBAC (ADMIN, ENGINEER, VIEWER)
  ├─ Document Ingestion + Storage
  ├─ Chat + SSE Streaming
  ├─ 8D Case Manager
  ├─ Evaluation API
  ├─ AOP Audit Logging
  └─ Actuator observability
        │
        ▼
Python FastAPI Agent Service  (LangGraph)
  ├─ Orchestrator (intent routing)
  ├─ Specialist agents: RAG, Report, Compare, Research, Action, Engineering
  ├─ Agentic CRAG loop (retrieval → confidence eval → reformulation)
  ├─ Connectors: Gmail, Google Drive, SharePoint, Slack
  └─ Memory (short/long-term)
        │
        ├─ PostgreSQL
        ├─ Qdrant (vector store)
        ├─ LLM Router → Ollama (chat + embeddings)
        ├─ n8n (workflow automation, optional)
        └─ Prometheus / Grafana
```

---

## 3. Main Backend Modules

### `backend/` — Java Spring Boot 3
- `controller/`: REST endpoints (auth, documents, chat/SSE, 8D cases, evaluation, datasources, audit) + WebSocket
- `service/`: business logic — chat, document, retrieval, web search (Tavily), query reformulation, CRAG
- `config/`: security (JWT filter), CORS, WebSocket, CRAG/Tavily settings
- `entity/` + `repository/`: JPA entities and Spring Data repositories
- `exception/`: global exception handler
- `util/`: helpers (LlmConfig, JWT)

### `agent/` — Python FastAPI + LangGraph
- `agents/`: 6 specialist agents + orchestrator
- `graph/`: LangGraph StateGraph workflow (CRAG loop: retrieval → confidence → reformulate → parallel re-retrieval → rerank)
- `tools/`: Qdrant hybrid search, Tavily web search, report generation
- `memory/`: short/long-term memory, context summarizer, VI-EN language handler
- `connectors/`: Gmail, Google Drive, SharePoint, Slack
- `streaming/`: SSE event helpers
- `benchmark/`, `eval_framework/`: evaluation harness + MLflow tracking

Endpoint groups (across backend + agent service):
- `/api/auth` — login / register / JWT
- `/api/documents` — upload / list / get / delete / ETL state
- `/api/chat` — ask, ask-stream (SSE), history, sessions, WebSocket
- `/api/eight-d` — 8D case CRUD + step/status updates
- `/api/evaluation` — evaluation runs (API-stored)
- `/api/datasources` — connector sources
- `/api/admin` — users, audit logs
- `/api/audit` — audit log queries + stats

---

## 4. Data Flow

## 4.1 Ingestion Flow

```text
Upload / Source Sync
→ validate file and source metadata
→ extract text
→ normalize content
→ split into chunks
→ enrich chunk metadata
→ create embeddings
→ upsert into Qdrant
→ persist document record in PostgreSQL
→ emit ingestion audit log
```

Metadata per chunk should include:
- document_id
- title
- source_type
- source_uri
- version
- uploaded_by
- chunk_index
- content_hash
- tags
- created_at

## 4.2 Question Answering Flow

```text
User prompt
→ classify task or use selected mode
→ optional safety checks
→ retrieve top-K chunks
→ optional rerank
→ assemble grounded context
→ call LLM with strict citation rules
→ return answer + citations + metadata
→ store audit entry
```

## 4.3 8D Flow

```text
User enters incident / defect context
→ system structures D1–D8 fields
→ retrieve similar incidents / reports
→ generate draft containment and root-cause hypotheses
→ propose corrective / preventive actions
→ save editable case timeline
```

---

## 5. Storage Design

### PostgreSQL
Use for transactional data:
- users
- roles
- documents
- document_versions
- chat_sessions
- chat_messages
- agent_runs
- eight_d_cases
- evaluation_runs
- audit_logs

### Qdrant
Use for semantic retrieval:
- document chunks
- incident embeddings
- test report chunks
- optional evaluation reference chunks

---

## 6. Safety Model

### Input Safety
- extension allowlist
- MIME check
- file size limit
- content hash dedup
- prompt injection heuristics
- connector allowlist

### Output Safety
- require citations for grounded claims
- mark low-confidence answers
- no silent tool side effects
- audit log for sensitive operations

### Tool Safety
- explicit tool schemas
- bounded timeout
- retry policy
- dry-run mode for risky actions

---

## 7. Deployment Strategy

### Local Demo
- Java Spring Boot backend + Python FastAPI agent service (LangGraph)
- React frontend
- PostgreSQL
- Qdrant
- Ollama via LLM router
- Docker Compose (`docker/docker-compose.dev.yml`)

### Self-Hosted
- production Docker Compose (`docker/docker-compose.yml`)
- Kubernetes + ArgoCD GitOps under `k8s/`
- environment-driven configuration
- reverse proxy in front of frontend/backend

---

## 8. Interview Talking Points

Strong points to present:
1. Dual storage model: PostgreSQL for transactions, Qdrant for semantic retrieval
2. Agent mode separation: Q&A vs analysis vs summary vs 8D
3. Grounded responses with citation discipline
4. Safe ingestion path with validation and dedup
5. Evaluation-first mindset for AI quality
6. Auditability and observability from early architecture stage
7. Provider abstraction to support mock, Ollama, OpenAI-compatible backends

Tradeoffs to mention:
- started with a working monolith stack and evolved it incrementally (agentic CRAG, RBAC, eval harness) instead of rewriting
- Prometheus scrape config exists (`docker/monitoring`) but the Actuator metrics endpoint is not yet fully exposed
- local Ollama models keep the stack self-contained, but answer quality depends on model size
- frontend can evolve independently from backend because the API boundary is explicit

---

## 9. Current Status

Implemented now:
- Java Spring Boot backend (auth, documents, chat/SSE, RBAC, audit logging)
- Python FastAPI agent service with LangGraph multi-agent orchestration
- agentic CRAG loop (confidence eval, query reformulation, parallel re-retrieval, web fallback)
- React frontend (Vite + TypeScript + TanStack Query)
- production Docker Compose, Kubernetes/ArgoCD, GitHub Actions CI/CD
- RAG evaluation harness (`eval/`, `agent/benchmark`)

Next build steps:
1. wire evaluation API to the eval pipeline end-to-end
2. extend connectors beyond Gmail / Google Drive / SharePoint / Slack
3. expose Actuator metrics endpoint for Prometheus
4. tune Grafana dashboards and alert thresholds
6. evaluation endpoints
7. frontend pages on existing app