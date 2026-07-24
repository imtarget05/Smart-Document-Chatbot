# Smart Document Chatbot - Project Skill

Enterprise Agentic Corrective RAG (CRAG) Platform for document Q&A with multi-agent orchestration.

## Architecture Overview

```
Frontend (React 18 + Vite + TypeScript)  :3000
    | proxy /api -> backend:8080
    | proxy /ws  -> backend:8080
Backend (Spring Boot 3.2 / Java 17)       :8080
    |-- REST API controllers (Chat, Auth, Document, DataSource, Agent, etc.)
    |-- JWT auth (jjwt) + httpOnly cookie
    |-- PostgreSQL (JPA/Hibernate + Flyway)
    |-- Qdrant vector store (gRPC)
    |-- Resilience4j (circuit breaker, time limiter)
    |-- Bucket4j (rate limiting)
    |-- Prometheus metrics + OpenTelemetry tracing
    |-- SseEmitter / WebSocket for streaming
    |
    +-- Agent Service (FastAPI / Python)   :9000
    |   |-- LangGraph multi-agent orchestrator
    |   |-- Specialist agents (RAG, research, CSKH, action, comparator, engineering, report, ingestion)
    |   |-- A2A (Agent-to-Agent) protocol
    |   |-- MCP (Model Context Protocol) server
    |   |-- Memory (short-term Redis, long-term PostgreSQL)
    |   |-- ADK runtime integration
    |   |-- Connectors (Google Drive, SharePoint, Gmail, Slack)
    |   |-- Drift detection, A/B testing, self-improvement pipeline
    |
    +-- LLM Router (FastAPI / Python)      :8001
    |   |-- Routes to: Ollama (local), OpenAI, Anthropic, NVIDIA
    |   |-- Configurable provider selection with fallback
    |
    +-- Airflow ETL Pipeline
    |   |-- Document ingestion DAG
    |   |-- Parse → Chunk → Embed → Index to Qdrant
    |
    +-- Monitoring Stack
        |-- Prometheus + Grafana + Loki
        |-- Alerting rules
```

## Project Structure

```
/
├── backend/                    # Spring Boot Java Backend
│   ├── pom.xml                 # Maven (Spring Boot 3.2, Java 17)
│   └── src/main/java/com/smartdocchat/
│       ├── SmartDocChatbotApplication.java
│       ├── config/             # Security, JWT, CORS, RateLimiting, OpenAPI
│       ├── controller/         # 11 REST controllers
│       ├── dto/                # Auth, Chat, Document, etc.
│       ├── entity/             # JPA entities (User, Document, ChatMessage, etc.)
│       ├── repository/         # Spring Data JPA repositories
│       ├── service/            # Business logic (Chat, Document, Embedding, etc.)
│       └── util/               # JWT, Qdrant, LLM config, Document parser
├── agent/                      # Python Agent Service (FastAPI + LangGraph)
│   ├── main.py                 # Entry point
│   ├── settings.py             # Pydantic settings (env-based)
│   ├── models.py               # Request/response models
│   ├── llm_factory.py          # LLM client factory
│   ├── adk_agent.py            # ADK-style agent framework
│   ├── adk_runtime.py          # ADK demo runtime
│   ├── mlflow_tracker.py       # MLflow experiment tracking
│   ├── rate_limiter.py         # Token-bucket rate limiter
│   ├── ab_testing.py           # A/B testing framework
│   ├── metrics.py              # Prometheus metrics
│   ├── retrain.py              # Retrain pipeline
│   ├── drift_detector.py       # Model drift detection
│   ├── agents/                 # 9 specialist agents
│   │   ├── orchestrator.py     # Central orchestrator
│   │   ├── rag_agent.py        # Core RAG agent
│   │   ├── researcher_agent.py # Web research
│   │   ├── cskh_agent.py       # Customer service (Vietnamese)
│   │   ├── action_agent.py     # Execute actions (email, Jira, Notion)
│   │   ├── comparator_agent.py # Document comparison
│   │   ├── engineering_analysis_agent.py
│   │   ├── report_agent.py     # PDF/Excel report generation
│   │   └── ingestion_agent.py  # Connector ingestion
│   ├── graph/                  # LangGraph workflow
│   │   ├── state.py            # Graph state schema
│   │   └── workflow.py         # LangGraph pipeline
│   ├── memory/                 # Short-term + long-term memory
│   ├── tools/                  # Web search, Qdrant, report, notification
│   ├── connectors/             # Google Drive, SharePoint, Gmail, Slack
│   ├── a2a/                    # Agent-to-Agent protocol
│   ├── mcp/                    # Model Context Protocol server
│   ├── streaming/              # SSE streaming
│   ├── security/               # Prompt injection detection
│   ├── improvement/            # Self-improvement pipeline
│   └── ingestion/              # Document ingestion pipeline
├── frontend/                   # React 18 + Vite + TypeScript
│   ├── src/
│   │   ├── App.tsx             # Router + auth guard
│   │   ├── context/AuthContext.tsx
│   │   ├── pages/              # AgentChat, ClassicChat, Login
│   │   ├── components/         # 16 components (ChatWindow, Dashboard, etc.)
│   │   └── lib/                # Analytics, PageSpeed, PostHog
│   └── e2e/                    # Playwright E2E tests
├── llm-router/                 # Python LLM Router (FastAPI)
│   └── app/
│       ├── config.py           # Router configuration
│       ├── providers.py        # LLM provider integrations
│       ├── routing.py          # Smart routing logic
│       └── service.py          # Request handling
├── eval/                       # Evaluation pipeline
├── airflow/                    # Apache Airflow DAGs
├── docker/                     # Docker Compose + Dockerfiles
├── k8s/                        # Kubernetes manifests (Kustomize)
├── tests/                      # Python integration tests
└── .github/workflows/          # CI/CD pipelines
```

