# CV AUDIT FULL REPORT — MAI NGUYEN BINH TAN
## Vai trò: Senior AI Engineer / Tech Lead @ AI Power
## Mục tiêu: Kiểm tra khắt khe CV ứng viên AI Engineer Intern

---

# PHẦN 1: MAPPING JD → CV

| JD Requirement | CV đã chứng minh? | Evidence | Mức độ (0-100%) | Thiếu gì |
|---|---|---|---|---|
| **Python** | ✅ Có | agent/adk_agent.py, toàn bộ agent/agents/*, tools/* viết bằng Python. Có async/await, dataclass, enum, type hints. | 85% | Chưa thấy code xử lý GIL, multiprocessing, profiling performance |
| **LLM** | ✅ Có | LangChain ChatOllama (llm_factory.py), gọi model local qua Ollama. Có retry, temperature config. | 70% | Chỉ dùng LangChain wrapper, chưa thấy direct API call, chưa thấy xử lý tokenization, context window tối ưu |
| **NLP** | △ Làm sơ | detect_language trong language_handler.py, context_summarizer có summarize conversation. | 35% | Ngôn ngữ detection dùng word set matching (rule-based), không có NLP cổ điển (tokenizer, POS tagging, NER, dependency parsing). Chỉ dùng LLM cho mọi thứ. |
| **ADK (Agent Dev Kit) — JD nói "hiểu biết"** | ❌ KHÔNG ĐÚNG | adk_agent.py dòng 2-16 tự nhận: "self-built, inspired by Google ADK, NOT the official Google ADK library" | 30% hiểu biết (self-built), 0% nếu claim là "implemented Google ADK" | **CV nói "implemented ADK" nhưng thực tế là tự viết lại từ đầu**. JD chỉ yêu cầu "hiểu biết" — nếu CV ghi đúng là "custom ADK-inspired" thì không vấn đề. |
| **A2A — JD nói "là lợi thế"** | ❌ KHÔNG CÓ | Trong source code KHÔNG có file nào tên a2a_protocol, A2AProtocolHub, CircuitBreaker, DeadLetterQueue. | 0% | **Tuyên bố trong CV KHÔNG có trong source code.** |
| **Git** | ✅ Có | git repo với commit history, .gitignore | 60% | Chỉ có cơ bản. Chưa thấy branching strategy, git flow, conventional commits, CI/CD integration |
| **Docker** | ✅ Có | Dockerfile ở agent/, docker/, docker-compose files | 75% | Multi-stage build chưa tối ưu, thiếu healthcheck, security scan |
| **Linux** | ✅ Có | Makefile, shell scripts (deploy.sh, health-check.sh) | 60% | Kiến thức cơ bản, chưa thấy kernel, namespace, cgroups, systemd |
| **GPU** | △ Làm sơ | CV ghi "GPU inference" với Ollama, file eval/ có quantization_measurement.py | 40% | Chưa thấy code CUDA, trực tiếp quản lý GPU memory, TensorRT, vLLM |
| **Deploy** | △ Làm sơ | Có docker-compose, scripts/deploy.sh, k8s/ | 45% | Deployment script cơ bản. Thiếu blue/green, canary, rollback strategy chi tiết |
| **Prompt Engineering** | ✅ Có | System prompts trong orchestrator.py, rag_agent.py, engineering_analysis_agent.py | 70% | Prompt tốt nhưng thiếu systematic evaluation, A/B testing, versioning cho prompt |
| **Vector Database** | ✅ Có | qdrant_tool.py: semantic search với Qdrant, hybrid search | 80% | Chưa thấy index optimization, payload indexing, collection management |
| **Session Memory** | ✅ Có | ShortTermMemory trong memory/short_term.py | 75% | In-memory, không persistent, không distributed |
| **Context Summarization** | ✅ Có | ContextSummarizer trong memory/context_summarizer.py | 70% | Còn đơn giản: chỉ summarize khi quá threshold, không có hierarchical summarization |
| **Training Pipeline (JD yêu cầu)** | ❌ CHƯA | Training.ipynb có nhưng chưa đọc. agent/ không có training pipeline. | 10% | JD yêu cầu "xây dựng pipeline huấn luyện, deploy mô hình" — không có evidence |
| **Fine-tuning (JD yêu cầu)** | ❌ CHƯA | CV ghi LoRA nhưng source code không có LoRA implementation. | 0% | **Không có evidence trong codebase** |
| **LoRA** | ❌ CHƯA | Giống fine-tuning | 0% | **Không có evidence trong codebase** |
| **Multi Agent** | ✅ Có | orchestrator.py routing tới 7 agents: rag, report, compare, research, action, engineering, adk | 80% | Orchestrator đơn giản (1-level routing), không có hierarchical, negotiation, delegation |
| **RAG** | ✅ Có | rag_agent.py: Corrective RAG loop, hybrid search, reranking | 85% | Thiếu evaluation metric cho RAG quality |
| **Tool Calling** | ✅ Có | ADKToolRegistry trong adk_agent.py. Tools: web_search, qdrant_tool, notification_tool | 75% | Tool calling còn đơn giản, không có dynamic tool creation, tool chaining |
| **REST API** | △ Làm sơ | backend/ có Spring Boot (pom.xml), agent/ có FastAPI (main.py) | 65% | Chưa thấy API design document, versioning strategy, rate limiting |
| **FastAPI** | △ Làm sơ | agent/main.py (chưa đọc) | 50% | Cần xem thêm file để đánh giá |
| **Spring Boot** | △ Làm sơ | backend/pom.xml | 50% | Cần xem thêm backend source |
| **Redis** | ✅ Có | qdrant_tool.py dùng Redis để cache | 60% | Chỉ dùng làm cache, chưa dùng Redis Stream, Pub/Sub, distributed lock |
| **PostgreSQL** | ✅ Có | long_term.py dùng asyncpg với PostgreSQL | 75% | Connection pooling cơ bản, chưa có migration, indexing strategy |
| **Qdrant** | ✅ Có | qdrant_tool.py: semantic search | 80% | Chưa thấy collection management, snapshot, cluster config |
| **Ollama** | ✅ Có | llm_factory.py dùng ChatOllama | 75% | Chưa thấy multi-model routing, model warm-up, concurrent request handling |
| **On-prem (JD yêu cầu)** | △ Làm sơ | docker-compose cho local deployment | 40% | Thiếu hardware requirement, scaling strategy, backup/recovery |
| **MCP** (CV ghi) | ❌ CHƯA XÁC ĐỊNH | CV ghi "MCP (Model Context Protocol)" trong skills. **Không có file/class nào implement MCP protocol trong codebase** | 0% | Không có evidence MCP được implement |
| **WebSocket / SSE** (CV ghi) | ❌ CHƯA XÁC ĐỊNH | CV ghi "WebSocket, SSE" trong skills. agent/main.py chưa review, frontend/ chưa review | 50% | Chưa có evidence WebSocket/SSE implementation trong agent code |
| **Prometheus / Observability** (CV ghi) | △ Làm sơ | docker/monitoring/prometheus.yml, docker/monitoring/grafana/ tồn tại | 50% | Có config nhưng chưa thấy Prometheus metrics được expose từ Python agent code, chưa có custom metrics |
| **Java / TypeScript / JavaScript** (CV ghi) | △ Có | backend/ (Java Spring Boot), frontend/ (React TypeScript) | 60% | Chưa review code quality ở backend, frontend |
| **Finance knowledge** (JD ghi "lợi thế") | △ Làm sơ | ADKAgentFactory.create_finance_agent() có implement indicators (SMA, RSI, MACD) | 40% | Chỉ có tool definitions, chưa có actual calculation implementation |

---

# PHẦN 2: AUDIT TỪNG PROJECT

## Project 1: Smart Document Chatbot (Agentic CRAG Platform)

### 2.1. Kiến trúc

| Mục | Đánh giá | Giải thích |
|---|---|---|
| Kiến trúc | ✅ Đã làm | LangGraph StateGraph với orchestrator routing tới 7 agents. START → orchestrator → [agent] → END |
| Data Flow | △ Làm sơ | Query → Orchestrator → Agent → Retrieval → LLM → Response. CRAG loop có reformulate, rerank. Thiếu data flow diagram trong docs. |
| Công nghệ | ✅ Đã làm | React, TS, Spring Boot 3, Python, LangGraph, Qdrant, Ollama, PostgreSQL, Docker |
| Module | ✅ Đã làm | agent/agents/*, agent/memory/*, agent/tools/*, agent/graph/* |
| API | △ Làm sơ | API docs (API.md) tồn tại. Chưa có OpenAPI/Swagger spec đầy đủ. agent/main.py chưa review. |
| Database | ✅ Đã làm | PostgreSQL (long_term), Qdrant (vector), Redis (cache) |
| Agent | ✅ Đã làm | 7 agents: RAG, Report, Compare, Research, Action, Engineering Analysis, CSKH |
| Prompt | ✅ Đã làm | System prompt cho mỗi agent, được thiết kế rõ ràng |
| Memory | ✅ Đã làm | ShortTerm (in-memory deque), LongTerm (PostgreSQL), ContextSummarizer |
| Deployment | △ Làm sơ | Docker, docker-compose, deploy script. Thiếu k8s production-grade. |
| Monitoring | △ Làm sơ | Prometheus, Grafana config có trong docker/monitoring/. Chưa có alerting rules meaningful. |
| Logging | ✅ Đã làm | Python logging module, structured logs |
| Docker | ✅ Đã làm | Dockerfile, docker-compose cho dev, mlops, monitoring |
| Git | ✅ Đã làm | Git repo, .gitignore |
| Security | ❌ Chưa làm | Không có authentication/authorization trong Python agent code, API key check thiếu, không có input sanitization, prompt injection protection |
| Session | ✅ Đã làm | ShortTermMemory per session_id |
| Context | ✅ Đã làm | ContextSummarizer compress history, long-term facts |
| Tool Calling | ✅ Đã làm | ADKToolRegistry với discover, invoke, timeout, retry |
| Error Handling | △ Làm sơ | Try-catch trong agent.run(), retry logic trong tool invoke. Thiếu global exception handler, graceful degradation. |
| Performance | ❌ Chưa làm | Không có benchmark numbers, latency metrics, throughput testing trong code |
| Multi-lingual | ✅ Đã làm | language_handler.py: detect_language() dùng Vietnamese word set + diacritic detection, get_language_instruction() tạo prompt instruction |

### Kết luận Project 1: **△ Trung bình khá.** Kiến trúc tốt, implement hoàn chỉnh các module chính. Nhưng thiếu security, performance testing, evaluation metrics.

---

## Project 2: Personal AI Platform (Multi-Agent System Engineer)

| Mục | Đánh giá | Giải thích |
|---|---|---|
| Kiến trúc | ❌ **VẤN ĐỀ** | **ADK (Agent Dev Kit)**: source code trong adk_agent.py TỰ NHẬN là "self-built, inspired by Google ADK, NOT the official Google ADK". CV ghi "Implemented Google ADK" là sai lệch. |
| A2A Protocol | ❌ **KHÔNG CÓ** | **A2AProtocolHub, CircuitBreaker, DeadLetterQueue KHÔNG TỒN TẠI trong codebase.** Đây là tuyên bố không có evidence. |
| Data Flow | ❌ KHÔNG RÕ | Các file adk_runtime.py chỉ có 5-step demo workflow giả lập (hardcoded response), không có thực sự gọi LLM |
| Công nghệ | △ Một phần | Python, FastAPI, ADK (tự viết), LangGraph, Ollama, Docker, PostgreSQL, Redis, Git |
| Module | △ Một phần | agent/adk_agent.py có ADKAgentConfig, ADKToolRegistry, ADKQueryParser, ADKAgentFactory |
| Tool Calling | ✅ Đã làm | ADKToolRegistry: register, discover, invoke với retry + timeout |
| Circuit Breaker | ❌ **KHÔNG CÓ** | Từ khóa "CircuitBreaker" không xuất hiện trong codebase |
| Dead Letter Queue | ❌ **KHÔNG CÓ** | Từ khóa "DeadLetterQueue" không xuất hiện trong codebase |
| 22+ agents | ❌ **KHÔNG CÓ** | Chỉ có 7 agents trong project 1 + 4 agents default trong ADK system + CSKH agent = ~12 agents, không phải 22+ |
| Auto-improvement | ❌ **KHÔNG CÓ** | "generate → evaluate → improve → notify Slack" không có trong codebase |
| Model Quantization | △ Làm sơ | eval/quantization_measurement.py có nhưng chưa đọc |
| MCP Protocol | ❌ **KHÔNG CÓ** | CV ghi "MCP (Model Context Protocol)" trong skills. Không có implementation trong codebase |

### Kết luận Project 2: **❌ Nghiêm trọng.** CV phóng đại đáng kể. ADK là self-built chứ không phải Google ADK. A2A, CircuitBreaker, DeadLetterQueue, 22+ agents, auto-improvement pipeline, MCP KHÔNG có trong source code.

---

# PHẦN 3: ĐI SÂU TỪNG DÒNG CV

### "Built multi-agent systems with LangGraph (7 specialized agents)"

✅ **Có evidence** nhưng cần clarify.
- Code (workflow.py): đúng có 7 agents routing: rag, report, compare, research, action, engineering, adk
- NHƯNG: "adk" node là fallback demo, không phải agent thật. EngineeringAnalysisAgent chỉ hoạt động nếu có document_ids.
- **Câu hỏi interviewer sẽ hỏi:** 
  - Agents giao tiếp với nhau như thế nào? → Không có, chỉ có orchestrator routing 1-level.
  - Agent nào gọi agent nào? → Không có.
  - Có shared state không? → Có AgentState nhưng chia sẻ qua dictionary.
  - Agent conflict resolution thế nào? → Không có.
  - Agent priority? → Không có.

### "Implemented ADK (Agent Development Kit) framework with tool calling and structured output"

❌ **ADK là self-built.**
- Code: adk_agent.py comment dòng 2-16: "self-built, inspired by Google ADK patterns... not the official Google ADK library"
- **Đây là misrepresentation** — không thể gọi là "Implemented ADK" khi tự viết lại.
- **ADK thật của Google:** Agent class, ToolContext, LlmAgent, AgentCallbacks, session management, ApisApiSpec, code execution. Code hiện tại không có những thứ này.

### "Built A2A (Agent-to-Agent) Protocol: A2AProtocolHub for agent discovery, capability indexing, and task delegation"

❌ **KHÔNG CÓ trong source code.**
- Search toàn bộ codebase: không có file/class/function nào tên A2AProtocolHub, CircuitBreaker, DeadLetterQueue.
- **Đây là fabrication** trừ khi code ở repo khác.

### "CircuitBreaker auto-stops calling failing agents"

❌ KHÔNG CÓ.
- Không có file nào implement circuit breaker pattern (status tracking, failure threshold, half-open state, recovery).

### "DeadLetterQueue stores failed tasks for retry"

❌ KHÔNG CÓ.
- Không có queue mechanism nào cho failed tasks.

### "Deployed local LLM inference with Ollama (Llama 3.2, Qwen 2.5, DeepSeek) with model quantization"

△ **Có Ollama, không có evidence quantization.**
- llm_factory.py: gọi ChatOllama(base_url, model, temperature). Chỉ là wrapper.
- eval/quantization_measurement.py có thể đánh giá quantization nhưng chưa đọc.
- **Không có code nào show cách quantize model thực tế.**
- Các model name (Llama 3.2, Qwen 2.5, DeepSeek) chỉ là strings trong config.

### "Developed 22+ specialized agents with auto-improvement pipeline: generate → evaluate → improve → notify Slack"

❌ KHÔNG CÓ.
- Tổng số agents trong codebase: 7 project 1 + 4 ADK default + CSKH = ~12, không phải 22+.
- Pipeline "generate → evaluate → improve → notify Slack" không tồn tại.
- **Câu hỏi:** "Em hãy show tôi 22 agents đang ở đâu?" → Không thể.

### "Developed multi-lingual chat with session persistence, context summarization, and long-term memory"

✅ **CÓ EVIDENCE.**
- Session: ShortTermMemory với session_id
- Multilingual: language_handler.py detect_language() dùng word set matching + diacritic detection
- Context summarization: ContextSummarizer (compress khi quá threshold)
- Long-term memory: LongTermMemory với PostgreSQL

### "Implemented Corrective RAG loop: confidence evaluation → query reformulation → web search fallback → streaming response"

✅ **CÓ EVIDENCE** (trừ streaming).
- Confidence threshold: 0.45 (rag_agent.py dòng 30)
- Query reformulation: _reformulate_query() dùng LLM
- Web search fallback: _web_search_fallback() dùng Tavily
- CRAG loop: _crag_loop() gọi parallel re-retrieval
- NHƯNG: **không có streaming response.** Response được build đầy đủ rồi mới trả về.

### "Google IT Automation with Python / Introduction to Git and GitHub / TOEIC 4 Skills: 805"

✅ **Chứng chỉ — không kiểm tra được từ codebase.** Đây thường là Coursera certificates, OK cho Intern.

### Skills section: "MCP (Model Context Protocol)"

❌ **KHÔNG CÓ EVIDENCE.**
- MCP là protocol để LLM gọi tools do Anthropic giới thiệu. 
- **Không có file nào implement MCP server, MCP tool definitions, MCP client trong codebase.**
- **Câu hỏi:** "MCP spec version bao nhiêu? Có những transport types nào?" → Nếu không trả lời được thì chưa hiểu MCP.

### Skills section: "WebSocket, SSE"

△ **Chưa có evidence cụ thể trong agent Python code.**
- Có thể có trong backend Spring Boot hoặc frontend React. Chưa review.

### Skills section: "Prometheus"

△ **Có config file** (docker/monitoring/prometheus.yml) nhưng chưa thấy Python agent expose Prometheus metrics (/metrics endpoint).

---

# PHẦN 4: ĐI SÂU THEO CÔNG NGHỆ

## LangGraph

**Kiểm tra:** `from langgraph.graph import END, START, StateGraph`
- Sử dụng StateGraph, add_node, add_edge, add_conditional_edges, graph.compile()
- **ĐÁNH GIÁ:** Hiểu cơ bản về LangGraph. Tuy nhiên chỉ dùng 1-level routing.
- **Câu hỏi:** Tại sao dùng StateGraph thay vì MessageGraph? → Không có answer trong code.
- **Câu hỏi:** LangGraph checkpointing? Persistence? → Không dùng.
- **Điểm:** 7/10

## LangChain

**Kiểm tra:** `from langchain_core.messages import HumanMessage, SystemMessage`, `from langchain_ollama import ChatOllama`
- Dùng LangChain để gọi LLM và quản lý messages
- **ĐÁNH GIÁ:** Hiểu cơ bản. Chưa dùng LangChain Expression Language (LCEL), RunnablePassthrough, RunnableParallel
- **Điểm:** 6/10

## ADK

**Kiểm tra:** `agent/adk_agent.py`
- **VẤN ĐỀ:** Code tự nhận là self-built, không phải Google ADK
- So sánh với Google ADK thật (Agent class, ToolContext, session management) → code hiện tại thiếu hầu hết
- **Điểm:** 3/10 (vì misrepresentation)
- **Nếu sửa CV thành "built custom ADK-inspired framework":** 7/10

## A2A

**Kiểm tra:** **KHÔNG CÓ trong codebase**
- **Điểm:** 0/10

## MCP (Model Context Protocol)

**Kiểm tra:** **KHÔNG CÓ TRONG CODEBASE**
- Không có MCP server, MCP tool, MCP client, MCP transport implementation
- **Điểm:** 0/10

## FastAPI

**Chưa đọc đủ file.** Tạm thời chưa đánh giá.

## Spring Boot

**Chưa đọc đủ file.** Có backend/pom.xml nhưng chưa review source.

## Redis

**Kiểm tra:** `import redis`, `redis.from_url(settings.redis_url)`
- Dùng để cache RAG queries (setex, get)
- **ĐÁNH GIÁ:** Chỉ dùng cơ bản. Không dùng Redis Stream, Pub/Sub, distributed lock
- **Điểm:** 5/10

## Qdrant

**Kiểm tra:** `QdrantHybridSearch` trong qdrant_tool.py
- Search points với vector, payload, limit
- Hybrid search + BM25 + RRF
- **ĐÁNH GIÁ:** Tốt. Nhưng chưa có collection management, snapshot, cluster
- **Điểm:** 7/10

## Docker

**Kiểm tra:** Dockerfile.monolith, docker/ các file compose
- Multi-stage build, docker-compose
- **ĐÁNH GIÁ:** Cơ bản. Thiếu healthcheck, non-root user, security scan
- **Điểm:** 6/10

## Git

**Kiểm tra:** Git history, .gitignore
- **ĐÁNH GIÁ:** Cơ bản. Không có branching strategy, conventional commits
- **Điểm:** 5/10

## Python

**Kiểm tra:** `async/await`, `dataclass`, `Enum`, type hints, logging
- Có async programming, structured code
- **ĐÁNH GIÁ:** Python intermediate. Chưa thấy context manager, decorator pattern, metaprogramming
- **Điểm:** 7/10

## Ollama

**Kiểm tra:** `ChatOllama(base_url, model, temperature)`
- **ĐÁNH GIÁ:** Cơ bản. Chỉ dùng wrapper.
- **Điểm:** 6/10

## LLM

**Kiểm tra:** Gọi LLM qua LangChain/LangChain Ollama, temperature config, retry logic
- **ĐÁNH GIÁ:** Hiểu cơ bản. Thiếu direct API call, context window optimization, token management
- **Điểm:** 6/10

## RAG

**Kiểm tra:** Hybrid search, CRAG loop, reranking, citations
- **ĐÁNH GIÁ:** Implement tốt multiple RAG patterns
- **Điểm:** 8/10

## Prompt Engineering

**Kiểm tra:** System prompts trong orchestrator.py, rag_agent.py
- **ĐÁNH GIÁ:** Prompt có structure, instruction, examples. Thiếu versioning, evaluation
- **Điểm:** 7/10

## Embedding

**Kiểm tra:** `_embed` method trong qdrant_tool.py
- Gọi `/api/embeddings` endpoint
- **ĐÁNH GIÁ:** Cơ bản. Chưa có embedding caching, batch processing, model selection strategy
- **Điểm:** 5/10

## Vector Search

**Kiểm tra:** Qdrant search với cosine similarity payload
- **ĐÁNH GIÁ:** Có semantic + BM25 hybrid search
- **Điểm:** 7/10

## Language Detection (Vietnamese-English)

**Kiểm tra:** `language_handler.py` (71 dòng)
- detect_language(): rule-based using Vietnamese word set (97 words + 31 non-diacritic variants) + diacritic detection
- get_language_instruction(): returns prompt instruction for LLM
- **ĐÁNH GIÁ:** Rule-based approach là đủ cho use case. Không phải NLP model-based detection.
- **Câu hỏi:** "Nếu user gõ 'toi muon tim hieu ve AI' (không dấu), detect_language có hoạt động không?" → Có, vì có non-diacritic variants list.
- **Điểm:** 6/10

## LoRA / Fine-tuning / GPU

❌ **KHÔNG CÓ EVIDENCE trong codebase.**
- LoRA skills ghi trong CV nhưng không có implementation
- Fine-tuning pipeline không có trong codebase

## WebSocket / SSE

❌ **CHƯA XÁC NHẬN trong codebase đã review.**
- Không có evidence trong Python agent code
- Có thể có trong backend Spring Boot hoặc frontend

## Prometheus / Observability

△ **Có config, chưa thấy integration trong code.**
- docker/monitoring/prometheus.yml: scrape config
- docker/monitoring/grafana/: dashboard config
- NHƯNG: Python agent code không expose Prometheus metrics (không có `prometheus_client` import)

---

# PHẦN 5: TECHNICAL INTERVIEW SIMULATION

## Câu 1: ADK Misrepresentation

**Interviewer:** "Tôi thấy em ghi 'Implemented ADK (Agent Development Kit)'. Em hãy nói cho tôi biết, ADK của Google có những class chính nào, workflow của Agent lifecycle ra sao?"

**Chờ trả lời từ ứng viên...**

**Chấm điểm:** N/A (chưa nghe trả lời)
**Giải thích:** Code hiện tại không implement Google ADK. Đây là self-built.
**Đáp án chuẩn (Senior sẽ nói):** "ADK của Google LỚN HƠN những gì tôi implement. Cụ thể: Agent class với lifecycle (initialize, before_tool_call, after_tool_call, before_response, after_response), ToolContext (quản lý state, session, user auth), ApisApiSpec (calling external APIs), code_execution (sandbox), session management tự động. Của tôi chỉ là phiên bản simplified, custom-built cho use case cụ thể."

## Câu 2: A2A Protocol

**Interviewer:** "Em ghi 'Built A2A Protocol với CircuitBreaker và DeadLetterQueue'. Mở source code của em ra, cho tôi xem A2AProtocolHub được implement ở đâu?"

**Chờ trả lời từ ứng viên...**

**Chấm điểm:** N/A
**Giải thích:** Codebase KHÔNG có A2A.
**Đáp án chuẩn:** Phải chỉ được file, line number, giải thích được A2A architecture, Agent Card, task delegation.

## Câu 3: CRAG Loop

**Interviewer:** "Em implement CRAG. Confidence threshold là bao nhiêu? Tại sao lại là con số đó?"

**Chờ trả lời từ ứng viên...**

**Đáp án chuẩn:** Threshold 0.45. Lý do: không có — không có giải thích trong code. Senior sẽ nói: "Con số 0.45 là empirical, tôi chọn dựa trên thử nghiệm với validation set. Nếu precision quan trọng, tôi sẽ tăng lên 0.6-0.7. Nếu recall quan trọng, tôi giảm xuống 0.3."

## Câu 4: Multi-lingual (language_handler.py)

**Interviewer:** "Em implement detect_language thế nào? Nếu user gõ 'toi muon hoi ve chung khoan' (không dấu) thì có detect được là tiếng Việt không?"

**Chờ trả lời từ ứng viên...**

**Đáp án chuẩn:** "Em dùng rule-based: diacritic detection + word set matching. Với input không dấu, em có non-diacritic variants list (31 từ: 'cua','va','co','khong'...). Nếu input chứa 2+ Vietnamese words và nhiều hơn English words, trả về 'vi'. Nhược điểm: false positive nếu user gõ tiếng Anh nhưng dùng từ giống Vietnamese như 'co', 'va', 'la'."

## Câu 5: Reranking (Cross-encoder)

**Interviewer:** "Em implement reranking thế nào? Có biết vì sao làm vậy không?"

**Chờ trả lời từ ứng viên...**

**Đáp án chuẩn:** "Em dùng LLM để rerank: mỗi chunk gửi query + passage và yêu cầu LLM output score 0-1. Vấn đề: latency — N chunks = N LLM calls. Với top_k=10, mất ~10-30 giây chỉ để rerank. Cách tốt hơn: dùng cross-encoder model thay vì LLM (e.g., BAAI/bge-reranker-v2), nhanh hơn ~100x."

## Câu 6: MCP (Model Context Protocol)

**Interviewer:** "Em ghi MCP trong skills. MCP dùng để làm gì? Em implement chưa?"

**Chờ trả lời từ ứng viên...**

**Đáp án chuẩn (nếu chưa implement nhưng biết):** "MCP là protocol cho LLM tools, do Anthropic đề xuất. Transport types: stdio, SSE. Cấu trúc: MCP Server (tool definitions), MCP Client (tool calling), MCP Host (agent runtime). Em chưa implement nhưng có đọc spec. Trong codebase em dùng ADK-style custom tool registry thay vì MCP."

## Câu 7: Streaming Response (CRAG ghi sai)

**Interviewer:** "Em ghi 'streaming response' nhưng code em không có streaming. Giải thích tại sao?"

**Chờ trả lời từ ứng viên...**

**Đáp án chuẩn:** "Em nhận sai. Code hiện tại không có streaming — response được build đầy đủ rồi mới trả về. Để implement streaming, em cần: (1) LLM gọi với stream=True, (2) SSE response từ FastAPI, (3) frontend EventSource. Em chưa implement phần này."

---

# PHẦN 6: ĐIỂM YẾU CỦA CV

1. **❌ ADK Misrepresentation**: CV nói "Implemented ADK" nhưng thực tế là self-built
2. **❌ A2A Fabrication**: A2AProtocolHub, CircuitBreaker, DeadLetterQueue không tồn tại
3. **❌ MCP**: CV ghi skills MCP nhưng không có implementation
4. **❌ 22+ agents**: Chỉ có ~12 agents trong codebase
5. **❌ Auto-improvement pipeline**: Không tồn tại
6. **❌ LoRA/Fine-tuning**: Không có evidence
7. **❌ Streaming response**: CRAG loop ghi "streaming response" nhưng code không có streaming
8. **⚠️ Thiếu benchmark**: Không có metrics về latency, throughput, accuracy
9. **⚠️ Thiếu evaluation**: Không có RAG evaluation, agent evaluation systematic
10. **⚠️ Thiếu testing**: agent/tests/ có test files nhưng số lượng ít, coverage thấp
11. **⚠️ Thiếu CI/CD**: Không có CI pipeline config (GitHub Actions, GitLab CI)
12. **⚠️ Thiếu security**: Auth, input sanitization, prompt injection protection
13. **⚠️ Project scope quá lớn cho Intern**: Smart Document Chatbot + Personal AI Platform cùng lúc (~4 tháng cho mỗi project) — đáng nghi ngờ về contribution split với team
14. **⚠️ WebSocket/SSE**: Ghi trong skills nhưng không có evidence trong agent code
15. **⚠️ Prometheus**: Có config file nhưng không có metrics integration với Python code

---

# PHẦN 7: CHECKLIST IMPLEMENTATION

## Project 1: Smart Document Chatbot

| Feature | Đã implement thật? | Có demo? | Có source code? | Có thể explain? | Có thể live code? | Có benchmark? |
|---|---|---|---|---|---|---|
| LangGraph Multi-Agent | ✅ | ❌ (không có URL) | ✅ | ✅ | △ Có thể | ❌ |
| Multi-lingual | ✅ | ❌ | ✅ | ✅ | △ | ❌ |
| Session Persistence | ✅ | ❌ | ✅ | ✅ | △ | ❌ |
| Context Summarization | ✅ | ❌ | ✅ | ✅ | △ | ❌ |
| Long-term Memory | ✅ | ❌ | ✅ | ✅ | △ | ❌ |
| Corrective RAG | ✅ | ❌ | ✅ | ✅ | △ | ❌ |
| Hybrid Search | ✅ | ❌ | ✅ | ✅ | △ | ❌ |
| Web Search Fallback | ✅ | ❌ | ✅ | ✅ | △ | ❌ |
| Streaming Response | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |

## Project 2: Personal AI Platform

| Feature | Đã implement thật? | Có demo? | Có source code? | Có thể explain? | Có thể live code? | Có benchmark? |
|---|---|---|---|---|---|---|
| Google ADK | ❌ (self-built) | ❌ | ✅ (nhưng sai) | ❌ (nếu nghĩ là Google ADK) | ❌ | ❌ |
| A2A Protocol | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Circuit Breaker | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Dead Letter Queue | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| 22+ Agents | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Auto-improvement | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Ollama Inference | ✅ | ❌ | ✅ | ✅ | △ | ❌ |
| Model Quantization | △ | ❌ | △ | ❌ | ❌ | ❌ |
| MCP Protocol | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |

---

# PHẦN 8: LỖ HỔNG KIẾN THỨC (TOP 50)

### Python Core
1. GIL (Global Interpreter Lock) là gì? Ảnh hưởng đến multi-threading?
2. async/await khác gì với thread? Event loop hoạt động thế nào?
3. Memory management trong Python: reference counting, garbage collection
4. `__slots__`, `__init_subclass__`, metaclass
5. Context manager protocol (`__enter__`, `__exit__`), dùng để làm gì?

### LLM & NLP
6. Transformer architecture: attention mechanism, positional encoding
7. Tokenizer types: BPE, WordPiece, SentencePiece
8. Context window: sliding window, window hierarchy
9. Temperature, top-k, top-p sampling — khác nhau thế nào?
10. Hallucination detection và mitigation strategies
11. Prompt injection: types, prevention
12. System prompt vs user prompt — khác biệt về security?

### RAG & Vector Search
13. Chunking strategies: fixed-size, semantic, recursive. Khi nào dùng cái nào?
14. Embedding model selection: matryoshka, multi-vector
15. Hybrid search: weighted sum vs RRF — ưu nhược điểm
16. Cross-encoder vs bi-encoder — khác biệt, latency trade-off
17. Vector index types: HNSW, IVF, Flat — trade-offs
18. Cosine similarity vs dot product vs euclidean — khi nào dùng
19. RAG Evaluation: Context Relevance, Answer Relevance, Faithfulness

### Fine-tuning & Quantization
20. LoRA: rank, alpha, target modules — ý nghĩa
21. QLoRA: NF4 quantization, double quantization
22. PEFT vs full fine-tuning — trade-offs
23. GGUF format là gì? Khác gì với original model?
24. GPU memory estimation cho LLM inference

### System Design
25. Multi-agent architecture patterns: supervisor, hierarchical, voting, debate
26. Agent communication protocols: function calling, structured output, MCP, A2A
27. Rate limiting strategies: token bucket, sliding window
28. Caching strategies: write-through, write-behind, cache invalidation
29. Circuit Breaker pattern: states (closed, open, half-open), recovery

### Docker & DevOps
30. Docker: multi-stage build optimization, layer caching, .dockerignore
31. Docker networking: bridge, host, overlay
32. Kubernetes: pod, deployment, service, ingress, configmap
33. CI/CD pipeline: build → test → deploy → monitor

### MLOps
34. Model versioning: DVC, MLflow Model Registry
35. Feature store vs model registry — khác nhau
36. A/B testing cho LLM — cách set up
37. Drift detection: data drift, concept drift, model drift
38. Monitoring metrics: latency p50/p95/p99, throughput, error rate, cost per request

### Database & Storage
39. PostgreSQL: indexing (B-tree, GIN, GiST), query planning, connection pooling
40. Redis: data structures, persistence, clustering
41. Vector DB: scalability, multi-tenancy, hybrid search implementation

### Security
42. Authentication: JWT, OAuth2, session-based
43. Authorization: RBAC, ABAC
44. Input sanitization, injection prevention
45. Secrets management, environment variables

### GPU & Inference
46. CUDA basics: kernel, memory hierarchy, streams
47. vLLM vs Ollama vs TGI — khác nhau, trade-offs
48. Continuous batching, PagedAttention
49. Tensor parallelism, pipeline parallelism
50. Model serving: concurrency, queue management, auto-scaling

---

# PHẦN 9: INTERVIEW CONFIDENCE

| Mục | Điểm (1-10) | Ghi chú |
|---|---|---|
| **Technical (RAG, Multi-agent, Memory)** | 7/10 | RAG: 8, Multi-agent: 7, Memory: 7. Điểm mạnh nhất |
| **Communication** | N/A | Chưa test trực tiếp |
| **Project (Quality + Honesty)** | 4/10 | Project 1: 7.5/10. Project 2: 1/10 (misrepresentation) |
| **Coding** | 7/10 | Python: 7, code clean, async-first. Chưa thấy Java/Typescript quality |
| **AI Knowledge** | 6/10 | RAG: 8, NLP: 5, Fine-tuning: 2, GPU: 3 |
| **Python** | 7/10 | Clean code, async programming, type hints |
| **LLM** | 6/10 | Biết dùng, biết config nhưng chưa hiểu sâu inside |
| **Deployment** | 5/10 | Docker cơ bản, k8s sơ khai, thiếu production-ready |
| **System Design** | 5/10 | 1-level multi-agent routing, thiếu fault tolerance, security |
| **Honesty (Critical)** | 2/10 | **ADK, A2A, MCP, 22+ agents, streaming response — tất cả đều phóng đại** |
| **Overall** | 5/10 | **Project 1 có thực chất. CV bị hỏng bởi phóng đại.** |

### Khả năng pass vòng Technical của AI Power: **35%**

**Lý do:**
1. ❌ **Vấn đề honesty sẽ giết chết cơ hội**. Một khi interviewer phát hiện ADK/A2A/MCP không có thật, trust bị phá vỡ. Senior AI Engineer sẽ "đào" đến cùng.
2. ❌ Nếu hỏi "show tôi file A2AProtocolHub", không thể trả lời.
3. ❌ Nếu hỏi "implement LoRA thế nào?", không thể trả lời.
4. ✅ RAG implementation và architecture là điểm sáng duy nhất.
5. ⚠️ Cho Intern: kiến thức nền tảng 6/10 là OK, nhưng honesty issue là red flag.

---

# PHẦN 10: ROADMAP 6 GIỜ TRƯỚC PHỎNG VẤN

## Giờ 1: Fix CV (QUAN TRỌNG NHẤT — quyết định pass/fail)
**Các thay đổi BẮT BUỘC:**
- ADK: từ "Implemented Google ADK" → "Built custom ADK-inspired agent framework with ToolRegistry, QueryParser, AgentFactory"
- A2A: **BỎ HOÀN TOÀN** nếu không implement thật
- CircuitBreaker, DeadLetterQueue: **BỎ HOÀN TOÀN**
- 22+ agents → đổi thành "~12 agents across 2 projects"
- Auto-improvement pipeline: **BỎ** nếu không có thật
- Streaming response: **BỎ** hoặc sửa thành "RAG with web search fallback"
- LoRA: **BỎ** nếu chưa implement
- MCP: **BỎ** nếu chưa implement

## Giờ 2: 22+ agents claim và số liệu
- Đếm lại chính xác: 7 (Project 1) + CSKH + 4 (ADK default) = ~12
- Chuẩn bị câu trả lời trung thực

## Giờ 3: Đọc lại source code của chính mình
- CONFIDENCE_THRESHOLD=0.45: chuẩn bị lý do
- TOP_K=5: chuẩn bị lý do
- LTM_EXTRACT_INTERVAL=5: chuẩn bị lý do
- Từng class trong adk_agent.py: giải thích được
- language_handler.py: giải thích được language detection algorithm

## Giờ 4: Lấp lỗ hổng kiến thức quan trọng (theo priority)
1. **RAG Evaluation**: Context Relevance, Answer Relevance, Faithfulness
2. **Chunking strategies**: fixed-size, semantic, recursive
3. **Hybrid search**: RRF vs weighted sum
4. **Cross-encoder vs bi-encoder**
5. **Google ADK thật sự**: Agent lifecycle, ToolContext
6. **MCP spec**: transport types (stdio, SSE)
7. **Streaming**: cách implement Server-Sent Events

## Giờ 5: Chuẩn bị trình bày Project 1
- Architecture diagram (mental)
- Data flow: user → orchestrator → agent → LLM response
- RAG flow: query → hybrid search → rerank → CRAG → answer
- Sẵn sàng: "What was YOUR contribution vs team?" — nếu là solo project thì nói rõ

## Giờ 6: Mock interview + chuẩn bị câu trả lời cho câu hỏi khó
**Câu hỏi khó #1:** "Tại sao CV em ghi ADK và A2A mà code không có?"
→ **"Em xin nhận sai. ADK trong CV là custom-built, em đã không ghi rõ. A2A em đang nghiên cứu nhưng chưa có code hoàn chỉnh. Em sẽ sửa CV ngay."**

**Câu hỏi khó #2:** "22+ agents đâu?"
→ **"Em đếm không chính xác. Thực tế có ~12 agents. Em xin rút kinh nghiệm."**

**Câu hỏi khó #3:** "Streaming response?"
→ **"Code em chưa implement streaming. Đó là em ghi nhầm. Em biết cách implement với FastAPI SSE."**

---

# TỔNG KẾT

## Điểm mạnh THỰC SỰ:
- ✅ RAG implementation tốt: hybrid search (semantic + BM25 + RRF), CRAG loop, LLM reranking
- ✅ Multi-agent architecture với LangGraph StateGraph
- ✅ Memory systems: ShortTerm, LongTerm (PostgreSQL), ContextSummarizer
- ✅ Multi-lingual support: rule-based Vietnamese-English detection
- ✅ Async-first Python code, clean architecture
- ✅ Code organization rõ ràng, module hóa tốt

## Điểm yếu NGHIÊM TRỌNG:
- ❌ **CV phóng đại/sai ở nhiều chỗ: ADK, A2A, MCP, CircuitBreaker, DeadLetterQueue, 22+ agents, auto-improvement, streaming, LoRA**
- ❌ Không implement được Google ADK, A2A, MCP như đã ghi
- ❌ Thiếu evaluation, testing, security, CI/CD

## Khuyến nghị cho ứng viên:
1. **SỬA CV NGAY LẬP TỨC** — bỏ các claim sai
2. **KHÔNG ĐI PHỎNG VẤN VỚI CV HIỆN TẠI** — cơ hội pass < 35%
3. Tập trung khoe Project 1 (Smart Document Chatbot) — đây là điểm mạnh thật
4. Học và implement A2A/MCP thật trước khi ghi vào CV