# Agent Architecture (Python LangGraph Service)

> **Trạng thái trung thực:** Python LangGraph Agent Service là một dịch vụ AI
> **thử nghiệm chạy song song** với sản phẩm chính. Nó có đầy đủ endpoint riêng
> (`/v1/agent/*` trên cổng 9000) và toàn bộ code hoạt động thật (LangGraph,
> retrieval Qdrant, memory, security), **nhưng chưa được nối vào luồng chat
> chính của sản phẩm**: Spring Boot và nginx không gọi dịch vụ này. Luồng
> sản phẩm chính là Spring Boot CRAG trên PostgreSQL chunks (xem README).

## Vai trò hai dịch vụ

| Dịch vụ | Vai trò | Trạng thái |
|---|---|---|
| Spring Boot (`:8080`) | Auth JWT, owner isolation, document CRUD, chat CRAG, SSE streaming, persistence | **Product path (đã nối)** |
| Python Agent (`:9000`) | LangGraph multi-agent, RAG Qdrant, connector ingestion, report/action, evaluation | **Prototype / experimental (chưa nối)** |

## Python Agent Service

Flow nội bộ (khi gọi trực tiếp `/v1/agent/invoke`):

```text
Request
  -> Prompt-injection + input guardrails (block HIGH, sanitize MEDIUM)
  -> Short/long-term memory load
  -> LangGraph StateGraph:
       orchestrator -> (rag | engineering | comparator | researcher | action | report | ingestion)
  -> Tool calls: Qdrant hybrid search, Tavily web search
  -> Output guardrails + SSE streaming
```

### Các thành phần

- `graph/workflow.py` — LangGraph StateGraph thật (import `langgraph`),
  wiring orchestrator + 7 specialist agents còn lại qua conditional edges.
- `agents/` — 9 file agent: orchestrator + 7 agents gắn vào graph
  (rag, engineering, comparator, researcher, action, report, ingestion)
  và `cskh_agent.py` **chưa được dùng** (orphan — không phải graph node).
- `security/prompt_injection.py` + `guardrails.py` — bảo vệ thật, chạy trên
  mọi entry point.
- `memory/` — long-term (asyncpg/PostgreSQL), short-term, context summarizer,
  VI-EN language handler — đều được dùng bởi rag_agent.
- `connectors/` — Gmail/Google Drive/Slack dùng SDK thật; SharePoint mặc định
  mock mode (`sharepoint_mock_enabled=true`).
- `eval_framework/`, `benchmark/` — chạy như router `/eval/*`, `/benchmark/*`.

### ADK / A2A / MCP — custom implementations (KHÔNG phải SDK chính thức)

Các module này lấy cảm hứng từ khái niệm của Google ADK, A2A và MCP nhưng là
code tự viết, **không** dùng `google.adk`, `mcp` SDK hay JSON-RPC A2A chính
thức — không có package tương ứng trong `requirements.txt`. Chúng chỉ được gọi
qua các endpoint demo riêng (`/v1/agent/adk/demo`, `/v1/a2a/*`, `/v1/mcp/*`)
và không nằm trong invoke path. Khi trình bày, hãy mô tả đúng:

> "Tôi xây lớp orchestration tùy chỉnh lấy cảm hứng từ các mẫu agent hiện đại
> (ADK/A2A/MCP concepts), không phải triển khai chính thức các giao thức đó."

### Connector Ingestion Flow (chỉ qua endpoint riêng)

```text
Google Drive / Gmail / Slack / SharePoint
  -> Connector fetch_documents()
  -> IngestionAgent -> ConnectorIngestionPipeline
  -> chunk -> embed (LLM Router / Ollama) -> upsert Qdrant (collection per user+doc hash)
```

Endpoint: `POST /v1/agent/connector/ingest` (trực tiếp trên agent:9000).

### Evaluation

- `eval/eval.py` — đánh giá classic `/chat/ask` (Spring Boot).
- `eval/agent_eval.py` — đánh giá `/v1/agent/invoke` (intent routing, retrieval
  accuracy, answer completeness, hallucination, latency, citation rate).
- `agent/eval_framework/` — suite cases (answer quality, hallucination,
  retrieval quality, robustness, security, cost, latency).

## Interview Positioning

- Java Spring Boot là product/API layer: auth, ownership, CRAG, persistence,
  stable user-facing APIs.
- Python LangGraph là AI agent layer thử nghiệm: multi-agent, connector
  ingestion, evaluation — sẵn sàng nối vào product khi có nhu cầu thực.