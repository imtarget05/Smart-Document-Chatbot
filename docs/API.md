# Smart Document Chatbot API

Base URL: `/api`. Swagger UI is available at `/api/swagger-ui/index.html`; the generated OpenAPI JSON is at `/api/v3/api-docs`.

## Authentication

Create an account with `POST /auth/register` or log in using `POST /auth/login`. Passwords must be 12 to 100 characters. Protected endpoints require:

```http
Authorization: Bearer <jwt>
```

Documents and chat histories are scoped to the authenticated username. A client cannot retrieve a different user's object by supplying its ID or session ID.

## Public Endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/auth/register` | Register and issue JWT |
| `POST` | `/auth/login` | Authenticate and issue JWT |
| `GET` | `/actuator/health` | Health and Kubernetes probes |
| `GET` | `/actuator/info` | Service information |
| `GET` | `/v3/api-docs` | OpenAPI schema |
| `GET` | `/swagger-ui/index.html` | Interactive API documentation |

## User Endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/documents/upload` | Upload PDF, DOCX or TXT, maximum 50 MB |
| `GET` | `/documents` | List the user's documents |
| `GET` | `/documents/{id}` | Read one owned document |
| `DELETE` | `/documents/{id}` | Delete one owned document and vector collection |
| `GET` | `/documents/{id}/mindmap` | Generate or return the cached concept map |
| `POST` | `/chat/ask` | Synchronous RAG question |
| `POST` | `/chat/ask-stream` | SSE RAG response |
| `GET` | `/chat/history/{sessionId}` | User-scoped conversation history |
| `DELETE` | `/chat/history/{sessionId}` | Clear user-scoped conversation history |

Chat payload:

```json
{
  "sessionId": "browser-session-id",
  "documentIds": [1, 2],
  "message": "Summarize the differences."
}
```

`sessionId` is limited to 100 characters and `message` to 8,000 characters.

## Internal Endpoints

These endpoints require `X-Internal-Token: <INTERNAL_SERVICE_TOKEN>`. They are not user APIs.

| Method | Path | Caller |
| --- | --- | --- |
| `POST` | `/documents/{id}/etl-complete` | Airflow callback |
| `POST` | `/documents/{id}/etl-fail` | Airflow callback |
| `GET` | `/actuator/prometheus` | Prometheus scraper |

Production deployments must inject a unique internal token into both backend and Airflow. Prometheus must send the same value as a bearer credential or `X-Internal-Token`.

## System Endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/system/health` | RAG infrastructure health (Qdrant + Ollama status). Public. |
| `GET` | `/system/metrics` | Aggregated RAG metrics (requests, latency, fallback/error rates). Requires JWT. |

