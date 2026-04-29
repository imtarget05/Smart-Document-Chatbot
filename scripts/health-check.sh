#!/bin/bash
# ============================================
# Smart Document Chatbot - Health Check Script
# Usage: ./scripts/health-check.sh
# ============================================

set -euo pipefail

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

BACKEND_PORT=${BACKEND_PORT:-8080}
FRONTEND_PORT=${FRONTEND_PORT:-80}
POSTGRES_PORT=${POSTGRES_PORT:-5432}
QDRANT_PORT=${QDRANT_PORT:-6333}

check() {
    local name=$1
    local url=$2
    local status
    
    status=$(curl -sf -o /dev/null -w "%{http_code}" "$url" 2>/dev/null || echo "000")
    
    if [ "$status" = "200" ]; then
        echo -e "  ${GREEN}✓${NC} ${name}: OK (HTTP ${status})"
        return 0
    else
        echo -e "  ${RED}✗${NC} ${name}: FAILED (HTTP ${status})"
        return 1
    fi
}

echo "============================================"
echo " Smart Document Chatbot - Health Check"
echo "============================================"
echo ""

FAILURES=0

# Backend
echo "Backend:"
check "API Health" "http://localhost:${BACKEND_PORT}/api/actuator/health" || ((FAILURES++))
check "API Info" "http://localhost:${BACKEND_PORT}/api/actuator/info" || ((FAILURES++))

echo ""

# Frontend
echo "Frontend:"
check "Web UI" "http://localhost:${FRONTEND_PORT}/" || ((FAILURES++))
check "Nginx Health" "http://localhost:${FRONTEND_PORT}/health" || ((FAILURES++))

echo ""

# Qdrant
echo "Qdrant:"
check "Vector DB" "http://localhost:${QDRANT_PORT}/healthz" || ((FAILURES++))

echo ""

# Docker services
echo "Docker Services:"
docker compose -f docker/docker-compose.yml ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null || echo "  (Docker Compose not running)"

echo ""
echo "============================================"

if [ ${FAILURES} -eq 0 ]; then
    echo -e "${GREEN}All health checks passed!${NC}"
    exit 0
else
    echo -e "${RED}${FAILURES} health check(s) failed!${NC}"
    exit 1
fi