## Key Patterns & Conventions

### Authentication
- JWT stored in **httpOnly cookie** (not localStorage) for XSS mitigation
- Spring Boot `/auth/login` sets the cookie; `/auth/logout` clears it
- Frontend `AuthContext` keeps only username/role in memory
- Agent service uses `X-Internal-Token` header for backend→agent communication

### API Design
- Backend REST API at `/api/*` (Spring Boot)
- Agent service at `/v1/*` (FastAPI, versioned)
- LLM Router at `/v1/*` (FastAPI, versioned)
- Streaming via SSE (`/agent/invoke-stream`) and WebSocket (`/ws/{session_id}`)

### Agent Architecture
- **LangGraph workflow** orchestrates multi-agent execution
- **A2A protocol** enables agent discovery and delegation
- **MCP server** registers tools (web search, document retrieval, report generation)
- **Specialist agents**: RAG, researcher, CSKH, action, comparator, engineering analysis, report, ingestion
- Each agent has a `run(state)` method returning updated state
- The `orchestrator.py` routes queries to the appropriate agent

### Memory System
- **Short-term**: Redis (in-memory fallback), per-session conversation history (10 turns)
- **Long-term**: PostgreSQL, persistent facts per user, turn-level history
- **Context summarizer**: Compresses old history when exceeding turn limit
- **Language handler**: Detects Vietnamese vs English, adapts prompts accordingly

### CRAG (Corrective RAG) Flow
```
Query → Initial Retrieval (hybrid: dense + sparse)
  → High confidence? → Direct answer
  → Low confidence? → Query reformulation → Parallel re-retrieval
    → Still low? → Web search fallback
    → Final answer with source citations
```

### Data Flow
```
User → Frontend → Backend (ChatController)
  → AgenticRetrievalService (CRAG loop)
    → Qdrant (vector + keyword search)
    → LLM Router (Ollama/Claude/GPT-4o)
  → ChatService (build context, call LLM, format response)
  → Frontend (SSE/WebSocket streaming)
```

## Development Commands

```bash
# Start dev infrastructure (PostgreSQL + Qdrant + Ollama)
make dev-up

# Run backend locally
make dev-backend

# Run frontend locally
make dev-frontend

# Run agent service locally
make dev-agent

# Run all tests
make test

# Run LLM router tests
make test-router

# Build Docker images
make build

# Start production stack
make up
```

## Common Workflows

### Add a new API endpoint
1. Create DTO in `backend/src/main/java/com/smartdocchat/dto/`
2. Create service method in `backend/src/main/java/com/smartdocchat/service/`
3. Create controller endpoint in `backend/src/main/java/com/smartdocchat/controller/`
4. Add frontend API call using `fetch()` with auth header

### Add a new agent
1. Create agent file in `agent/agents/` with a class that has `run(state)` method
2. Register the agent in `agent/main.py` within the A2A hub setup
3. Add routing logic in `orchestrator.py` if needed
4. Add frontend mode button in `AgentChat.tsx`

### Add a new agent tool (MCP)
1. Define handler function in `agent/main.py`
2. Call `_mcp_server.register_tool()` with name, description, handler, input schema
3. Tool is now callable via `/v1/mcp/call` endpoint

### Add a new LLM provider
1. Add provider config in `llm-router/app/config.py`
2. Implement provider client in `llm-router/app/providers.py`
3. Add routing rule in `llm-router/app/routing.py`

## Testing

```bash
# Backend (Java)
mvn test -B                      # Unit + integration tests
cd backend && mvn verify         # Full test suite

# Frontend (TypeScript)
npm run test:coverage            # Vitest unit tests
npm run test:e2e                 # Playwright E2E tests

# Agent service (Python)
cd agent && pytest -q            # Agent unit tests

# LLM Router (Python)
cd llm-router && pytest -q       # Router tests

# Integration tests (Python)
pytest tests/                    # E2E, security, load tests
```

## Deployment

### Docker Compose
```bash
make build      # Build images
make up         # Start all services
make down       # Stop all services
```

### Kubernetes (Kustomize + Argo CD)
```
k8s/
├── base/                        # Common manifests
└── overlays/
    ├── staging/                 # Staging-specific overrides
    └── production/              # Production-specific overrides
```

### CI/CD (GitHub Actions)
- **CI**: Build, test, SonarCloud analysis, Docker build, Trivy scan
- **CD**: Build images → Update K8s manifests → Argo CD syncs to cluster
- Staging deploys on push to `main`
- Production deploys on version tags (`v*`)

## Environment Variables

Key variables (see `agent/settings.py`, `backend/src/main/resources/application.yml`):
- `INTERNAL_SERVICE_TOKEN` - Shared secret between backend and agent
- `JWT_SECRET` - JWT signing key
- `QDRANT_HOST` / `QDRANT_API_KEY` - Vector database
- `NEON_DATABASE_URL` - PostgreSQL connection string
- `TAVILY_API_KEY` - Web search API key
- `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` - Cloud LLM providers
