# 📚 Smart Document Chatbot - Enterprise Agentic CRAG Platform
[![Vite](https://img.shields.io/badge/Vite-5.x-646CFF?logo=vite&logoColor=white)](https://vite.dev/)
[![React](https://img.shields.io/badge/React-18.x-61DAFB?logo=react&logoColor=white)](https://react.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.x-3178C6?logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![TanStack Query](https://img.shields.io/badge/TanStack_Query-5.x-FF4154?logo=reactquery&logoColor=white)](https://tanstack.com/query)
[![Spring Boot](https://img.shields.io/badge/Spring_Boot-3.2.x-6DB33F?logo=springboot&logoColor=white)](https://spring.io/projects/spring-boot)
[![Ollama](https://img.shields.io/badge/Ollama-Local_LLM-black)](https://ollama.com/)
[![Qdrant](https://img.shields.io/badge/Qdrant-Vector_DB-red?logo=qdrant&logoColor=white)](https://qdrant.tech/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-4169E1?logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Airflow](https://img.shields.io/badge/Apache_Airflow-ETL-017CEE?logo=apacheairflow&logoColor=white)](https://airflow.apache.org/)

Dự án mẫu mực kết hợp giữa **Kỹ nghệ Phần mềm truyền thống (Software Engineering)** chất lượng cao và **Kỹ nghệ Trí tuệ Nhân tạo hiện đại (AI Engineering)** theo xu thế công nghệ năm 2025. Hệ thống là một nền tảng **Agentic Corrective RAG (CRAG)** đa tài liệu (Multi-document) mạnh mẽ, hỗ trợ phân tích định dạng tệp thông minh, suy luận sâu và stream kết quả thời gian thực token-by-token.

> [!TIP]
> **Dành cho nhà tuyển dụng (CV / Portfolio)**: Dự án này minh chứng cho khả năng thiết kế kiến trúc phân tán, tích hợp LLM chuyên sâu, cấu trúc RAG tự thích ứng (Self-reflective), di chuyển build-tool hiện đại sang Vite, quản lý state chuyên nghiệp bằng React Query, và tối ưu hóa trải nghiệm người dùng với Server-Sent Events (SSE).

---

## 🧪 Chạy n8n cục bộ

Để khởi động workflow automation cùng hệ thống chính, chạy:

```bash
cd docker
docker compose -f docker-compose.yml up -d n8n n8n-postgres
```

Sau khi khởi động, truy cập:
- n8n UI: http://localhost:5678
- tài khoản đăng nhập: giá trị `N8N_BASIC_AUTH_USER` / `N8N_BASIC_AUTH_PASSWORD` trong file `.env`

Nếu bạn muốn khởi động toàn bộ stack (backend, frontend, agent, monitoring và n8n), chạy:

```bash
cd docker
docker compose -f docker-compose.yml up -d
```

## 🎯 Tính năng Nổi bật (Core Features)

*   **Real-time Streaming Response (Server-Sent Events - SSE)**: Chatbot phản hồi tức thời theo thời gian thực, kết nối qua `SseEmitter` của Spring Boot và luồng NDJSON native từ **Ollama**.
*   **Vite + React + TypeScript 5 (Strict Mode)**: Hệ thống Frontend được tái cấu trúc từ CRA sang **Vite**, tăng tốc độ khởi động và HMR gấp 10-20 lần. Toàn bộ mã nguồn sử dụng **TypeScript** an toàn cao, biên dịch 100% không lỗi.
*   **TanStack Query (React Query v5)**: Quản lý cache dữ liệu tài liệu và lịch sử chat tối ưu, tự động invalidation khi upload/delete thông qua `useQuery` và `useMutation`, loại bỏ hoàn toàn việc fetch dữ liệu thủ công qua `useEffect`.
*   **Kiến trúc Agentic CRAG (Corrective RAG) Loop**:
    *   *Confidence Evaluation*: Đánh giá điểm tin cậy ngữ cảnh trích xuất từ Qdrant (ngưỡng 0.45).
    *   *Query Reformulation*: Khi độ tin cậy thấp, kích hoạt tác nhân (Agent) tự động phân rã và viết lại câu hỏi thành các biến thể tối ưu hơn thông qua mô hình DeepSeek.
    *   *Parallel Retrieval & Reranking*: Truy vấn song song (Multi-threading) trên các vector collection và xếp hạng lại tài liệu.
    *   *Web Search Fallback*: Tự động bổ sung ngữ cảnh trực tuyến bằng API Tavily khi tài liệu không đủ dữ liệu.
    *   *Deep Reasoning Fallback*: Kích hoạt chế độ suy luận chuyên sâu nội bộ của mô hình khi nằm ngoài phạm vi tài liệu.
*   **Multi-Document Synthesis**: Hỗ trợ lựa chọn linh hoạt giữa chế độ hỏi đáp trên một tài liệu đơn lẻ (Single File Mode) hoặc tổng hợp ngữ cảnh chéo trên nhiều tài liệu cùng lúc (Multi-File Chat Mode).
*   **Trích dẫn Nguồn ngữ cảnh (Citations)**: Hiển thị minh bạch nguồn gốc thông tin trích xuất (metadata tệp, nội dung đoạn văn gốc) giúp kiểm chứng tính chính xác của phản hồi.
*   **Visual Concept Mapping**: AI tự động trích xuất các khái niệm cốt lõi của tài liệu và dựng thành bản đồ tư duy (Concept Map) trực quan bằng SVG, cho phép người dùng click để hỏi chatbot sâu hơn về khái niệm đó.
*   **Apache Airflow Ingestion ETL**: Pipeline dữ liệu tự động hóa quy trình phân tách trang, làm sạch nội dung, sinh embeddings và nạp index vào Qdrant một cách chuyên nghiệp.

---

## 🏗️ Kiến trúc Hệ thống (System Architecture)

Flow AI chính được chuẩn hóa trong [`docs/agent_architecture.md`](docs/agent_architecture.md): Frontend -> Spring Boot API gateway -> Python Agent Service -> LangGraph Orchestrator -> Specialist Agent -> Tools/Qdrant/LLM Router.

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
│  │     ┌──────────────┐            ┌─────────────┐  │  │
│  │     │  Embeddings  ├─(Ollama)──►│   Qdrant    │  │  │
│  │     └──────────────┘            └─────────────┘  │  │
│  │                                 (Vector search)  │  │
│  │     ┌──────────────┐                             │  │
│  │     │ Ollama/DeepSeek├─(Streaming)┐              │  │
│  │     └──────────────┘             │               │  │
│  │                                  │               │  │
│  │     ┌──────────────┐             ▼               │  │
│  │     │  Web Search  ├─(Tavily)──►[SSE Endpoint]   │  │
│  │     └──────────────┘                             │  │
│  └──────────────────┬───────────────────────────────┘  │
└─────────────────────┼──────────────────────────────────┘
                      │ JPA ORM
             ┌────────▼────────┐
             │ PostgreSQL DB   │
             │ (Chat History / │
             │  Doc Metadata)  │
             └─────────────────┘
```

---

## 🛠️ Tech Stack & Quyết định Công nghệ

| Layer | Công nghệ | Vai trò & Lý do chọn lựa |
| :--- | :--- | :--- |
| **Backend Core** | Spring Boot 3.2.x | Phát triển RESTful API hiệu năng cao, cơ chế Graceful Shutdown & Async processing chuyên nghiệp. |
| **AI LLM Runtime** | FastAPI LLM Router + Ollama / Claude / GPT-4o | Router ưu tiên Vision cho ảnh/scan, Claude cho tác vụ phức tạp và Llama cục bộ cho tác vụ đơn giản. |
| **Embedding Engine** | Ollama | Chạy mô hình `nomic-embed-text` cục bộ để sinh vector 768 chiều. |
| **Vector DB** | Qdrant (REST API) | Cấu trúc dữ liệu Vector hiệu năng cao, tổ chức phân tách linh hoạt theo Collection ID riêng cho từng tài liệu. |
| **Relational DB** | PostgreSQL 15 | Quản lý lưu trữ metadata tệp tin và toàn bộ lịch sử hội thoại chuẩn hóa ACID. |
| **Data Pipelines** | Apache Airflow | Tự động hóa tiến trình ETL tách nhỏ tài liệu, làm sạch cấu trúc và lập chỉ mục không đồng bộ. |
| **Frontend Platform** | Vite 5 + React 18 | Tối ưu hóa tối đa tốc độ biên dịch (Hot Module Replacement) thay thế cho Webpack/CRA lỗi thời. |
| **State & Caching** | TanStack Query v5 | Quản lý đồng bộ trạng thái server-state, tự động hóa cơ chế cache-busting, retry, và loading skeleton. |
| **Telemetry** | MLflow / Prometheus | Tracing chi tiết độ trễ, tokens tiêu hao, giám sát trực quan các bước suy luận của Agentic CRAG. |

---

## 📂 Cấu trúc Dự án (Project Structure)

```
Smart-Document-Chatbot/
├── backend/
│   ├── src/main/java/com/smartdocchat/
│   │   ├── controller/               # REST Endpoints (Chat Controller hỗ trợ SSE)
│   │   ├── service/                  # Core RAG, Agentic CRAG Loop & Embedding Services
│   │   ├── entity/                   # ORM Entity (PostgreSQL mapping)
│   │   ├── dto/                      # Data Transfer Objects (ChatRequest/Response)
│   │   └── config/                   # CORS, Web MVC Configurations
│   ├── src/main/resources/
│   │   └── application.yml           # Cấu hình DB, LLM Model & Web Search
│   └── pom.xml                       # Quản lý dependency Maven
├── frontend/
│   ├── src/
│   │   ├── components/               # ChatWindow, ConceptMap, DocumentList, DocumentUpload
│   │   ├── App.tsx                   # Main component tích hợp React Query
│   │   ├── index.tsx                 # Điểm đầu vào chính, khởi tạo QueryClient
│   │   └── vite-env.d.ts             # Định nghĩa kiểu cho các biến môi trường của Vite
│   ├── index.html                    # HTML Template chính (được dịch chuyển lên thư mục gốc)
│   ├── vite.config.ts                # Cấu hình Vite & Server CORS Proxy
│   └── package.json                  # Script và package dependency (TypeScript, TanStack Query)
├── llm-router/                        # FastAPI routing, provider adapters, fallback và cost logs
├── airflow/
│   └── dags/
│       └── document_etl.py           # Pipeline ETL Apache Airflow ingestion
├── eval/                              # 📊 RAG Evaluation Pipeline
│   ├── questions.json                # Bộ câu hỏi test (20 câu, 3 mức độ)
│   ├── eval.py                       # Script đánh giá tự động
│   └── results/                      # Kết quả evaluation JSON
├── data/                              # 🗂️ Intermediate Data Artifacts
│   └── sample_chunks.json            # Mẫu chunks để debug pipeline
└── docker/
    └── docker-compose.yml            # Khởi động Qdrant, PostgreSQL, Airflow, MLflow
```

---

## 🔄 Luồng Nghiệp vụ RAG Tự Phản Hồi (Self-reflective RAG In-depth)

### Quy trình Xử lý Tài liệu (Ingestion Pipeline)
1. **Upload**: Tải tài liệu định dạng `.pdf`, `.docx` hoặc `.txt` (kiểm tra loại nội dung ở backend).
2. **Parsing**: Apache PDFBox / POI phân tách cấu trúc văn bản.
3. **Hierarchical Chunking**: Cắt nhỏ văn bản thành các phân đoạn nhỏ có gối đầu để bảo toàn ngữ cảnh ngữ nghĩa.
4. **Vector Embeddings**: Gọi Ollama cục bộ với model `nomic-embed-text`.
5. **Index**: Lưu trữ các vectors vào collection riêng trong **Qdrant Vector DB**, đồng thời đồng bộ trạng thái hoàn thành và sinh executive summary của tài liệu qua PostgreSQL.

### Quy trình Trả lời Streaming & Tác nhân (Query & Self-reflective CRAG Flow)
```
[User Question]
       │
       ▼
[Initial Retrieval (Qdrant)] ──► Max Cosine Similarity Score >= 0.45?
       │                                     │
       ├──(YES: High Confidence)             ├──(NO: Low Confidence)
       │                                     │
       ▼                                     ▼
[Build RAG Prompt with Context]     [Query Reformulation (DeepSeek)]
       │                                     │
       │                                     ▼
       │                            [Parallel Re-retrieval]
       │                                     │
       │                                     ▼
       │                            [Deduplication & Reranking] ──► Score >= 0.45?
       │                                     │                           │
       │                                     ├──(YES)                    ├──(NO)
       │                                     │                           │
       │                                     ▼                           ▼
       │                            [Agentic Synthesis]         [Tavily Web Search Fallback]
       │                                     │                           │
       │                                     ▼                           ▼
       ├─────────────────────────────────────┴───────────────────────────┤
       ▼
[Ollama Streaming LLM (DeepSeek-R1)]
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

### Bước 1: Khởi động Hạ tầng Dev (PostgreSQL, Qdrant & Ollama)
Từ thư mục gốc dự án:
```bash
make dev-up
```
*Hạ tầng sẽ hoạt động tại: PostgreSQL (`localhost:5432`), Qdrant (`localhost:6333`), Ollama (`localhost:11434`) và LLM Router (`localhost:8001`). Container puller tự tải `llama3.2:3b` cùng `nomic-embed-text`.*

### Bước 2: Khởi động Backend (Spring Boot)
1. Cấu hình `LLM_BASE_URL=http://localhost:8001` khi backend chạy ngoài Docker, cùng `JWT_SECRET` và `INTERNAL_SERVICE_TOKEN` trong file `.env`. Thêm `ANTHROPIC_API_KEY` và `OPENAI_API_KEY` để bật các route cloud.
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
*   `GET /api/documents` - Lấy danh sách toàn bộ tài liệu đã được lập chỉ mục kèm theo tóm tắt và câu hỏi gợi ý.
*   `GET /api/documents/{id}` - Truy vấn trạng thái chi tiết của tệp tin.
*   `DELETE /api/documents/{id}` - Xóa tài liệu khỏi hệ cơ sở dữ liệu và thu hồi chỉ mục Vector trên Qdrant.

### 💬 API Hội thoại & Hỏi đáp (Chat & Streaming)
*   `POST /api/chat/ask` - Endpoint hỏi đáp đồng bộ truyền thống.
*   `POST /api/chat/ask-stream` - Endpoint hỏi đáp **Streaming dạng Text-Event-Stream** (Server-Sent Events).
*   `GET /api/chat/history/{sessionId}` - Tải lịch sử hội thoại của toàn bộ phiên.
*   `GET /api/chat/history/{sessionId}/{documentId}` - Lấy lịch sử hội thoại được phân tách theo tài liệu cụ thể.
*   `DELETE /api/chat/history/{sessionId}` - Xóa lịch sử phiên chat.

### 🏥 System Health & Metrics
*   `GET /api/system/health` - Kiểm tra kết nối Qdrant, Ollama và trạng thái tổng thể (public, không cần JWT).
*   `GET /api/system/metrics` - Tổng hợp RAG metrics: total requests, latency, fallback rate, error rate.

**Ví dụ output `/api/system/health`:**
```json
{
  "vector_db": "connected",
  "llm_provider": "available",
  "status": "ok"
}
```

**Ví dụ output `/api/system/metrics`:**
```json
{
  "total_requests": 1024,
  "average_latency_ms": 1350,
  "p95_latency_ms": 3200,
  "fallback_count": 42,
  "fallback_rate": 0.041,
  "stream_errors": 3,
  "error_rate": 0.003,
  "fallback_breakdown": {
    "corrective_retrieval": 28,
    "web_search": 10,
    "general_knowledge": 4
  }
}
```

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
  "model": "llama3.2:3b",
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
| `confidence` | `high` (≥0.70), `medium` (≥0.45), `low` (<0.45) |
| `ragStrategy` | `direct` / `corrective` / `web_search` / `general_knowledge` |
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

* `POST /api/auth/register` và `POST /api/auth/login` cấp JWT ký bằng secret cấu hình ổn định; login/upload/chat được rate-limit.
* Callback Airflow và `/api/actuator/prometheus` cần `INTERNAL_SERVICE_TOKEN`; chỉ health/info được public.
* Backend dùng JUnit/Mockito/Jacoco; frontend dùng Vitest + Testing Library và Playwright smoke test. GitHub Actions chạy test, build và scan image/IaC.
* Log backend ở định dạng JSON có `requestId`; Prometheus thu metrics RAG và OTLP tracing có thể xuất sang collector.
* Structured logging mỗi RAG request ghi nhận: `requestId`, `questionLen`, `retrievedDocs`, `topScore`, `model`, `strategy`, `latencyMs`, `status`.

Tài liệu vận hành: [`docs/OBSERVABILITY.md`](docs/OBSERVABILITY.md), [`docs/PERFORMANCE.md`](docs/PERFORMANCE.md) và quyết định bảo mật [`docs/adr/0001-security-boundaries.md`](docs/adr/0001-security-boundaries.md).

