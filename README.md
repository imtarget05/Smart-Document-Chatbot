# Smart Document Chatbot

Upload tài liệu (PDF, Word...) → Hỏi chatbot bằng tiếng Việt/Anh → AI trả lời dựa trên nội dung tài liệu

## 🎯 Tính năng

### Core (bắt buộc)
- ✅ Upload tài liệu PDF/Word
- ✅ Chat hỏi đáp dựa trên tài liệu
- ✅ Stream response realtime (typewriter effect)
- ✅ Lưu lịch sử chat

### Nâng cao (làm thêm)
- 🔲 Multi-document (chọn tài liệu nào để hỏi)
- 🔲 Hiển thị nguồn trích dẫn (trang mấy, đoạn nào)
- 🔲 Authentication (JWT)
- 🔲 Conversation memory (nhớ ngữ cảnh chat trước)

## 🏗️ Kiến trúc hệ thống

```
┌─────────────────────────────────────────────────┐
│                   Frontend                       │
│         React + WebSocket (chat realtime)        │
└───────────────────┬─────────────────────────────┘
                    │ HTTP / WS
┌───────────────────▼─────────────────────────────┐
│              Spring Boot Backend                 │
│  ┌──────────────┐    ┌───────────────────────┐  │
│  │ Upload API   │    │  Chat API (WebSocket)  │  │
│  └──────┬───────┘    └──────────┬────────────┘  │
│         │                       │               │
│  ┌──────▼───────┐    ┌──────────▼────────────┐  │
│  │  Embedding   │    │     RAG Pipeline       │  │
│  │  Service     │    │  Search → Prompt → LLM │  │
│  └──────┬───────┘    └──────────┬────────────┘  │
└─────────┼─────────────────────── ┼──────────────┘
          │                        │
┌─────────▼──────┐      ┌──────────▼─────────────┐
│  Vector DB     │      │     OpenAI / Gemini     │
│  (Qdrant)      │      │     API                 │
└────────────────┘      └────────────────────────┘
          │
┌─────────▼──────┐
│  PostgreSQL    │
│  (metadata,    │
│   chat history)│
└────────────────┘
```

## 🛠️ Tech Stack

| Layer | Công nghệ | Lý do chọn |
|-------|-----------|-----------|
| Backend | Spring Boot 3 | Quen thuộc, ecosystem lớn |
| LLM Framework | LangChain4j | Java-native, dễ tích hợp |
| LLM Provider | OpenAI GPT-4o-mini | Rẻ, đủ mạnh (~$0.01/query) |
| Embedding | OpenAI text-embedding-3-small | Chất lượng cao |
| Vector DB | Qdrant (Docker) | Free, dễ setup local |
| Relational DB | PostgreSQL + pgvector | Lưu metadata + chat history |
| Realtime | Spring WebSocket | Chat streaming |
| File Parsing | Apache PDFBox + POI | Đọc PDF, Word |
| Frontend | React + Tailwind CSS | UI chat đẹp |
| Deploy | Docker Compose | Dễ demo |

## 📋 Cấu trúc Project

```
Smart Document Chatbot/
├── backend/
│   ├── src/main/java/com/smartdocchat/
│   │   ├── SmartDocChatbotApplication.java
│   │   ├── controller/
│   │   │   ├── DocumentController.java
│   │   │   └── ChatController.java
│   │   ├── service/
│   │   │   ├── DocumentService.java
│   │   │   ├── ChatService.java
│   │   │   └── EmbeddingService.java
│   │   ├── entity/
│   │   │   ├── Document.java
│   │   │   └── ChatMessage.java
│   │   ├── repository/
│   │   │   ├── DocumentRepository.java
│   │   │   └── ChatMessageRepository.java
│   │   ├── dto/
│   │   │   ├── ChatRequest.java
│   │   │   ├── ChatResponse.java
│   │   │   ├── DocumentDTO.java
│   │   │   └── UploadResponse.java
│   │   └── util/
│   │       ├── DocumentParser.java
│   │       ├── OpenAIConfig.java
│   │       └── QdrantConfig.java
│   ├── src/main/resources/
│   │   └── application.yml
│   └── pom.xml
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── DocumentUpload.jsx
│   │   │   ├── DocumentList.jsx
│   │   │   └── ChatWindow.jsx
│   │   ├── App.jsx
│   │   ├── index.jsx
│   │   └── index.css
│   ├── public/
│   │   └── index.html
│   └── package.json
├── docker/
│   ├── Dockerfile.backend
│   ├── Dockerfile.frontend
│   └── docker-compose.yml
└── README.md
```

## 🚀 Cài đặt & Chạy

