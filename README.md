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
| **AI LLM Runtime** | Ollama + DeepSeek-R1 | Chạy mô hình `deepseek-r1:1.5b` cục bộ trong Docker, không yêu cầu API key nhà cung cấp AI. |
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
├── airflow/
│   └── dags/
│       └── document_etl.py           # Pipeline ETL Apache Airflow ingestion
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
*Hạ tầng sẽ hoạt động tại: PostgreSQL (`localhost:5432`), Qdrant (`localhost:6333`) và Ollama (`localhost:11434`). Container puller tự tải `deepseek-r1:1.5b` cùng `nomic-embed-text`.*

### Bước 2: Khởi động Backend (Spring Boot)
1. Cấu hình `OLLAMA_BASE_URL=http://localhost:11434` khi backend chạy ngoài Docker, cùng `JWT_SECRET` và `INTERNAL_SERVICE_TOKEN` trong file `.env`. Model AI chạy cục bộ và không cần API key.
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

---

## Security, Testing & Operations

* `POST /api/auth/register` và `POST /api/auth/login` cấp JWT ký bằng secret cấu hình ổn định; login/upload/chat được rate-limit.
* Callback Airflow và `/api/actuator/prometheus` cần `INTERNAL_SERVICE_TOKEN`; chỉ health/info được public.
* Backend dùng JUnit/Mockito/Jacoco; frontend dùng Vitest + Testing Library và Playwright smoke test. GitHub Actions chạy test, build và scan image/IaC.
* Log backend ở định dạng JSON có `requestId`; Prometheus thu metrics RAG và OTLP tracing có thể xuất sang collector.

Tài liệu vận hành: [`docs/OBSERVABILITY.md`](docs/OBSERVABILITY.md), [`docs/PERFORMANCE.md`](docs/PERFORMANCE.md) và quyết định bảo mật [`docs/adr/0001-security-boundaries.md`](docs/adr/0001-security-boundaries.md).
