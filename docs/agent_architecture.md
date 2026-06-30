# Agent Architecture and Demo Workflow

This project uses the Python LangGraph Agent Service as the primary AI workflow.
Spring Boot remains the enterprise gateway for auth, API contracts, document
management, rate limiting, and persistence.

## Primary Flow

```text
Frontend
  -> Spring Boot API
  -> Python Agent Service
  -> LangGraph Orchestrator
  -> Specialist Agent
  -> Tools / Qdrant / LLM Router
```

Spring Boot responsibilities:

- JWT authentication and user isolation.
- Document upload, metadata, and lifecycle management.
- API gateway proxy for `/agent/*` with `X-Internal-Token`.
- Classic `/chat/ask` and `/chat/ask-stream` compatibility.

Python Agent Service responsibilities:

- LangGraph intent routing and specialist agents.
- RAG retrieval, report generation, comparison, research, actions, and engineering analysis.
- Connector ingestion from Google Drive, Gmail, Slack, and SharePoint/mock SharePoint.
- Long-term agent session memory in PostgreSQL.

## Connector Ingestion Flow

```text
Google Drive / Gmail / Slack / SharePoint
  -> Connector fetch_documents()
  -> IngestionAgent
  -> ConnectorIngestionPipeline
  -> chunk text
  -> embed with LLM Router / Ollama-compatible embeddings
  -> upsert chunks into Qdrant
  -> return collection_id
  -> RAG / Engineering Agent can search that collection_id
```

The connector endpoint is:

```http
POST /api/agent/connector/ingest
Authorization: Bearer <jwt>
Content-Type: application/json
```

Example SharePoint mock ingestion:

```json
{
  "source": "sharepoint",
  "params": {
    "mock": true
  }
}
```

The response includes `collection_id`. Pass that value as a document id to
`/api/agent/invoke`.

## Engineering Report Workflow

The `EngineeringAnalysisAgent` handles test reports, failure summaries,
root-cause analysis, corrective actions, and 8D-style reports.

Demo scenario:

1. Ingest the mock SharePoint engineering test report.
2. Copy the returned `collection_id`.
3. Ask:

```text
Summarize failures and generate an 8D report.
```

4. Use `intentOverride: "engineering"` for deterministic demos, or let the
   orchestrator route automatically.
5. The agent retrieves evidence from Qdrant and returns a structured 8D report
   with citations.

Example invoke payload through Spring Boot:

```json
{
  "query": "Summarize failures and generate an 8D report.",
  "sessionId": "demo-8d",
  "documentIds": ["conn_sharepoint_<hash>"],
  "intentOverride": "engineering"
}
```

## Agent Evaluation

Classic RAG evaluation remains in `eval/eval.py` for `/chat/ask`.
Agent-specific evaluation is in `eval/agent_eval.py` for `/agent/invoke`.

Metrics produced:

- intent routing accuracy
- retrieval accuracy
- answer completeness
- hallucination rate
- latency
- source citation rate

Run through Spring Boot:

```bash
python eval/agent_eval.py \
  --base-url http://localhost:8080/api \
  --token <jwt> \
  --document-ids <collection_id>
```

Run directly against the Python agent service:

```bash
python eval/agent_eval.py \
  --base-url http://localhost:9000 \
  --direct-agent \
  --internal-token <INTERNAL_SERVICE_TOKEN> \
  --document-ids <collection_id>
```

## Interview Positioning

Use this distinction when explaining the Java and Python flows:

- Java Spring Boot is the product/API layer: security, ownership, document management,
  stable user-facing APIs, and compatibility endpoints.
- Python LangGraph is the AI agent layer: intent routing, specialist agents,
  tool usage, connector ingestion, evaluation, and engineering-report workflows.

