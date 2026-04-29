#!/bin/bash
# ============================================
# Smart Document Chatbot - Deployment Script
# Usage: ./scripts/deploy.sh [staging|production]
# ============================================

set -euo pipefail

ENVIRONMENT=${1:-staging}
COMPOSE_FILE="docker/docker-compose.yml"
BACKUP_DIR="backups"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() { echo -e "${GREEN}[DEPLOY]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

# --- Pre-flight checks ---
log "Starting deployment to ${ENVIRONMENT}..."

# Check Docker
command -v docker >/dev/null 2>&1 || error "Docker is not installed"
command -v docker compose >/dev/null 2>&1 || error "Docker Compose is not installed"

# Check .env file
if [ ! -f ".env" ]; then
    if [ -f ".env.${ENVIRONMENT}" ]; then
        warn ".env not found, copying from .env.${ENVIRONMENT}"
        cp ".env.${ENVIRONMENT}" .env
    else
        error ".env file not found. Copy from .env.example and configure."
    fi
fi

# Load environment
set -a
source .env
set +a

# --- Backup database (if running) ---
if docker compose -f ${COMPOSE_FILE} ps postgres 2>/dev/null | grep -q "running"; then
    log "Backing up database..."
    mkdir -p ${BACKUP_DIR}
    docker compose -f ${COMPOSE_FILE} exec -T postgres \
        pg_dump -U ${POSTGRES_USER:-postgres} ${POSTGRES_DB:-smart_doc_chatbot} \
        > "${BACKUP_DIR}/db-${TIMESTAMP}.sql" 2>/dev/null || warn "Database backup failed (may be first deploy)"
    log "Database backup: ${BACKUP_DIR}/db-${TIMESTAMP}.sql"
fi

# --- Pull/Build images ---
log "Building Docker images..."
docker compose -f ${COMPOSE_FILE} build --parallel

# --- Deploy ---
log "Deploying services..."
docker compose -f ${COMPOSE_FILE} up -d --remove-orphans

# --- Wait for health checks ---
log "Waiting for services to be healthy..."
RETRIES=30
RETRY_INTERVAL=5

for i in $(seq 1 ${RETRIES}); do
    if docker compose -f ${COMPOSE_FILE} ps | grep -v "unhealthy\|starting" | grep -q "healthy"; then
        break
    fi
    
    if [ $i -eq ${RETRIES} ]; then
        error "Services did not become healthy within timeout"
    fi
    
    echo -n "."
    sleep ${RETRY_INTERVAL}
done
echo ""

# --- Verify deployment ---
log "Verifying deployment..."

# Check backend health
BACKEND_HEALTH=$(curl -sf http://localhost:${BACKEND_PORT:-8080}/api/actuator/health 2>/dev/null || echo "failed")
if echo "${BACKEND_HEALTH}" | grep -q "UP"; then
    log "Backend health: UP"
else
    warn "Backend health check returned: ${BACKEND_HEALTH}"
fi

# Check frontend
FRONTEND_STATUS=$(curl -sf -o /dev/null -w "%{http_code}" http://localhost:${FRONTEND_PORT:-80}/ 2>/dev/null || echo "000")
if [ "${FRONTEND_STATUS}" = "200" ]; then
    log "Frontend health: OK (HTTP ${FRONTEND_STATUS})"
else
    warn "Frontend returned HTTP ${FRONTEND_STATUS}"
fi

# --- Clean up ---
log "Cleaning up old images..."
docker image prune -f >/dev/null 2>&1

# --- Summary ---
echo ""
log "============================================"
log "Deployment to ${ENVIRONMENT} completed!"
log "============================================"
log "Frontend: http://localhost:${FRONTEND_PORT:-80}"
log "Backend:  http://localhost:${BACKEND_PORT:-8080}"
log ""
docker compose -f ${COMPOSE_FILE} ps
