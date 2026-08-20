# LLM Router Service

FastAPI service placed between the application and the LLM backend. It exposes
Ollama-compatible endpoints used by the existing CRAG code, while the actual
inference is handled by **Cloudflare Workers AI** (primary) with **local
Ollama** as automatic fallback:

- `POST /api/chat`: routes chat requests; served by Cloudflare Workers AI when
  configured, otherwise by the simple/complex local models.
- `POST /api/embeddings`: proxies embeddings to Cloudflare Workers AI or Ollama.
- `GET /health`: reports service provider configuration status.

## Routing

The router serves **Cloudflare Workers AI** as the primary provider. Routing
still decides which configured model a request would use under the local
fallback:

1. Complex tasks (`compare`, `summarize`, `summarize_long`) → `chat_model_complex`.
2. More than 2 documents or more than 10 pages → `chat_model_complex`.
3. `confidence_score` below `ROUTER_CONFIDENCE_THRESHOLD` (default 0.7) → `chat_model_complex`.
4. Everything else (Q&A, extraction, keyword search) → `chat_model_simple`.

When `CLOUDFLARE_ACCOUNT_ID` and `CLOUDFLARE_API_TOKEN` are set, requests are
translated to the Workers AI REST API (`/accounts/{id}/ai/run/{model}`) with
the model `@cf/meta/llama-3.3-70b-instruct-fp8-fast`. Responses and streaming
are converted back to the Ollama wire format so callers never change.

## Provider fallback & circuit breaker

`FailoverProvider` tries Cloudflare first. After `CIRCUIT_BREAKER_THRESHOLD`
consecutive Cloudflare failures (default 5), it stops calling Cloudflare for 60
seconds and serves local Ollama instead, then re-arms automatically. Request
metadata and structured JSON logs record the provider actually used.

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

Every response includes a `router` object. Logs are JSON and include the
selected provider, model, reason, request ID, and latency for cost tracking.

## Configuration

Use `.env.example` at the repository root. Cloudflare credentials:

- `CLOUDFLARE_ACCOUNT_ID` / `CLOUDFLARE_API_TOKEN` — Workers AI API auth.
- `CLOUDFLARE_CHAT_MODEL` — inference model (default `@cf/meta/llama-3.3-70b-instruct-fp8-fast`).
- `CLOUDFLARE_EMBED_MODEL` — embedding model (default `@cf/baai/bge-base-en-v1.5`).
- `CIRCUIT_BREAKER_THRESHOLD` — consecutive failures before falling back (default 5).

`LOCAL_LLM_BASE_URL` points at Ollama (`http://ollama:11434` in Docker);
`LOCAL_CHAT_MODEL_SIMPLE` / `LOCAL_CHAT_MODEL_COMPLEX` select the fallback
models. When `ROUTER_INTERNAL_TOKEN` is set, callers must send it in
`X-Internal-Token` for `/api/*` routes.

Run tests from this directory:

```bash
pytest -q
```

Smoke-test against real Cloudflare from this directory:

```bash
set -a && source ../.env && set +a
uv run --python 3.12 python - <<'PY'
import asyncio
from app.config import Settings
from app.providers import FailoverProvider
from app.models import ChatRequest, RoutingContext, RouteDecision

async def main():
    p = FailoverProvider(Settings())
    resp = await p.chat(
        ChatRequest(messages=[{"role": "user", "content": "Say hello"}],
                     routing=RoutingContext()),
        RouteDecision(provider="local", model="x", reason="smoke", task_type="general"),
        "smoke",
    )
    print(resp["message"]["content"])
    await p.close()

asyncio.run(main())
PY
```
