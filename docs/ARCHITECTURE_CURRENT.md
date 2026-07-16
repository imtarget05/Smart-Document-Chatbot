# Current Architecture Audit

Tài liệu này ghi lại kiến trúc hiện tại của repo Smart Document Chatbot theo code thực tế (đã kiểm tra từ frontend, backend Spring Boot, agent-service Python, cấu hình Docker/PostgreSQL). Mục đích là làm baseline trước khi sửa hoặc mở rộng.

## 1. Tổng quan hệ thống

Hệ thống hiện có 3 lớp chính:

- Frontend: React + TypeScript + Vite
- Backend API: Java Spring Boot 3, chạy dưới context-path `/api`
- Agent Service: Python FastAPI + LangGraph/LangChain, đóng vai trò orchestrator cho các specialist agent

Ngoài ra còn có:

- Qdrant: vector database cho retrieval
- Ollama / LLM Router: model inference cho chat và embeddings
- PostgreSQL: lưu metadata tài liệu, user, chat history
- Airflow: ingestion ETL workflow
- Prometheus/Grafana: monitoring/observability

---

## 2. Cấu trúc module chính hiện tại

### 2.1 Frontend
Đường dẫn: `frontend/`

Cấu trúc chính:

- `frontend/src/App.tsx`: component chính, điều hướng auth, sidebar, chat mode, tab classic/agent
- `frontend/src/components/`: UI thành phần
  - `DocumentUpload.tsx`: upload file
  - `DocumentList.tsx`: hiển thị danh sách tài liệu
  - `ChatWindow.tsx`: chat classic qua SSE
  - `AgentChat.tsx`: chat qua agent service
  - `ConceptMap.tsx`: hiển thị concept map (nếu có dữ liệu)
  - `ErrorBoundary.tsx`: error boundary
- `frontend/src/App.css`, `frontend/src/index.css`: styling
- `frontend/vite.config.ts`: Vite config
- `frontend/package.json`: dependency và scripts

### 2.2 Backend Spring Boot
Đường dẫn: `backend/src/main/java/com/smartdocchat/`

Package chính:

- `config/`: security, CORS, WebSocket, actuator/monitoring config
- `controller/`: REST endpoints và WebSocket endpoint
- `dto/`: request/response DTO
- `entity/`: JPA entities
- `repository/`: Spring Data repositories
- `service/`: business logic cho auth, document, chat, retrieval, storage, embedding
- `util/`: utility/helper
- `exception/`: exception handling

Các controller hiện có:

- `AuthController`: login/register
- `DocumentController`: upload/list/get/delete/update ETL state/mindmap
- `ChatController`: ask, ask-stream, history, sessions, WebSocket
- `AgentController`: gọi agent service / report / action / connector ingest / health
- `SystemHealthController`: health check
- `MetricsController`: system metrics

### 2.3 Agent Service (Python)
Đường dẫn: `agent/`

Cấu trúc chính:

- `agents/`: LangGraph specialist agents
  - `orchestrator.py`
  - `rag_agent.py`
  - `report_agent.py`
  - `comparator_agent.py`
  - `researcher_agent.py`
  - `action_agent.py`
  - `engineering_analysis_agent.py`
  - `ingestion_agent.py`
- `graph/`: workflow và state definition
- `tools/`: tool wrappers
  - `qdrant_tool.py`
  - `web_search_tool.py`
  - `notification_tool.py`
  - `report_tool.py`
- `connectors/`: connectors cho Gmail/Drive/SharePoint/Slack
- `ingestion/`: ingestion pipeline logic
- `memory/`: short-term và long-term memory
- `llm_factory.py`: LLM client factory
- `main.py`: FastAPI entrypoint
- `settings.py`: env-driven config
- `rate_limiter.py`: rate limiter

---

## 3. API hiện có

Backend chạy dưới context-path `/api`, nên route thực tế thường là `/api/...`.

### 3.1 Auth

| Method | Path | Mô tả ngắn |
|---|---|---|
| POST | `/api/auth/register` | Đăng ký user |
| POST | `/api/auth/login` | Đăng nhập, trả JWT |

### 3.2 Documents

| Method | Path | Mô tả ngắn |
|---|---|---|
| POST | `/api/documents/upload` | Upload file tài liệu (PDF/DOCX/TXT), xử lý lưu trữ + indexing |
| GET | `/api/documents` | Lấy danh sách tài liệu của user |
| GET | `/api/documents/{id}` | Lấy chi tiết tài liệu |
| DELETE | `/api/documents/{id}` | Xóa tài liệu |
| POST | `/api/documents/{id}/etl-complete` | Cập nhật trạng thái ETL sang READY |
| POST | `/api/documents/{id}/etl-fail` | Đánh dấu ETL thất bại |
| GET | `/api/documents/{id}/mindmap` | Lấy hoặc tạo concept map cho tài liệu |

