# LLM Router Service

FastAPI service placed between the application and LLM backends. It exposes the
Ollama-compatible endpoints used by the existing CRAG code:

- `POST /api/chat`: routes chat and vision requests.
- `POST /api/embeddings`: proxies embeddings to Ollama without routing.
- `GET /health`: reports service and provider configuration status.

## Routing order

1. Any image, scan, Ollama `images` value, or OpenAI-style image content routes to GPT-4o.
2. More than 2 documents, more than 10 pages, `compare`, or `summarize_long` routes to Claude.
3. Remaining Q&A, field extraction, and keyword tasks route to local Llama.
4. Local requests taking more than 3 seconds, failing before output, or carrying confidence below 0.7 escalate to Claude.

Vision always wins over all other criteria. Streaming timeout means time to the
first token; escalation after partial output is intentionally disabled to avoid
mixing responses from two models.

## Request metadata

Existing Ollama requests continue to work. Callers can add optional metadata:

```json
{
  "model": "ignored-by-router",
  "messages": [{"role": "user", "content": "Compare these contracts"}],
  "stream": false,
  "routing": {
    "task_type": "compare",
    "document_count": 3,
    "page_count": 24,
    "confidence_score": 0.82,
    "has_image": false,
    "attachments": ["contract-a.pdf", "contract-b.pdf"],
    "request_id": "optional-correlation-id"
  }
}
```

Every response includes a `router` object. Logs are JSON and include the selected
provider, model, reason, escalation flag, request ID, and latency for cost tracking.

## Configuration

Use `.env.example` at the repository root. `ANTHROPIC_API_KEY` is required for
complex and escalated tasks; `OPENAI_API_KEY` is required for visual requests.
When `ROUTER_INTERNAL_TOKEN` is set, callers must send it in `X-Internal-Token`.

Run tests from this directory:

```bash
pytest -q
```
