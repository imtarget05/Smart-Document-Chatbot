# ============================================
# Smart Document Chatbot - Makefile
# Common DevOps commands
# ============================================

.PHONY: help dev dev-up dev-down build up down restart logs \
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

dev-up: ## Start dev infrastructure (PostgreSQL + Qdrant)
	docker compose -f docker/docker-compose.dev.yml up -d
	@echo "Dev infrastructure started!"
	@echo "  PostgreSQL: localhost:5432"
	@echo "  Qdrant:     localhost:6333"

dev-down: ## Stop dev infrastructure
	docker compose -f docker/docker-compose.dev.yml down

dev-tools: ## Start dev infra + tools (pgAdmin)
	docker compose -f docker/docker-compose.dev.yml --profile tools up -d
	@echo "pgAdmin: http://localhost:5050 (admin@smartdoc.local / admin)"

dev-backend: ## Run backend locally (requires dev-up)
	cd backend && mvn spring-boot:run

dev-frontend: ## Run frontend locally
	cd frontend && npm start

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
	@echo "  Grafana:    http://localhost:3001 (admin/admin)"

monitoring-down: ## Stop monitoring stack
	docker compose -f docker/docker-compose.yml -f docker/docker-compose.monitoring.yml down

# ========================
# Logs
# ========================

logs: ## Show all service logs (follow)
	docker compose -f docker/docker-compose.yml logs -f

logs-backend: ## Show backend logs
	docker compose -f docker/docker-compose.yml logs -f backend

logs-frontend: ## Show frontend logs
	docker compose -f docker/docker-compose.yml logs -f frontend

logs-db: ## Show database logs
	docker compose -f docker/docker-compose.yml logs -f postgres

# ========================
# Testing
# ========================

test: test-backend test-frontend ## Run all tests

test-backend: ## Run backend tests
	cd backend && mvn test -B

test-frontend: ## Run frontend tests
	cd frontend && npm test -- --watchAll=false --passWithNoTests

# ========================
# Linting
# ========================

lint: lint-backend lint-frontend ## Run all linters

lint-backend: ## Lint backend code
	cd backend && mvn checkstyle:check || true

lint-frontend: ## Lint frontend code
	cd frontend && npx eslint src/ --ext .js,.jsx --max-warnings 0 || true

# ========================
# Database
# ========================

db-backup: ## Backup PostgreSQL database
	@mkdir -p backups
	docker compose -f docker/docker-compose.yml exec -T postgres \
		pg_dump -U postgres smart_doc_chatbot > backups/db-$$(date +%Y%m%d-%H%M%S).sql
	@echo "Database backup created in backups/"

db-restore: ## Restore database from latest backup (usage: make db-restore FILE=backups/db-xxx.sql)
	@if [ -z "$(FILE)" ]; then echo "Usage: make db-restore FILE=backups/db-xxx.sql"; exit 1; fi
	docker compose -f docker/docker-compose.yml exec -T postgres \
		psql -U postgres smart_doc_chatbot < $(FILE)
	@echo "Database restored from $(FILE)"

db-shell: ## Open PostgreSQL shell
	docker compose -f docker/docker-compose.yml exec postgres psql -U postgres smart_doc_chatbot

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
