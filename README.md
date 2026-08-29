# 📚 Smart Document Chatbot - Enterprise Agentic CRAG Platform
[![Vite](https://img.shields.io/badge/Vite-5.x-646CFF?logo=vite&logoColor=white)](https://vite.dev/)
[![React](https://img.shields.io/badge/React-18.x-61DAFB?logo=react&logoColor=white)](https://react.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.x-3178C6?logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![TanStack Query](https://img.shields.io/badge/TanStack_Query-5.x-FF4154?logo=reactquery&logoColor=white)](https://tanstack.com/query)
[![Spring Boot](https://img.shields.io/badge/Spring_Boot-3.2.x-6DB33F?logo=springboot&logoColor=white)](https://spring.io/projects/spring-boot)
[![Cloudflare Workers AI](https://img.shields.io/badge/Cloudflare_Workers_AI-LLM-F38020?logo=cloudflare&logoColor=white)](https://developers.cloudflare.com/workers-ai/)
[![Qdrant](https://img.shields.io/badge/Qdrant-Vector_DB-red?logo=qdrant&logoColor=white)](https://qdrant.tech/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-4169E1?logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Cloudflare R2](https://img.shields.io/badge/Cloudflare_R2-Storage-F38020?logo=cloudflare&logoColor=white)](https://developers.cloudflare.com/r2/)

Dự án mẫu mực kết hợp giữa **Kỹ nghệ Phần mềm truyền thống (Software Engineering)** chất lượng cao và **Kỹ nghệ Trí tuệ Nhân tạo hiện đại (AI Engineering)** theo xu thế công nghệ năm 2025. Hệ thống là một nền tảng **Agentic Corrective RAG (CRAG)** đa tài liệu (Multi-document) mạnh mẽ, hỗ trợ phân tích định dạng tệp thông minh, suy luận sâu và stream kết quả thời gian thực token-by-token.

> [!TIP]
> **Dành cho nhà tuyển dụng (CV / Portfolio)**: Dự án này minh chứng cho khả năng thiết kế kiến trúc phân tán, tích hợp LLM chuyên sâu, cấu trúc RAG tự thích ứng (Self-reflective), di chuyển build-tool hiện đại sang Vite, quản lý state chuyên nghiệp bằng React Query, và tối ưu hóa trải nghiệm người dùng với Server-Sent Events (SSE).

---

## 🧪 Chạy n8n cục bộ

> **Trạng thái trung thực:** n8n được đóng gói dưới dạng hạ tầng Docker Compose (service + Postgres riêng) **nhưng chưa có workflow nào được định nghĩa trong repository này**. Phần tích hợp sâu với Action Agent (`n8n_config.py`) nằm trong roadmap. Chạy n8n nếu bạn muốn dùng nó làm công cụ tự động hóa ngoài hệ thống — đừng coi đây là tính năng tích hợp đã hoàn thiện.

Để khởi động n8n cùng hệ thống chính, chạy:

```bash
cd docker
docker compose -f docker-compose.yml up -d n8n n8n-postgres
```

Sau khi khởi động, truy cập:
- n8n UI: http://localhost:5678
- tài khoản đăng nhập: giá trị `N8N_BASIC_AUTH_USER` / `N8N_BASIC_AUTH_PASSWORD` trong file `.env` (phải tự đặt — không có giá trị mặc định trong repo)

Nếu bạn muốn khởi động toàn bộ stack (backend, frontend, agent, monitoring và n8n), chạy:

```bash
cd docker
docker compose -f docker-compose.yml up -d
```

## 🎯 Tính năng Nổi bật (Core Features)

*   **Real-time Streaming Response (Server-Sent Events - SSE)**: Chatbot phản hồi tức thời theo thời gian thực, kết nối qua `SseEmitter` của Spring Boot và luồng NDJSON stream từ **LLM Router (Cloudflare Workers AI)**.
*   **Vite + React + TypeScript 5 (Strict Mode)**: Hệ thống Frontend được tái cấu trúc từ CRA sang **Vite**, tăng tốc độ khởi động và HMR gấp 10-20 lần. Toàn bộ mã nguồn sử dụng **TypeScript** an toàn cao, biên dịch 100% không lỗi.
*   **TanStack Query (React Query v5)**: Quản lý cache dữ liệu tài liệu và lịch sử chat tối ưu, tự động invalidation khi upload/delete thông qua `useQuery` và `useMutation`, loại bỏ hoàn toàn việc fetch dữ liệu thủ công qua `useEffect`.
*   **Kiến trúc Agentic CRAG (Corrective RAG) Loop**:
    *   *Confidence Evaluation*: Đánh giá điểm tin cậy ngữ cảnh trích xuất (ngưỡng 0.6).
    *   *Query Reformulation*: Khi độ tin cậy thấp, tự động viết lại câu hỏi thành các biến thể tối ưu hơn qua LLM Router (Cloudflare Workers AI), sau đó truy vấn lại.
    *   *Reranking*: Gộp kết quả truy vấn gốc và các biến thể, sắp xếp lại theo điểm số và giữ top-k.
    *   *Web Search Fallback*: Bổ sung ngữ cảnh trực tuyến bằng API Tavily khi tài liệu không đủ dữ liệu (tùy chọn, cần `TAVILY_API_KEY`).
    *   *Safe Abstention (Unanswerable Handling)*: Khi không có đủ bằng chứng và không có web fallback, hệ thống **trả về thông báo "không đủ bằng chứng" thay vì bịa câu trả lời** từ kiến thức chung (có thể tắt qua `CRAG_ABSTAIN_ENABLED=false`).
*   **Multi-Document Synthesis**: Hỗ trợ lựa chọn linh hoạt giữa chế độ hỏi đáp trên một tài liệu đơn lẻ (Single File Mode) hoặc tổng hợp ngữ cảnh chéo trên nhiều tài liệu cùng lúc (Multi-File Chat Mode).
*   **Trích dẫn Nguồn ngữ cảnh (Citations)**: Hiển thị minh bạch nguồn gốc thông tin trích xuất (metadata tệp, nội dung đoạn văn gốc, điểm số tương đồng) giúp kiểm chứng tính chính xác của phản hồi.
*   **Prompt-Injection Defense**: Kiểm tra heuristic trên câu hỏi người dùng trước mọi lời gọi LLM; các yêu cầu cố gắng ghi đè chỉ thị / lộ system prompt / trích xuất bí mật bị chặn (xem `backend/.../security/PromptInjectionDetector.java`).
*   **Cloudflare Workers AI**: LLM (`@cf/meta/llama-3.3-70b-instruct-fp8-fast`) và embedding (`@cf/baai/bge-base-en-v1.5`) chạy qua LLM Router (Ollama-compatible API, thuần Cloudflare — không còn local fallback).
*   **Cloudflare R2 Storage**: Lưu trữ tài liệu gốc (S3-compatible) thay thế Supabase Storage.

---

## 🏗️ Kiến trúc Hệ thống (System Architecture)

> **Ghi chú trung thực:** Luồng chat chính của sản phẩm là **Spring Boot → LLM Router → Cloudflare Workers AI**, với retrieval dựa trên chunks lưu trong **PostgreSQL** (lexical scoring). Python Agent Service (LangGraph) là một dịch vụ AI thử nghiệm riêng biệt có đầy đủ endpoint riêng (`/v1/agent/*`) nhưng **chưa được nối vào luồng chat chính** — đừng mô tả nó như API gateway của sản phẩm.

```
┌────────────────────────────────────────────────────────┐
│                   Frontend Client                      │
│      React 18 + Vite 5 + TypeScript + React Query      │
└───────────┬────────────────────────────────┬───────────┘
            │                                │
            │ HTTP (SSE / Stream)            │ HTTP / JSON
┌───────────▼────────────────────────────────▼───────────┐
│                    Spring Boot API                     │
│               Controller (SseEmitter)                  │
│  ┌──────────────────────────────────────────────────┐  │
│  │                    ChatService                   │  │
│  │  ┌──────────────┐      ┌──────────────────────┐  │  │
│  │  │  Retrieval   ├─────►│  PostgreSQL chunks   │  │  │
│  │  │ (lexical     │      │  (vector collection  │  │  │
│  │  │  scoring)    │      │  per user/document)  │  │  │
│  │  └──────┬───────┘      └──────────────────────┘  │  │
│  │         │ confidence < 0.6                        │  │
│  │         ▼                                         │  │
│  │  ┌──────────────┐      ┌──────────────────────┐  │  │
│  │  │ Query Reform │─────►│ Re-retrieve + merge  │  │  │
│  │  └──────┬───────┘      └──────────────────────┘  │  │
│  │         ▼                                         │  │
│  │  [LLM Router → Cloudflare Workers AI] ◄── [Tavily] │  │
│  │         │ (web fallback tùy chọn)                │  │
│  │         ▼                                         │  │
│  │  [Safe Abstention khi thiếu bằng chứng]          │  │
│  └──────────────────┬───────────────────────────────┘  │
└─────────────────────┼──────────────────────────────────┘
                      │ JPA ORM
             ┌────────▼────────┐
             │ PostgreSQL DB   │
             │ (Chat History / │
             │  Doc Metadata / │
             │  Chunks)        │
             └─────────────────┘
```

Dịch vụ Python Agent (LangGraph multi-agent) chạy độc lập trên cổng 9000, với các endpoint `/v1/agent/invoke`, `/v1/agent/invoke-stream`, connector ingestion (Google Drive/Gmail/Slack/SharePoint), memory dài hạn trong PostgreSQL, Qdrant retrieval, và các endpoint thử nghiệm ADK/A2A/MCP (custom implementation lấy cảm hứng từ các khái niệm tương ứng — **không phải** Google ADK / A2A / MCP chính thức). Xem [`docs/agent_architecture.md`](docs/agent_architecture.md).

---

## 🛠️ Tech Stack & Quyết định Công nghệ

| Layer | Công nghệ | Vai trò & Lý do chọn lựa |
| :--- | :--- | :--- |
| **Backend Core** | Spring Boot 3.2.x | RESTful API, auth JWT, owner isolation, CRAG orchestration, SSE streaming, Graceful Shutdown. |
| **AI LLM Runtime** | FastAPI LLM Router → Cloudflare Workers AI (`@cf/meta/llama-3.3-70b-instruct-fp8-fast`) | Router phân phối tác vụ đơn giản/phức tạp giữa các model Workers AI (thuần Cloudflare, không local fallback). |
| **Embedding Engine** | Cloudflare Workers AI (`@cf/baai/bge-base-en-v1.5`) | Sinh embedding 768 chiều qua LLM Router. |
| **File Storage** | Cloudflare R2 (S3-compatible) | Lưu trữ tài liệu gốc upload, thay thế Supabase Storage. |
| **Vector DB** | Qdrant (REST API) | Retrieval vector cho Agent Service (collection riêng theo user+doc) — **không nằm trong luồng chat Java** (Java dùng lexical scoring trên chunks PostgreSQL). |
| **Relational DB** | PostgreSQL 15 | Metadata tệp, chunks, lịch sử hội thoại chuẩn hóa ACID, Flyway migrations. |
| **Frontend Platform** | Vite 5 + React 18 | Build tool hiện đại, HMR nhanh, TypeScript strict. |
| **State & Caching** | TanStack Query v5 | Quản lý server-state, cache-busting, retry, loading skeleton. |
| **Telemetry** | Prometheus / Actuator / structured logs (JSON) | Metrics RAG, health probes, logs có `requestId`; MLflow tùy chọn cho eval. |

---

## 📂 Cấu trúc Dự án (Project Structure)

```
Smart-Document-Chatbot/
├── backend/                            # Java Spring Boot 3 API (context-path /api)
│   ├── src/main/java/com/smartdocchat/
│   │   ├── controller/                 # REST endpoints (ChatController hỗ trợ SSE streaming)
│   │   ├── service/                    # Chat, document, storage, LLM handling
│   │   ├── repository/                 # Spring Data JPA repositories
│   │   ├── entity/                     # JPA entities (User, Document, ChatMessage)
│   │   ├── dto/                        # Request/Response DTOs
│   │   ├── config/                     # Security, JWT filter, OpenAPI
│   │   ├── exception/                  # Global exception handler
│   │   └── util/                       # Helpers (LlmConfig, JWT, ...)
│   ├── src/main/resources/             # application.yml, profiles, logback, Flyway db/
│   └── pom.xml                         # Maven dependency management
├── frontend/                           # React 18 + Vite 5 + TypeScript + TanStack Query
│   ├── src/
│   │   ├── pages/                      # LoginPage, ChatPage
│   │   ├── context/                    # AuthContext (JWT)
│   │   ├── components/                 # ErrorBoundary
│   │   ├── App.tsx, index.tsx, types.ts
│   ├── e2e/                            # Playwright smoke tests
│   └── package.json, vite.config.ts
├── agent/                              # Python FastAPI + LangGraph (multi-agent CRAG, THỬ NGHIỆM)
│   ├── agents/                         # 8 specialist agents + orchestrator (LangGraph graph)
│   ├── graph/                          # LangGraph StateGraph workflow (được dùng thật)
│   ├── tools/                          # Qdrant hybrid search, Tavily web search, report, notification
│   ├── memory/                         # Short/long-term memory, context summarizer, VI-EN language handler
│   ├── connectors/                     # Gmail, Google Drive, SharePoint, Slack
│   ├── streaming/                      # SSE event helpers
│   ├── benchmark/, eval_framework/, security/, improvement/
│   ├── mcp/, a2a/, adk_*               # CUSTOM implementations lấy cảm hứng từ MCP/A2A/ADK (không phải SDK chính thức)
│   └── main.py                         # FastAPI entrypoint (port 9000)
├── llm-router/                         # FastAPI router → Cloudflare Workers AI (chat + embeddings, Ollama wire protocol)
├── eval/                               # RAG evaluation scripts + question sets
├── docker/                             # docker-compose (prod/dev/monitoring) + Dockerfiles
│   └── docker-compose.yml              # LLM router, backend, frontend, agent, n8n, Prometheus, Grafana
└── docs/                               # Architecture, API, observability, ADR
```

---

## 🔄 Luồng Nghiệp vụ RAG Tự Phản Hồi (Self-reflective RAG In-depth)

### Quy trình Xử lý Tài liệu (Ingestion Pipeline — luồng Java chính)
1. **Upload**: Tải tài liệu định dạng `.pdf`, `.docx` hoặc `.txt` (kiểm tra loại nội dung ở backend).
2. **Parsing**: Apache PDFBox / POI phân tách cấu trúc văn bản.
3. **Chunking**: Cắt nhỏ văn bản thành các phân đoạn (kích thước 500 ký tự).
4. **Lưu trữ**: Tài liệu gốc lưu vào **Cloudflare R2**; metadata + chunks (JSON) lưu vào **PostgreSQL**; owner isolation theo `owner_username`.

### Quy trình Trả lời Streaming & CRAG
```
[User Question]
       │
       ▼
[Prompt-Injection Check] ──(HIGH)──► [Blocked response — không gọi LLM]
       │
       ▼
[Initial Retrieval (PostgreSQL chunks — lexical score)] ──► Max Score >= 0.6?
       │                                                     │
       ├──(YES: High Confidence)                             ├──(NO: Low Confidence)
       │                                                     │
       ▼                                                     ▼
[Build RAG Prompt with Context]                      [Query Reformulation (LLM Router)]
       │                                                     │
       │                                                     ▼
       │                                            [Re-retrieve variants]
       │                                                     │
       │                                                     ▼
       │                                            [Merge & Rerank by score] ──► Score >= 0.6?
       │                                                     │                       │
       │                                                     ├──(YES)                ├──(NO)
       │                                                     │                       │
       │                                                     ▼                       ▼
       │                                            [Agentic Synthesis]     [Tavily Web Search (nếu có)]
       │                                                     │                       │
       │                                                     ▼                       ▼
       │                                            [Thiếu bằng chứng?]     [Web snippets]
       │                                                     │                       │
       │                                                     ▼                       ▼
       │                                            [Safe Abstention —         [Grounded answer]
       │                                             "không đủ bằng chứng"]
       │
       ├──────────────────────────────────────────────────────────────────────┘
       ▼
[LLM Router Streaming (Cloudflare Workers AI)]
       │
       ▼
[Typewriter Response Streamed to UI via SSE (SseEmitter)]
       │
       ▼
[Save Full Conversation History in PostgreSQL]
```

---

## 🚀 Hướng dẫn Cài đặt & Khởi động nhanh (Local Setup)

### Yêu cầu Hệ thống
*   Docker & Docker Compose
*   Java 17+ & Maven 3.8+
*   Node.js 18+ & npm

### Bước 1: Khởi động Hạ tầng Dev (PostgreSQL, Qdrant & LLM Router)
Từ thư mục gốc dự án:
```bash
make dev-up
```
*Hạ tầng sẽ hoạt động tại: PostgreSQL (`localhost:5432`), Qdrant (`localhost:6333`) và LLM Router (`localhost:8001`). LLM Router gọi Cloudflare Workers AI (cần `CLOUDFLARE_ACCOUNT_ID` + `CLOUDFLARE_API_TOKEN`).*

### Bước 2: Khởi động Backend (Spring Boot)
1. Copy `.env.example` sang `.env` và đặt giá trị thật: **bắt buộc** `JWT_SECRET` và `INTERNAL_SERVICE_TOKEN` (tạo bằng `openssl rand -base64 48`), `POSTGRES_PASSWORD`, và `QDRANT_API_KEY` nếu dùng Qdrant Cloud. Nếu backend chạy ngoài Docker, cấu hình `LLM_BASE_URL=http://localhost:8001`.
2. Khởi chạy ứng dụng Spring Boot:
```bash
cd backend
mvn spring-boot:run
```
*Backend API chạy tại: `http://localhost:8080/api`*

### Bước 3: Khởi động Frontend (Vite + TS)
1. Cài đặt các package cần thiết:
```bash
cd frontend
npm install
```
2. Khởi động môi trường phát triển:
```bash
npm run dev
```
*Truy cập trực tiếp tại: `http://localhost:3000` (được cấu hình proxy tự động tới API backend).*

---

## 📡 Chi tiết API Endpoint

API protected yêu cầu JWT (`Authorization: Bearer <token>`); tài liệu và lịch sử được cô lập theo tài khoản. Swagger UI: `/api/swagger-ui/index.html`. Chi tiết contract và endpoint nội bộ nằm tại [`docs/API.md`](docs/API.md).

### 📄 API Quản lý Tài liệu (Documents)
*   `POST /api/documents/upload` - Tải lên tài liệu mới (Xử lý Multipart-file).
*   `GET /api/documents` - Lấy danh sách tài liệu của người dùng hiện tại (cô lập theo `owner_username`).
*   `GET /api/documents/{id}` - Truy vấn trạng thái chi tiết của tệp tin (chỉ tài liệu của chính người dùng).
*   `DELETE /api/documents/{id}` - Xóa tài liệu khỏi hệ cơ sở dữ liệu (chỉ tài liệu của chính người dùng).

### 💬 API Hội thoại & Hỏi đáp (Chat & Streaming)
*   `POST /api/chat/ask` - Endpoint hỏi đáp đồng bộ truyền thống.
*   `POST /api/chat/ask-stream` - Endpoint hỏi đáp **Streaming dạng Text-Event-Stream** (Server-Sent Events).
*   `GET /api/chat/history/{sessionId}` - Tải lịch sử hội thoại của toàn bộ phiên.
*   `GET /api/chat/history/{sessionId}/{documentId}` - Lấy lịch sử hội thoại được phân tách theo tài liệu cụ thể.
*   `DELETE /api/chat/history/{sessionId}` - Xóa lịch sử phiên chat.
*   `GET /api/chat/sessions` - Danh sách phiên chat của người dùng.

### 🏥 Health & Metrics
*   `GET /api/actuator/health` - Health probe (public; kết nối DB, disk, liveness/readiness).
*   `GET /api/actuator/info` - Thông tin build (public).
*   Prometheus: `management.endpoints.web.exposure` chỉ expose `health,info` theo mặc định — cần mở `/actuator/prometheus` nếu muốn scrape metrics (xem [`docs/OBSERVABILITY.md`](docs/OBSERVABILITY.md)).

---

## 🧩 Structured Output Format (AI Engineer Standard)

Mỗi response từ `/chat/ask` và SSE `complete` event đều trả về cấu trúc đầy đủ:

```json
{
  "id": 42,
  "sessionId": "abc-123",
  "userMessage": "Hệ thống sử dụng framework nào?",
  "aiResponse": "Theo tài liệu, hệ thống sử dụng Spring Boot làm backend...",
  "sourceChunks": "[system_design.pdf] Backend service is implemented...",
  "confidence": "high",
  "confidenceScore": 0.87,
  "latencyMs": 1420,
  "model": "@cf/meta/llama-3.3-70b-instruct-fp8-fast",
  "ragStrategy": "direct",
  "sources": [
    {
      "document": "system_design.pdf",
      "documentId": 1,
      "content": "Backend service is implemented with Spring Boot...",
      "score": 0.87
    }
  ]
}
```

| Field | Ý nghĩa |
| :--- | :--- |
| `confidence` | `high` (≥0.70), `medium` (≥0.6), `low` (<0.6) |
| `ragStrategy` | `direct` / `corrective` / `web_search` / `no_evidence` / `general_knowledge` / `blocked` |
| `sources` | Danh sách structured citation kèm similarity score |

---

## 📊 Evaluation Pipeline

Hệ thống tích hợp pipeline đánh giá chất lượng RAG tự động:

Ngoài script classic RAG cho `/chat/ask`, agent workflow có evaluation riêng tại `eval/agent_eval.py` để đo intent routing, retrieval, answer completeness, hallucination, latency và source citation rate trên `/agent/invoke`.

```bash
# Chạy evaluation (cần JWT token và document đã upload)
python eval/eval.py \
  --base-url http://localhost:8080/api \
  --token <your-jwt-token> \
  --document-id 1
```

**Output mẫu:**
```
📊 EVALUATION RESULTS
============================================================
  Total Questions:      20
  Retrieval Accuracy:   85.00%
  Answer Correctness:   80.00%
  Hallucination Cases:  2
  Hallucination Rate:   10.00%
  Avg Latency:          1420ms
  P95 Latency:          3200ms
  Errors:               0
============================================================
```

Kết quả chi tiết được lưu tại `eval/results/eval_results.json`.

---

## 🤖 AI Tools Integration | Tích Hợp Công Cụ AI

This project was developed with heavy use of modern AI tools to accelerate development and improve code quality.

| Tool | How it was used | Specific prompts / usage |
|------|----------------|-------------------------|
| **ChatGPT (GPT-4o)** | Generated RAG evaluation pipeline, designed agent prompts, wrote test data, created system prompts | *"Create a set of 20 evaluation questions for a RAG system that answers questions from engineering documents"*, *"Design a system prompt for a document Q&A agent that cites sources and handles low-confidence scenarios"* |
| **GitHub Copilot** | Code completion for Spring Boot controllers, React components, TypeScript types, test cases | Auto-completed SSE streaming controller (`SseEmitter`), TanStack Query hooks, JPA entity mappings, Playwright e2e tests |
| **Claude (Anthropic)** | Designed CRAG architecture, reviewed MLOps pipeline, wrote documentation, created portfolio strategy | *"Design a Corrective RAG (CRAG) architecture with confidence scoring, query reformulation, web search fallback"*, *"Review this MLOps setup for gaps in model lifecycle management"* |
| **GenAI Tools (Prompt Engineering)** | Crafted structured output formats (JSON schema), few-shot prompts for citation formatting, guardrails against prompt injection | Used iterative refinement: *"Make the output include source citations with document name, page number, and similarity score"* |

### Example: ChatGPT Prompt for RAG Evaluation
```
Prompt: "Create 10 evaluation questions for a multi-document RAG chatbot that answers technical 
questions from engineering PDFs. Each question should have:
1. The question text (in Vietnamese)
2. Expected answer keywords
3. Expected source document
4. Difficulty level (easy/medium/hard)

Example format:
{
  "question": "Hệ thống sử dụng framework nào cho backend?",
  "expected_keywords": ["Spring Boot", "Java"],
  "expected_source": "system_design.pdf",
  "difficulty": "easy"
}"
```

### Example: Copilot Auto-completing SSE Controller
```java
// Copilot suggested this entire method after typing @SseEmitter
@PostMapping("/ask-stream")
public SseEmitter askStream(@RequestBody ChatRequest request) {
    SseEmitter emitter = new SseEmitter(300_000L); // 5 min timeout
    chatService.processStreaming(request, emitter);
    return emitter;
}
```

> 💡 **Takeaway**: AI tools reduced development time by ~60%. ChatGPT generated evaluation datasets and prompts, Copilot handled boilerplate code, and Claude reviewed architecture and documentation.

## Security, Testing & Operations

* `POST /api/auth/register` và `POST /api/auth/login` cấp JWT ký bằng secret cấu hình; login có khóa tài khoản tạm thời sau 5 lần sai trong 15 phút (in-memory). Upload/chat/auth endpoints được bảo vệ bằng token-bucket rate limiting thực tế (`RateLimitInterceptor` + `WebMvcConfig`, cấu hình `ratelimit.*`); Agent Service có rate limiting Redis thật (`agent/rate_limiter.py`).
* `/api/actuator/prometheus` được bảo vệ bằng `X-Internal-Token` (`INTERNAL_SERVICE_TOKEN`); chỉ health/info public. **Fail-fast:** staging/production từ chối khởi động nếu `JWT_SECRET` rỗng hoặc vẫn dùng secret dev mặc định (`SecretStrengthValidator`).
* Backend dùng JUnit + Mockito + JaCoCo (**187 test** bao phủ CRAG flow, abstention, prompt-injection, JWT, secret validation, rate-limit, filter); frontend dùng Vitest + Testing Library và Playwright smoke test (**25 unit test** + e2e); agent/llm-router dùng pytest. GitHub Actions chạy test, build và scan image/IaC (Trivy). Backend chat/upload/auth endpoints được bảo vệ bằng token-bucket rate limiting thực tế (`RateLimitInterceptor` + `WebMvcConfig`).
* Structured logging JSON mọi request ghi nhận: `requestId`, `method`, `path`, `status`, `durationMs` (`RequestIdFilter` + LogstashEncoder). Mỗi lần đọc tài liệu (`GET /documents/{id}`, `GET /documents/{id}/legal-chunks`) phát ra 1 dòng audit có `auditAction=document.read`, `documentId`, `owner`, `granted` (true/false theo owner isolation) để truy vết ai truy cập tài liệu nào. Prometheus thu metrics RAG (`chat.requests.total{strategy,confidence}`, `chat.abstentions`, `chat.injection.blocked`, `chat.latency`) qua `/actuator/prometheus`.
* Prompt-injection defense: heuristic kiểm tra câu hỏi người dùng trước mọi lời gọi LLM (`PromptInjectionDetector`); câu trả lời chỉ dựa trên context khi không đủ bằng chứng (safe abstention, `CRAG_ABSTAIN_ENABLED=true`).
* **Batch ingestion automation**: DAG Airflow thực tế `airflow/dags/document_ingestion_pipeline.py` (schedule daily 02:00) quét thư mục `inbound/`, login lấy JWT, gọi `POST /api/documents/upload` để đẩy tài liệu qua pipeline ingest chính (parse → chunk → embed → index PostgreSQL). Chạy qua `airflow-webserver` + `airflow-scheduler` + `airflow-postgres` trong `docker/docker-compose.yml` (LocalExecutor, không load example DAGs). Credentials qua Airflow Variables/Connections + env, không hardcode.
* **Model retrain automation**: DAG `airflow/dags/model_retrain_pipeline.py` (schedule weekly Chủ nhật 03:00) tái sinh dataset (`finetune/build_dataset.py`) rồi gọi agent service `POST /v1/agent/retrain` (internal-token) để huấn luyện lại LoRA adapter, cuối cùng xác thực artifact. DAG *orchestrate* (training chạy trên GPU runner qua agent service), fail loud nếu agent unavailable — không sinh adapter lỗi thầm.

Tài liệu vận hành: [`docs/OBSERVABILITY.md`](docs/OBSERVABILITY.md), [`docs/PERFORMANCE.md`](docs/PERFORMANCE.md), quyết định bảo mật [`docs/adr/0001-security-boundaries.md`](docs/adr/0001-security-boundaries.md), quyết định routing supply-chain [`docs/adr/0002-supply-chain-routing.md`](docs/adr/0002-supply-chain-routing.md) và bản đồ gap/evidence [`docs/AUDIT_AND_GAP_ANALYSIS.md`](docs/AUDIT_AND_GAP_ANALYSIS.md).

