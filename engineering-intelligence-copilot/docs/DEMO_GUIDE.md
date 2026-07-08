# Demo Guide

## 1. Demo Goal

Show clear end-to-end story:

1. engineering knowledge ingestion
2. grounded Q&A with citations
3. agent-based workflow selection
4. 8D problem-solving support
5. production-minded architecture

If full stack not running, use docs + code walkthrough.

---

## 2. Best Demo Order

### Option A — Live System Demo
Use when backend, frontend, Qdrant, and DB running.

1. Open app
2. Login
3. Show document upload
4. Ask grounded question
5. Show cited answer
6. Switch to specialized workflow:
   - document analysis
   - test report summary
   - 8D problem-solving
7. Explain architecture
8. End with observability / audit / security notes

### Option B — Interview Code Demo
Use when stack only partially running.

1. Show current repo structure
2. Show existing Java backend + Python agent split
3. Show new Python-first backend scaffold in `engineering-intelligence-copilot/backend/`
4. Open:
   - `docs/ARCHITECTURE.md`
   - `docs/INTERVIEW_TALKING_POINTS.md`
   - `docs/SECURITY.md`
5. Explain flows and tradeoffs
6. Mention verified FastAPI entrypoint import works

---

## 3. Demo Narrative

Use this short story:

> Engineering teams have too many internal docs, test reports, and incident notes. This system ingests those sources, indexes them into vector search, and routes user requests to specialist AI workflows such as grounded Q&A, test report summarization, and 8D problem solving. I designed it with clear service boundaries, retrieval grounding, evaluation hooks, and production controls like RBAC and audit logging.

---

## 4. Screens / Files To Show

## Existing Repo
- Java backend for core product APIs
- Python agent layer for orchestration
- React frontend for upload + chat
- Docker Compose for infra

## New Work Added
- `engineering-intelligence-copilot/backend/app/main.py`
- `engineering-intelligence-copilot/backend/app/core/config.py`
- `engineering-intelligence-copilot/backend/app/api/v1/router.py`
- `engineering-intelligence-copilot/docs/ARCHITECTURE.md`
- `engineering-intelligence-copilot/docs/INTERVIEW_TALKING_POINTS.md`
- `engineering-intelligence-copilot/docs/SECURITY.md`

---

## 5. What To Say At Each Step

### Step 1 — Problem
“Engineering knowledge is fragmented across uploaded files, reports, and incident records. Users need grounded answers, not generic chatbot responses.”

### Step 2 — Architecture
“I split transactional data and semantic retrieval: PostgreSQL for system state, Qdrant for embeddings. Java handles stable product APIs, Python handles faster AI iteration.”

### Step 3 — Ingestion
“Documents go through validation, extraction, chunking, metadata enrichment, embedding, and vector indexing.”

### Step 4 — Retrieval
“At query time, system retrieves top relevant chunks, builds grounded context, and requires citations in output.”

### Step 5 — Agent Routing
“Different prompts need different workflows, so orchestrator routes between knowledge Q&A, analysis, report summary, and 8D support.”

### Step 6 — Safety
“I treat retrieved text as untrusted input, enforce role-based permissions, and log sensitive actions.”

### Step 7 — Evolution
“I started Python-first backend scaffold for long-term consolidation without breaking existing working services.”

---

## 6. Suggested 90-Second Version

1. “This project is AI copilot for engineering teams.”
2. “It combines React frontend, backend APIs, vector retrieval, and specialized AI workflows.”
3. “Knowledge goes through ingestion into Qdrant with metadata.”
4. “User questions trigger retrieval, grounded prompting, and cited answers.”
5. “More complex tasks route to specialist agents like report summary or 8D problem solving.”
6. “I also planned for security, auditability, and evaluation instead of treating this as only prompt engineering.”
7. “To align with Python-first target architecture, I added new FastAPI scaffold and docs for migration path.”

---

## 7. Fallback If Live Demo Breaks

Say this calmly:

- “Core architecture and service boundaries are complete.”
- “Current repo already has Java backend, Python agent layer, and frontend.”
- “I also added Python-first backend skeleton to support migration.”
- “If live infra is unavailable, I can still walk through ingestion flow, retrieval flow, agent routing, and security model from code and docs.”

Then show:
- `docs/ARCHITECTURE.md`
- `docs/INTERVIEW_TALKING_POINTS.md`
- `docs/SECURITY.md`

---

## 8. Common Questions During Demo

### “How do you prevent hallucination?”
Use retrieval grounding + citations + evaluation datasets.

### “Why Qdrant?”
Efficient semantic retrieval with metadata filtering.

### “Why not keep everything in Java?”
Java good for core APIs; Python ecosystem faster for agent experimentation and LLM tooling.

### “What is unfinished?”
Frontend feature expansion, full ingestion connectors, 8D persistence, integrated evaluation UI, full Docker Compose for new Python-first stack.

---

## 9. Interview Win Conditions

Good demo if interviewer understands:
- you know full-stack architecture
- you understand RAG beyond buzzwords
- you think about security and evaluation
- you can evolve legacy/mixed systems instead of rewriting blindly