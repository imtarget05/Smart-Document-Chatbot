# Test Plan — Smart Document Chatbot (E2E)

## Prerequisites

- Backend running (Spring Boot, context-path `/api`), e.g. on the default port:
  ```bash
  cd backend
  env SERVER_PORT=8082 \
      SPRING_DATASOURCE_URL=jdbc:postgresql://localhost:5433/smart_doc_chatbot \
      SPRING_DATASOURCE_USERNAME=postgres \
      SPRING_DATASOURCE_PASSWORD=postgres \
      SPRING_JPA_HIBERNATE_DDL_AUTO=validate \
      LLM_BASE_URL=http://localhost:11434 \
      LLM_CHAT_MODEL=qwen2.5:7b \
      mvn -B spring-boot:run
  ```
- Ollama running with `qwen2.5:7b` + `nomic-embed-text` (chat + embeddings).
- Tools: `curl`, `jq`.

> **Base URL**: adjust `BASE` to your running instance (default `http://localhost:8080`; the
> E2E run above uses `8082`). All endpoints are under the **`/api`** context-path.

## Notes on Auth (important)

- `JwtAuthenticationFilter` accepts **either** the `Authorization: Bearer <token>` header
  **or** the httpOnly `jwt_token` cookie → header is the easy path for `curl`.
- CSRF is ignored for `/auth/**`, `/documents/**`, `/chat/**` (`SecurityConfig`), so no
  `X-XSRF-TOKEN` header is required when using the Bearer header.
- Password must be **12–100 characters** (`AuthRequest @Size(min=12)`) — `admin`/`admin` fails.
- No admin user is seeded by Flyway — **register** the user you want first.

## 1. Register + Login → get token

```bash
BASE=http://localhost:8080

# Register first (400 if the username is already taken — that's fine).
curl -s -X POST "$BASE/api/auth/register" \
  -H 'Content-Type: application/json' \
  -d '{"username":"testuser","password":"testpassword123"}' >/dev/null || true

TOKEN=$(curl -s -X POST "$BASE/api/auth/login" \
  -H 'Content-Type: application/json' \
  -d '{"username":"testuser","password":"testpassword123"}' | jq -r .token)
```

## 2. Upload a document (PDF / DOCX / TXT)

```bash
curl -s -X POST "$BASE/api/documents/upload" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@path/to/rag_demo.txt" | jq
# → note the returned documentId (e.g. 2). ETL will populate chunkCount.
```

## 3. Chat — `/api/chat/ask`

Correct endpoint (NOT `/api/ask`), `sessionId` **required** (`@NotBlank`), Bearer token.

```bash
curl -s -X POST "$BASE/api/chat/ask" \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"sessionId":"test-session-1","documentId":2,"message":"..."}' | jq
```

### Expected `ragStrategy`

Retrieval is **lexical** (word-coverage scoring over PostgreSQL chunks, `RetrievalService`).
The question must contain **keywords actually present in the document** to reach strategy `direct`:

- ✅ `rag_demo.txt` (content: *"…embedding generation, vector retrieval … corrective RAG …"*)
  → `{"message":"What does the Smart Document Chatbot do?","documentId":2}` → **`direct`**
- 🔁 Partial overlap → `corrective`
- ❌ Keep a placeholder / unrelated keywords, or omit `documentId` (null)
  → **`general_knowledge`** — this is **by design** (CRAG fallback), not a failure.

```bash
# direct (high confidence)
curl -s -X POST "$BASE/api/chat/ask" \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"sessionId":"test-session-1","documentId":2,"message":"What does the Smart Document Chatbot do?"}' | jq

# fallback (documentId null) — expect ragStrategy "general_knowledge"
curl -s -X POST "$BASE/api/chat/ask" \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"sessionId":"test-session-1","message":"...","documentId":null,"webSearch":false}' | jq
```

## 4. Streaming — `/api/chat/ask-stream`

SSE: emits `event:metadata` → `event:chunk` (×N) → `event:complete`.

```bash
curl -N -X POST "$BASE/api/chat/ask-stream" \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"sessionId":"test-session-2","documentId":2,"message":"What does the Smart Document Chatbot do?"}'
```
