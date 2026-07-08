# Engineering Intelligence Copilot Architecture

## 1. Goal

Engineering Intelligence Copilot helps engineers:
- ask grounded questions over internal knowledge
- analyze uploaded engineering documents
- summarize test reports
- generate structured 8D problem-solving drafts
- evaluate response quality and trace system behavior

System designed for:
- local demo with mock or Ollama-backed LLMs
- self-hosted deployment with PostgreSQL + Qdrant
- safe extension toward enterprise data connectors

---

## 2. High-Level Architecture

```text
React Frontend
  ├─ Dashboard
  ├─ AI Workspace
  ├─ Knowledge Base
  ├─ Data Sources
  ├─ 8D Cases
  ├─ Evaluation Lab
  ├─ Audit Logs
  └─ Settings
        │
        ▼
FastAPI Backend
  ├─ Auth / RBAC
  ├─ Document Ingestion
  ├─ Retrieval + Citations
  ├─ Agent Orchestrator
  ├─ 8D Case Manager
  ├─ Evaluation Runner
  ├─ Audit Logging
  └─ Observability
        │
        ├─ PostgreSQL
        ├─ Qdrant
        └─ LLM / Embedding Provider
```

---

## 3. Main Backend Modules

### `app/main.py`
FastAPI app entrypoint.
Responsibilities:
- app bootstrapping
- CORS
- lifecycle hooks
- `/health`, `/ready`, `/metrics`
- API router mount

### `app/core`
Shared app config.
Responsibilities:
- environment variable loading
- runtime settings
- feature flags
- provider selection

### `app/api/v1`
REST API layer.
Planned endpoint groups:
- `/auth`
- `/documents`
- `/chat`
- `/agents`
- `/cases`
- `/evaluations`
- `/audit-logs`
- `/settings`

### `app/ingestion`
Document pipeline.
Responsibilities:
- file validation
- text extraction
- chunking
- metadata enrichment
- deduplication
- embedding + vector indexing

### `app/agents`
Agent orchestration layer.
Planned agent modes:
- Knowledge Q&A
- Document Analysis
- Test Report Summary
- 8D Problem Solver

### `app/services`
Business logic.
Responsibilities:
- retrieval orchestration
- citation formatting
- LLM invocation
- source connector execution
- case workflow logic

### `app/tools`
Safe tool execution layer.
Responsibilities:
- schema validation
- timeout control
- audit log emission
- side-effect boundaries

### `app/evaluations`
Offline + online evaluation logic.
Responsibilities:
- benchmark dataset execution
- scoring
- comparison reports
- regression detection

### `app/observability`
Telemetry and logging.
Responsibilities:
- metrics
- structured logs
- tracing hooks
- audit trail integration

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
- FastAPI backend
- React frontend
- PostgreSQL
- Qdrant
- optional Ollama
- mock provider fallback

### Self-Hosted
- Docker Compose first
- Kubernetes later
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
- started with minimal API skeleton to keep iteration fast
- metrics endpoint placeholder before full Prometheus integration
- mock provider fallback improves demo reliability but not answer quality
- frontend can evolve independently from backend because API boundary is explicit

---

## 9. Current Status

Implemented now:
- new project structure
- FastAPI app skeleton
- central config
- API v1 root router
- architecture and implementation planning docs

Next build steps:
1. auth + RBAC
2. document ingestion API
3. retrieval service
4. agent mode endpoints
5. 8D workflow persistence
6. evaluation endpoints
7. frontend pages on existing app