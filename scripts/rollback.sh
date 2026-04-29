#!/bin/bash
# ============================================
# Smart Document Chatbot - Rollback Script
# Usage: ./scripts/rollback.sh [backup-file.sql]
# ============================================

set -euo pipefail

COMPOSE_FILE="docker/docker-compose.yml"
BACKUP_DIR="backups"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() { echo -e "${GREEN}[ROLLBACK]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

# --- Find backup to restore ---
if [ -n "${1:-}" ]; then
    BACKUP_FILE="$1"
else
    # Find the latest backup
    BACKUP_FILE=$(ls -t ${BACKUP_DIR}/db-*.sql 2>/dev/null | head -1)
fi

if [ -z "${BACKUP_FILE}" ] || [ ! -f "${BACKUP_FILE}" ]; then
    error "No backup file found. Usage: ./scripts/rollback.sh [backup-file.sql]"
fi

log "Rolling back using: ${BACKUP_FILE}"

# --- Load environment ---
if [ -f ".env" ]; then
    set -a
    source .env
    set +a
fi

# --- Stop backend to prevent writes ---
log "Stopping backend..."
docker compose -f ${COMPOSE_FILE} stop backend

# --- Restore database ---
log "Restoring database..."
docker compose -f ${COMPOSE_FILE} exec -T postgres \
    psql -U ${POSTGRES_USER:-postgres} -d ${POSTGRES_DB:-smart_doc_chatbot} < "${BACKUP_FILE}"

# --- Restart all services ---
log "Restarting services..."
docker compose -f ${COMPOSE_FILE} up -d

# --- Verify ---
sleep 15
BACKEND_HEALTH=$(curl -sf http://localhost:${BACKEND_PORT:-8080}/api/actuator/health 2>/dev/null || echo "failed")
if echo "${BACKEND_HEALTH}" | grep -q "UP"; then
    log "Rollback completed successfully. Backend is healthy."
else
    error "Rollback completed but backend health check failed: ${BACKEND_HEALTH}"
fi

docker compose -f ${COMPOSE_FILE} ps