### 3.3 Chat

| Method | Path | Mô tả ngắn |
|---|---|---|
| POST | `/api/chat/ask` | Chat hỏi đáp đồng bộ |
| POST | `/api/chat/ask-stream` | Chat streaming theo SSE |
| GET | `/api/chat/history/{sessionId}` | Lấy lịch sử chat theo session |
| GET | `/api/chat/history/{sessionId}/{documentId}` | Lấy lịch sử chat theo session + document |
| DELETE | `/api/chat/history/{sessionId}` | Xóa lịch sử chat session |
| GET | `/api/chat/sessions` | Lấy danh sách session chat của user |

### 3.4 Agent proxy endpoints

| Method | Path | Mô tả ngắn |
|---|---|---|
| POST | `/api/agent/invoke` | Gọi agent orchestration service |
| POST | `/api/agent/report` | Tạo report/PDF |
| POST | `/api/agent/action` | Thực hiện action (email/webhook/Jira/Notion) |
| POST | `/api/agent/connector/ingest` | Trigger ingestion từ connector |
| GET | `/api/agent/health` | Health check agent service |

### 3.5 System / observability

| Method | Path | Mô tả ngắn |
|---|---|---|
| GET | `/api/system/health` | Health check hệ thống |
| GET | `/api/system/metrics` | Metrics tổng hợp của hệ thống |
| GET | `/api/actuator/health` | Spring Boot health endpoint |
| GET | `/api/actuator/prometheus` | Prometheus metrics export |

### 3.6 WebSocket

| Method | Path | Mô tả ngắn |
|---|---|---|
| WS / STOMP | `/ws` + `/app/chat/send` | Gửi chat qua WebSocket, broadcast tới topic `/topic/messages` |

---

## 4. LangGraph agents hiện tại

Workflow được dựng trong `agent/graph/workflow.py` và router theo `agent_type`.

### 4.1 Orchestrator
- File: `agent/agents/orchestrator.py`
- Vai trò: phân loại intent người dùng và quyết định agent nào sẽ xử lý
- Intent hỗ trợ: `rag`, `report`, `compare`, `research`, `action`, `engineering`
- Mặc định fallback heuristic nếu LLM call fail

### 4.2 Specialist agents

| Agent | File | Chức năng | Tool gọi |
|---|---|---|---|
| RAG | `agent/agents/rag_agent.py` | Trả lời từ tài liệu, có hybrid retrieval và citation | `QdrantHybridSearch`, optional `TavilySearch` |
| Report | `agent/agents/report_agent.py` | Tạo report và PDF | `QdrantHybridSearch`, `PdfReportBuilder` |
| Comparator | `agent/agents/comparator_agent.py` | So sánh nhiều tài liệu | `QdrantHybridSearch` |
| Researcher | `agent/agents/researcher_agent.py` | Tìm kiếm web và tổng hợp | `TavilySearch`, `QdrantHybridSearch` |
| Action | `agent/agents/action_agent.py` | Thực hiện email/webhook/Jira/Notion | `EmailNotifier`, `WebhookTrigger`, HTTP calls |
| Engineering Analysis | `agent/agents/engineering_analysis_agent.py` | Phân tích engineering/test report dạng 8D | `QdrantHybridSearch` |
| Ingestion | `agent/agents/ingestion_agent.py` | Điều phối ingestion từ connector | pipeline ingestion |

### 4.3 Workflow routing

Graph hiện tại:

`START -> orchestrator -> [rag|report|compare|research|action|engineering] -> END`

---

## 5. Tools và dependency bên trong agent service

### Tool chính

- `tools/qdrant_tool.py`: hybrid search (semantic + BM25)
- `tools/web_search_tool.py`: gọi Tavily
- `tools/notification_tool.py`: gửi email/webhook
- `tools/report_tool.py`: sinh PDF report

### Connector hiện có

- `connectors/gmail.py`
- `connectors/google_drive.py`
- `connectors/sharepoint.py`
- `connectors/slack_connector.py`

Các connector hiện có trong code nhưng chưa chắc đã được wired đầy đủ vào UI/API hiện tại.

---

## 6. PostgreSQL schema hiện tại

### 6.1 Bảng chính

| Table | Mô tả |
|---|---|
| `users` | user đăng nhập, role, password hash (ở code hiện tại password được lưu như plain text ở entity/DTO flow, cần kiểm tra lại thực tế triển khai) |
| `documents` | metadata tài liệu upload: filename, filepath, owner, type, size, status, chunk_count, summary, suggested questions, concept map |
| `chat_messages` | lịch sử chat: session_id, owner, document_id(s), user message, AI response, source chunks |

