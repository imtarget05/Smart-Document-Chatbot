# Langfuse Observability — Smart Document Chatbot

Tích hợp tracing end-to-end cho luồng CRAG: mỗi request = 1 trace, gồm các
span `retrieve_chunks` → `judge_relevance` → `query_reformulate` →
`retrieve_chunks_corrective` → (`web_search`) → `generate_answer`. Trace id
được lan truyền từ Spring Boot sang llm-router (FastAPI) qua header
`X-Langfuse-Trace-Id` để 1 request hiện đầy đủ cả 2 tầng trong cùng 1 cây.

## Kiến trúc

```
Browser
  └─ Spring Boot (ChatService.runCrag)      ← Java spans
       ├─ retrieve_chunks / judge_relevance
       ├─ query_reformulate / retrieve_chunks_corrective
       ├─ web_search
       └─ LlmClient.chat ──(X-Langfuse-Trace-Id)──▶ llm-router (FastAPI)
                                                              └─ router_generate / router_embeddings  ← Python spans
```

## Bật tracing

### Local dev (self-host Langfuse)

```bash
# 1. Khởi động stack monitor (Langfuse nằm trong compose monitoring)
docker compose -f docker/docker-compose.yml -f docker/docker-compose.monitoring.yml up -d langfuse-server
# Mở http://localhost:3000 → tạo project → copy PUBLIC/SECRET key

# 2. Backend: set env (KHÔNG commit key)
export LANGFUSE_HOST=http://localhost:3000
export LANGFUSE_PUBLIC_KEY=pk-lf-...
export LANGFUSE_SECRET_KEY=sk-lf-...

# 3. llm-router: set cùng 2 key + host
export LANGFUSE_HOST=http://localhost:3000
export LANGFUSE_PUBLIC_KEY=pk-lf-...
export LANGFUSE_SECRET_KEY=sk-lf-...
```

### Staging (Render)

Render **không chạy được docker-compose sidecar** → dùng **Langfuse Cloud**
(`https://cloud.langfuse.com`). Set `LANGFUSE_PUBLIC_KEY` / `LANGFUSE_SECRET_KEY`
/ `LANGFUSE_HOST` là **Environment Variables trên Render dashboard**, không
bao giờ commit vào repo (xem `.env.example`).

## Tắt tracing

Để trống `LANGFUSE_PUBLIC_KEY` (hoặc `LANGFUSE_ENABLED=false`) → mọi hàm
Langfuse là no-op, **zero overhead**, app chạy bình thường.

## Metadata bắt buộc trên mỗi trace

| Trường | Ý nghĩa |
|---|---|
| `strategy` | `direct` / `corrective` / `web_search` / `no_evidence` / `general_knowledge` |
| `confidence` | điểm confidence cuối cùng (0–1) |
| `documentId` | id tài liệu được hỏi |
| `chunkCount` | số chunk retrieved |
| `outputTokens` | số token sinh ra (nếu có) |
| `llmError` | `circuit_open` / `unreachable` / `generation_failed` (khi lỗi) |

## Dashboard & Export trace xấu

- **Dashboard Langfuse**: p50/p95 latency theo strategy, tỷ lệ `no_evidence`
  / `web_search` fallback, chi phí token/ngày (dùng session/grouping theo
  `strategy` + `llmError`).
- **Export trace xấu** để rerun eval trên case thực tế:

```bash
python scripts/langfuse_export_bad_traces.py \
  --host https://cloud.langfuse.com \
  --project-id <pid> \
  --out eval/results/bad_traces_$(date +%F).json \
  --from-date 2026-08-01
```

Script lọc trace có `llmError`, strategy `no_evidence`/`general_knowledge`,
hoặc confidence < 0.45, xuất JSON cùng format với `eval/results/`.

## Security

- Không một secret nào (`LANGFUSE_SECRET_KEY`, `pk-lf-*`, `sk-lf-*`) được commit.
- `.env` đã nằm trong `.gitignore`; `.env.example` chỉ chứa placeholder rỗng.
- Ingestion dùng Basic auth `base64(pk:sk)` gửi thẳng `/api/public/ingestion`.
