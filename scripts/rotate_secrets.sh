#!/usr/bin/env bash
# Secret rotation helper — generates new secrets and prints Render update commands
# Usage: ./scripts/rotate_secrets.sh [service]
set -euo pipefail
SERVICE=${1:-smart-doc-backend}
echo "Generating new secrets..."
JWT=$(openssl rand -base64 48 | tr -d '\n')
TOKEN=$(openssl rand -base64 32 | tr -d '\n')
echo "JWT_SECRET=$JWT"
echo "INTERNAL_SERVICE_TOKEN=$TOKEN"
echo ""
echo "To rotate on Render:"
echo "  1) Render Dashboard -> $SERVICE -> Environment -> sync: false keys -> update"
echo "  2) Via API (requires RENDER_API_KEY):"
echo "     curl -X PUT https://api.render.com/v1/services/\$RENDER_SERVICE_ID/env-vars/JWT_SECRET \\"
echo "       -H \"Authorization: Bearer \$RENDER_API_KEY\" -d '{\"value\":\"'$JWT'\"}'"
echo "  3) Restart service and verify /api/actuator/health"
echo ""
echo "For Neon/Qdrant/R2 keys, rotate in their dashboards and update Render env similarly."
echo "Schedule: quarterly, or after any suspected leak (TruffleHog alert)."