### 6.2 Schema tóm tắt

#### `users`
- `id` (PK)
- `username` (unique)
- `password`
- `role`
- `created_at`

#### `documents`
- `id` (PK)
- `file_name`
- `file_path`
- `owner_username`
- `file_type`
- `file_size`
- `created_at`
- `updated_at`
- `vector_collection_id`
- `chunk_count`
- `summary`
- `suggested_questions`
- `concept_map`
- `status`

#### `chat_messages`
- `id` (PK)
- `session_id`
- `owner_username`
- `document_id`
- `document_ids`
- `user_message`
- `ai_response`
- `source_chunks`
- `created_at`

### 6.3 Database init
- File: `docker/init-db/01-init.sql`
- Tạo extension: `uuid-ossp`, `pg_trgm`

---

## 7. Biến môi trường đang được dùng

### 7.1 Backend Spring Boot
Các biến được đọc từ `backend/src/main/resources/application.yml`:

| Variable | Mô tả |
|---|---|
| `SPRING_DATASOURCE_URL` / `NEON_DATABASE_URL` | JDBC URL PostgreSQL |
| `SPRING_DATASOURCE_USERNAME` | PostgreSQL username |
| `SPRING_DATASOURCE_PASSWORD` | PostgreSQL password |
| `SPRING_JPA_HIBERNATE_DDL_AUTO` | Hibernate ddl mode |
| `SERVER_PORT` | Port backend |
| `JWT_SECRET` | JWT secret |
| `JWT_EXPIRATION_MS` | JWT expiration |
| `INTERNAL_SERVICE_TOKEN` | token để auth giữa backend và agent service |
| `CORS_ALLOWED_ORIGINS` | allowed origins |
| `LLM_BASE_URL` | LLM router base URL |
| `LLM_CHAT_MODEL` | chat model |
| `LLM_EMBEDDING_MODEL` | embedding model |
| `QDRANT_HOST` / `QDRANT_PORT` | Qdrant host/port |
| `QDRANT_API_KEY` | Qdrant API key |
| `AIRFLOW_ENABLED` / `AIRFLOW_URL` | Airflow integration |
| `AGENT_SERVICE_URL` | Python agent service URL |
| `STORAGE_PROVIDER` | local/supabase |
| `SUPABASE_URL` / `SUPABASE_BUCKET` / `SUPABASE_SERVICE_KEY` | Supabase storage |
| `LOCAL_UPLOAD_DIR` | local upload dir |
| `OTEL_EXPORTER_OTLP_TRACES_ENDPOINT` | tracing exporter |

### 7.2 Agent Service Python
Các biến đọc từ `agent/settings.py` (qua Pydantic BaseSettings):

| Variable | Mô tả |
|---|---|
| `INTERNAL_SERVICE_TOKEN` | verify request từ Spring Boot |
| `LLM_BASE_URL` / `LLM_CHAT_MODEL` / `LLM_EMBEDDING_MODEL` | LLM router + models |
| `QDRANT_HOST` / `QDRANT_PORT` / `QDRANT_API_KEY` | Qdrant access |
| `POSTGRES_*` | long-term memory DB |
| `TAVILY_API_KEY` | web search |
| `JIRA_*` | Jira integration |
| `NOTION_API_TOKEN` | Notion integration |
| `SMTP_*` | email integration |
| `AGENT_ALLOWED_ORIGINS` | allowed CORS origins |
| `AGENT_MAX_REQUEST_BYTES` | max request size |
| `AGENT_RATE_LIMIT_RPM` | rate limit |
| `REDIS_URL` | optional Redis |

### 7.3 Frontend
Biến môi trường hiện dùng trong code:

| Variable | Mô tả |
|---|---|
| `VITE_API_URL` | base URL cho backend API |

---

## 8. Điểm cần chú ý khi tiếp tục phát triển

- Backend và agent service hiện đang kết nối với nhau qua HTTP, với token nội bộ.
- Agent workflow có sẵn nhưng runtime phụ thuộc vào dependency Python và service bên ngoài như Qdrant/LLM/Ollama/Tavily.
- Frontend đang dùng chat classic qua SSE và agent chat qua backend proxy.
- Hệ thống đã có nền tảng monitoring và observability, nhưng vẫn cần kiểm tra tính đầy đủ và tính vận hành thực tế.

---

## 9. Kết luận ngắn

Repo hiện tại đã có một nền tảng RAG chatbot khá đầy đủ ở mức MVP/POC: frontend, backend API, agent orchestration, document ingestion, vector search, monitoring, và persistence. Tuy nhiên, vẫn có nhiều phần cần làm rõ thêm về production-hardening, RBAC, audit logging, connector coverage, và hoàn thiện workflow enterprise.
