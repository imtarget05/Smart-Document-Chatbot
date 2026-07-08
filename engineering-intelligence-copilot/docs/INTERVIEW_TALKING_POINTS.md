# Interview Talking Points

## 1. One-Line Pitch

Built multi-service AI document copilot for engineering teams: ingest internal knowledge, retrieve grounded answers with citations, summarize test reports, and support structured 8D problem solving.

---

## 2. Current Repo Story

This repo has 3 major layers:

1. **Java Spring Boot backend**
   - auth
   - document CRUD
   - chat/session APIs
   - SSE streaming
   - gateway role for core product APIs

2. **Python FastAPI + LangGraph agent service**
   - orchestrator classifies user intent
   - specialist agents handle RAG, report generation, comparison, research, actions, engineering workflows
   - internal token protects service-to-service traffic

3. **React frontend**
   - upload documents
   - list documents
   - classic chat
   - agent chat
   - Tailwind-based UI

Supporting stack:
- PostgreSQL for transactional data
- Qdrant for vector search
- Ollama / OpenAI-compatible LLM support
- Docker Compose for local deployment
- Prometheus/Grafana for observability

---

## 3. Architecture Decisions To Explain

## Why split Java backend and Python agent?
- Java backend already good for auth, CRUD, stable API surface
- Python better for LLM ecosystem, LangGraph, agent tooling
- separation keeps AI iteration fast without destabilizing product core

## Why PostgreSQL + Qdrant?
- PostgreSQL stores users, sessions, documents, audit events
- Qdrant stores embeddings and chunk metadata
- transactional storage and semantic retrieval have different workloads

## Why agent routing?
Not every prompt needs same workflow.

Examples:
- knowledge question → retrieve chunks + grounded answer
- test report → summarize findings and failures
- engineering issue → generate 8D draft
- comparison request → compare multiple documents

This improves control, prompt quality, and debuggability.

---

## 4. RAG Flow To Describe

Use this short flow in interview:

```text
document upload
→ extract text
→ chunk content
→ generate embeddings
→ store vectors in Qdrant
→ user asks question
→ retrieve top relevant chunks
→ build grounded prompt
→ LLM answers with citations
```

Key quality controls:
- chunk metadata
- top-K retrieval
- source citations
- confidence scoring
- optional reranking

---

## 5. Agent Flow To Describe

Current agent graph:
- orchestrator
- rag
- report
- compare
- research
- action
- engineering

Simple explanation:
1. orchestrator determines intent
2. route to specialist node
3. node executes narrow workflow
4. return final answer with sources or action result

Benefit:
- cleaner prompts
- easier evaluation
- easier to add new domain agents later

---

## 6. Security / Production Points

Mention these to sound production-minded:
- JWT auth on user-facing APIs
- internal token for backend-to-agent calls
- file validation needed at upload boundary
- prompt injection mitigation needed for retrieved context
- audit logs for AI actions and sensitive events
- least-privilege for connectors and service accounts
- no hardcoded secrets in production; use env or secret manager

---

## 7. What You Improved

New work added in `engineering-intelligence-copilot/`:
- FastAPI backend skeleton
- centralized config
- health / ready / metrics endpoints
- API v1 router
- architecture plan doc
- interview talking points doc

Why this matters:
- gives clear migration path toward Python-first backend
- keeps old working code intact
- creates narrative for evolving system instead of rewriting blindly

---

## 8. Strong Answers For Common Questions

## “How do you reduce hallucination?”
- RAG with chunk-level retrieval
- strict grounding prompts
- citations in response
- confidence score / fallback when retrieval weak
- evaluation set for regression tracking

## “Why not full document in prompt?”
- token cost too high
- noisy context hurts answer quality
- chunk retrieval narrows context to relevant evidence

## “How would you scale this?”
- separate frontend, API, agent, vector DB
- async ingestion pipeline
- queue for heavy indexing jobs
- horizontal scale on stateless services
- caching for frequent retrieval patterns

## “How would you evaluate it?”
- benchmark question sets
- retrieval quality
- citation correctness
- hallucination rate
- task completion quality for 8D and report summarization
- latency and cost metrics

## “Biggest risk in production?”
- retrieval quality drift
- weak metadata and chunking
- unsafe connectors
- silent hallucinations if citations not enforced
- operational cost if model and embedding choices poorly controlled

---

## 9. 90-Second Demo Script

1. Login and open app
2. Upload engineering document or test report
3. Ask grounded question in AI Workspace
4. Show cited answer
5. Switch to report summary / 8D workflow
6. Explain multi-agent routing and Qdrant retrieval
7. Show monitoring / architecture docs if live demo limited

---

## 10. Honest Tradeoffs

Say this if asked what is unfinished:
- frontend navigation still smaller than target product
- Python-first backend migration started, not finished
- metrics endpoint currently placeholder
- evaluation UI not yet integrated end-to-end
- connectors beyond file upload still planned

This sounds stronger than pretending everything done.

---

## 11. Best Keywords To Use

Use naturally:
- RAG
- semantic retrieval
- vector database
- grounded generation
- orchestration
- LangGraph
- observability
- evaluation harness
- service boundary
- auditability
- RBAC
- ingestion pipeline
- provider abstraction