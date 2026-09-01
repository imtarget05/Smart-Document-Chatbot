# 🤖 Smart Document Chatbot — Enterprise RAG Platform

[![CI/CD](https://github.com/imtarget05/Smart-Document-Chatbot/actions/workflows/ci.yml/badge.svg)](https://github.com/imtarget05/Smart-Document-Chatbot/actions)
[![Java 17](https://img.shields.io/badge/Java-17-ED8B00?logo=openjdk)](https://openjdk.org/)
[![React 18](https://img.shields.io/badge/React-18-61DAFB?logo=react)](https://react.dev/)
[![Spring Boot](https://img.shields.io/badge/Spring%20Boot-3.2-6DB33F?logo=spring)](https://spring.io/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.x-3178C6?logo=typescript)](https://www.typescriptlang.org/)
[![Python 3.11](https://img.shields.io/badge/Python-3.11-3776AB?logo=python)](https://python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> **AI-powered document Q&A system** with Corrective RAG (CRAG) architecture for accurate, hallucination-free answers.

## 🎯 What It Does

Smart Document Chatbot is an enterprise-grade RAG (Retrieval-Augmented Generation) platform that allows users to:

1. **Upload** legal documents (PDF, DOCX, TXT)
2. **Ask questions** in natural language (Vietnamese/English)
3. **Get accurate answers** with source citations
4. **Trust the output** — Hallucination mitigation through 5-layer verification

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Frontend (React + TypeScript)              │
│                        Vite • TanStack Query • TailwindCSS       │
└─────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Backend (Spring Boot 3.2)                      │
│                    JWT + CSRF • Rate Limiting • Audit Logging     │
└─────────────────────────────────────────────────────────────────┘
                    │                           │
                    ▼                           ▼
┌─────────────────────────┐     ┌─────────────────────────────────┐
│    PostgreSQL 15        │     │      LLM Router (FastAPI)       │
│    (metadata + Chunks)  │     │      Task Routing • Caching     │
│    ► Production path    │     │                                 │
└─────────────────────────┘     └─────────────────────────────────┘
                                              │
                                    ┌─────────┴─────────┐
                                    ▼                   ▼
                          ┌─────────────┐       ┌─────────────┐
                          │   Ollama    │       │  Cloudflare  │
                          │  (Local)    │       │  Workers AI  │
                          └─────────────┘       └─────────────┘
```

> **Note:** Production chat uses **PostgreSQL lexical search**. Qdrant hybrid search + BM25 + RRF is available in the experimental Python agent service only.

## ✨ Key Features

### 🧠 AI/ML Capabilities
- **Corrective RAG (CRAG)**: Auto-corrects low-confidence retrievals
- **5-Layer Hallucination Defense**: Confidence gate → Lexical support → Retrieval scoring → Abstention → Eval heuristic
- **Vietnamese Legal NLP**: Điều/Khoản/Điểm structure detection
- **Multi-LLM Support**: Ollama (local) + Cloudflare Workers AI (cloud)
- **Prompt Injection Defense**: Blocks direct, role-play, and homoglyph attacks

### 🔒 Security
- **JWT Authentication** with refresh tokens
- **CSRF Protection** (double-submit cookie pattern)
- **Role-Based Access Control** (ADMIN, ENGINEER, USER)
- **Rate Limiting** (Redis-backed sliding window)
- **Audit Logging** (immutable trail)
- **SSO/OIDC Integration** (Keycloak, Azure AD, Okta)

### 🛠️ DevOps
- **CI/CD Pipeline** (GitHub Actions)
- **Docker Compose** (full stack)
- **Database Migrations** (Flyway)
- **Monitoring** (Prometheus + Grafana)
- **Automated Testing** (251 backend + 35 frontend tests)

## ⚠️ Known Limitations

- **Retrieval accuracy varies significantly by document** (9.68%–96.8% across 5 production runs). The median is ~71%.
- **Hallucination rate is 3-10%**, not 0%. Every eval run shows 1-3 hallucination cases.
- **Production chat uses PostgreSQL lexical search**, not Qdrant hybrid search. Qdrant is only in the experimental Python agent service.
- **Evaluation uses keyword matching**, not semantic similarity (semantic metric added but not yet calibrated).
- **Deploy step is manual** — CI builds images but doesn't auto-deploy.

## ✅ What's Genuinely Implemented

- Full-stack app: Spring Boot + React + TypeScript + Python
- JWT auth, CSRF, RBAC, account lockout, audit logging
- CRAG corrective loop with query reformulation
- Hybrid search + BM25 + RRF (Python agent)
- Docker Compose with 11 services, healthchecks, monitoring
- CI/CD pipeline with tests, security scan, eval
- Prompt injection defense
- Legal document parsing with OCR fallback
- Streaming SSE
- LangGraph multi-agent orchestration
- GraphRAG memory prototype
- MLflow experiment tracking
- LoRA fine-tuning pipeline
- LLM-judge evaluation

## 🚀 Quick Start

### Prerequisites
- Java 17+
- Node.js 20+
- Docker & Docker Compose
- Ollama (optional, for local LLM)

### 1. Clone & Setup
```bash
git clone https://github.com/imtarget05/Smart-Document-Chatbot.git
cd Smart-Document-Chatbot
cp .env.example .env
```

### 2. Start Infrastructure
```bash
make local-infra-up
```

### 3. Start Backend
```bash
cd backend
export JAVA_HOME=/opt/homebrew/opt/openjdk@17
mvn spring-boot:run
```

### 4. Start Frontend
```bash
cd frontend
npm install
npm run dev
```

### 5. Access
- Frontend: http://localhost:3000
- Backend API: http://localhost:8080/api
- API Docs: http://localhost:8080/api/swagger-ui.html

## 📊 Performance Metrics

| Metric | Value |
|--------|-------|
| Retrieval Accuracy (keyword) | 9.68%–96.8% (varies by document) |
| Retrieval Accuracy (semantic) | Measured via cosine similarity |
| Hallucination Rate | 3.2%–9.7% (1-3 cases per 31 questions) |
| Avg Latency | ~1.9s (production) |
| P95 Latency | ~2.7s (production) |
| Automated Tests | 286+ passing (251 backend + 35 frontend) |
| Evaluation Dataset | 31 Vietnamese legal questions |

## 🧪 Testing

```bash
# Backend tests
cd backend && mvn test

# Frontend tests
cd frontend && npm test

# Load test (100 users)
python scripts/load_test.py --users 100 --duration 60

# Eval pipeline
python eval/eval.py --base-url http://localhost:8080/api --token $JWT --document-id 1 --questions eval/questions.json
```

## 📁 Project Structure

```
Smart-Document-Chatbot/
├── backend/              # Spring Boot API
│   ├── src/main/java/    # Java source
│   ├── src/test/         # Unit tests (251 tests)
│   └── src/main/resources/db/migration/  # Flyway migrations
├── frontend/             # React + TypeScript
│   ├── src/components/   # UI components
│   └── src/pages/        # Page components
├── llm-router/           # Python FastAPI LLM router
├── agent/                # Python AI agent
├── eval/                 # Evaluation pipeline
├── docker/               # Docker Compose configs
├── docs/                 # Documentation
├── n8n-workflows/        # Automation workflows
└── scripts/              # Utility scripts
```

## 🔧 Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `LLM_BASE_URL` | LLM Router URL | http://localhost:8001 |
| `LOCAL_OLLAMA_URL` | Ollama URL | (empty) |
| `REDIS_HOST` | Redis host | localhost |
| `JWT_SECRET` | JWT signing key | (required) |
| `DATABASE_URL` | PostgreSQL URL | (required) |

## 📚 Documentation

- [Production Guide](docs/PRODUCTION_GUIDE.md)
- [Fine-Tuning Guide](docs/FINE_TUNE_GUIDE.md)
- [API Documentation](http://localhost:8080/api/swagger-ui.html)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing`)
5. Open a Pull Request

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

---

**Built with ❤️ for AI Engineer & Fullstack Developer interviews.**
