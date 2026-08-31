# ============================================
# Smart Document Chatbot - Makefile
# Common DevOps commands
# ============================================

.PHONY: help dev dev-up local-infra-up local-infra-down dev-down build up down restart logs \
        backend-build frontend-build test test-backend test-frontend \
        clean monitoring db-backup db-restore lint

# Default target
help: ## Show available commands
	@echo "Smart Document Chatbot - DevOps Commands"
	@echo "========================================="
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ========================
# Development
# ========================

dev-up: ## Start dev infrastructure (PostgreSQL + Qdrant + LLM Router)
	docker compose -f docker/docker-compose.dev.yml up -d
	@echo "Dev infrastructure started!"
	@echo "  PostgreSQL: localhost:5432"
	@echo "  Qdrant:     localhost:6333"
	@echo "  LLM Router: localhost:8001 (Cloudflare Workers AI)"
	@echo "  Local LLM:  none in dev.yml — run 'make local-infra-up' for Ollama (localhost:11434)"

local-infra-up: ## Start local eval stack (pgvector Postgres + Qdrant + Ollama)
	docker compose -f docker/docker-compose.local.yml up -d
	@echo "Local eval stack started!"
	@echo "  PostgreSQL: localhost:5432 (smartdoc)"
	@echo "  Qdrant:     localhost:6333"
	@echo "  Ollama:     localhost:11434 (pull models, e.g. ollama pull llama3.2)"

local-infra-down: ## Stop the local eval stack
	docker compose -f docker/docker-compose.local.yml down

dev-down: ## Stop dev infrastructure
	docker compose -f docker/docker-compose.dev.yml down

dev-tools: ## Start dev infra + tools (pgAdmin)
	docker compose -f docker/docker-compose.dev.yml --profile tools up -d
	@echo "pgAdmin: http://localhost:5050 (admin@smartdoc.local / admin)"

dev-backend: ## Run backend locally (requires dev-up)
	cd backend && mvn spring-boot:run

dev-frontend: ## Run frontend locally
	cd frontend && npm run dev

dev-agent: ## Run Python agent service locally (requires dev-up)
	cd agent && uvicorn main:app --host 0.0.0.0 --port 9000 --reload

dev-agent-install: ## Install Python agent dependencies
	cd agent && pip install -r requirements.txt

test-router: ## Run LLM router unit tests (MUST use llm-router/.venv — root venv lacks pdfplumber)
	cd llm-router && .venv/bin/python -m pytest -q

# ========================
# Production Build & Deploy
# ========================

build: ## Build all Docker images
	docker compose -f docker/docker-compose.yml build

build-no-cache: ## Build images without cache
	docker compose -f docker/docker-compose.yml build --no-cache

up: ## Start all services (production)
	docker compose -f docker/docker-compose.yml up -d
	@echo "Application started!"
	@echo "  Frontend: http://localhost"
	@echo "  Backend:  http://localhost:8080"

down: ## Stop all services
	docker compose -f docker/docker-compose.yml down

restart: ## Restart all services
	docker compose -f docker/docker-compose.yml restart

status: ## Show service status
	docker compose -f docker/docker-compose.yml ps

# ========================
# Monitoring
# ========================

monitoring-up: ## Start monitoring stack (Prometheus + Grafana + Loki)
	docker compose -f docker/docker-compose.yml -f docker/docker-compose.monitoring.yml up -d
	@echo "Monitoring started!"
	@echo "  Prometheus: http://localhost:9090"
	@echo "  Grafana:    http://localhost:3000 (admin/admin)"

monitoring-down: ## Stop monitoring stack
	docker compose -f docker/docker-compose.yml -f docker/docker-compose.monitoring.yml down

# ========================
# Logs
# ========================

logs: ## Show all service logs (follow)
	docker compose -f docker/docker-compose.yml logs -f

logs-backend: ## Show backend logs
	docker compose -f docker/docker-compose.yml logs -f smart-document

logs-frontend: ## Show frontend logs
	docker compose -f docker/docker-compose.yml logs -f frontend

# NOTE: the production stack uses managed PostgreSQL (Neon) — there is no local
# "postgres" container in docker-compose.yml. DB commands target the dev stack.
logs-db: ## Show dev database logs
	docker compose -f docker/docker-compose.dev.yml logs -f postgres

# ========================
# Testing
# ========================

test: test-backend test-frontend ## Run all tests

test-backend: ## Run backend tests
	cd backend && mvn test -B

test-frontend: ## Run frontend tests
	cd frontend && npm run test:coverage

# ========================
# Linting
# ========================

lint: lint-backend lint-frontend ## Run all linters

lint-backend: ## Lint backend code
	cd backend && mvn checkstyle:check || true

lint-frontend: ## Lint frontend code
	cd frontend && npm run build

# ========================
# Database
# ========================

db-backup: ## Backup dev PostgreSQL database
	@mkdir -p backups
	docker compose -f docker/docker-compose.dev.yml exec -T postgres \
		pg_dump -U postgres smart_doc_chatbot > backups/db-$$(date +%Y%m%d-%H%M%S).sql
	@echo "Database backup created in backups/"

db-restore: ## Restore dev database from latest backup (usage: make db-restore FILE=backups/db-xxx.sql)
	@if [ -z "$(FILE)" ]; then echo "Usage: make db-restore FILE=backups/db-xxx.sql"; exit 1; fi
	docker compose -f docker/docker-compose.dev.yml exec -T postgres \
		psql -U postgres smart_doc_chatbot < $(FILE)
	@echo "Database restored from $(FILE)"

db-shell: ## Open dev PostgreSQL shell
	docker compose -f docker/docker-compose.dev.yml exec postgres psql -U postgres smart_doc_chatbot

# ========================
# Cleanup
# ========================

clean: ## Remove all containers, volumes, and images
	docker compose -f docker/docker-compose.yml down -v --rmi all
	docker compose -f docker/docker-compose.dev.yml down -v
	@echo "Cleaned up all Docker resources"

prune: ## Remove unused Docker resources
	docker system prune -f
	docker volume prune -f
	@echo "Pruned unused Docker resources"

# top_p feature verification (LLM_TOP_P)
.PHONY: test-top-p e2e-top-p
test-top-p: ## top_p propagation unit tests (backend LLM tests + llm-router)
	cd backend && mvn -q -Dtest="LlmConfigTest,LlmClientTest" test
	cd llm-router && pytest -q tests/test_top_p.py

e2e-top-p: ## Localhost end-to-end verification of top_p (mock provider + real router)
	cd llm-router && .venv/bin/python ../scripts/local_top_p_e2e.py