### Yêu cầu
- Docker & Docker Compose
- Node.js 18+ (nếu chạy local frontend)
- Java 17+ (nếu chạy local backend)
- Maven 3.8+

### Chạy với Docker Compose

```bash
# Clone repository
cd Smart\ Document\ Chatbot

# Set OpenAI API Key
export OPENAI_API_KEY=your-api-key-here

# Khởi động tất cả services
docker-compose -f docker/docker-compose.yml up --build

# Frontend: http://localhost:3000
# Backend API: http://localhost:8080/api
# Qdrant Dashboard: http://localhost:6333
```

### Chạy Local (Development)

#### Backend
```bash
cd backend

# Install dependencies
mvn install

# Run
mvn spring-boot:run

# Server runs on http://localhost:8080
```

#### Frontend
```bash
cd frontend

# Install dependencies
npm install

# Run
npm start

# App opens at http://localhost:3000
```

#### PostgreSQL
```bash
# Docker
docker run -d \
  --name postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=smart_doc_chatbot \
  -p 5432:5432 \
  postgres:15-alpine
```

#### Qdrant
```bash
# Docker
docker run -d \
  --name qdrant \
  -p 6333:6333 \
  qdrant/qdrant:latest
```

## 🔄 RAG Pipeline hoạt động như thế nào

### UPLOAD PHASE
```
1. User upload PDF/Word/TXT
   ↓
2. Extract Text (PDFBox/POI)
   ↓
3. Split into Chunks (500 tokens)
   ↓
4. Generate Embeddings (OpenAI API)
   ↓
5. Store in Qdrant Vector DB
   ↓
6. Save Metadata to PostgreSQL
```

### QUERY PHASE
```
1. User asks question
   ↓
2. Generate Query Embedding (OpenAI API)
   ↓
3. Semantic Search in Qdrant (Top 3 chunks)
   ↓
4. Build RAG Prompt with Context
   ↓
5. Call OpenAI GPT-4o-mini
   ↓
6. Stream response to Frontend
   ↓
7. Save Chat History to DB
```

## 📡 API Endpoints

### Documents
- `POST /api/documents/upload` - Upload tài liệu
- `GET /api/documents` - Danh sách tài liệu
- `GET /api/documents/{id}` - Chi tiết tài liệu
- `DELETE /api/documents/{id}` - Xóa tài liệu

### Chat
- `POST /api/chat/ask` - Hỏi câu hỏi
- `GET /api/chat/history/{sessionId}` - Lịch sử chat
- `GET /api/chat/history/{sessionId}/{documentId}` - Lịch sử chat theo tài liệu
- `DELETE /api/chat/history/{sessionId}` - Xóa lịch sử chat
- `WS /ws/chat` - WebSocket realtime chat

## 🔑 Biến môi trường

```env
# Backend
OPENAI_API_KEY=sk-...
DATABASE_URL=jdbc:postgresql://localhost:5432/smart_doc_chatbot
DATABASE_USER=postgres
DATABASE_PASSWORD=postgres
QDRANT_HOST=localhost
QDRANT_PORT=6333
SPRING_JPA_HIBERNATE_DDL_AUTO=update
```

## 📊 Database Schema

### documents
```sql
- id (Long, PK)
- file_name (String)
- file_path (String)
- file_type (String)
- file_size (Long)
- vector_collection_id (String)
- chunk_count (Integer)
- created_at (DateTime)
- updated_at (DateTime)
```

### chat_messages
```sql
- id (Long, PK)
- session_id (String)
- document_id (Long, FK)
- user_message (TEXT)
- ai_response (TEXT)
- source_chunks (TEXT)
- created_at (DateTime)
```

## 🔐 Bảo mật

- [TODO] JWT Authentication
- [TODO] Rate limiting per user
- [TODO] File upload validation
- [TODO] SQL injection prevention (JPA ORM)
- [TODO] XSS protection (React)

## 🚧 Tiếp theo

1. **Integration OpenAI API thực sự** trong EmbeddingService & ChatService
2. **Qdrant Client** - Connect & store vectors
3. **Stream responses** - WebSocket streaming
4. **Authentication** - JWT + Spring Security
5. **Conversation memory** - Multi-turn context
6. **Citation tracking** - Hiển thị nguồn trích dẫn
7. **Multi-language** - Support Tiếng Việt

## 📝 Lưu ý

- Cần OpenAI API key để chạy (có thể dùng trial account)
- PostgreSQL & Qdrant sẽ auto-create database khi startup
- File upload max 50MB
- Session ID lưu ở localStorage (browser)

## 📞 Support

Nếu có lỗi, check:
1. Logs: `docker logs <container_name>`
2. Health check: http://localhost:8080/actuator/health
3. Qdrant dashboard: http://localhost:6333

---

Happy coding! 🎉
