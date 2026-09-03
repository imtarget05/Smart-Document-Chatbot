#!/usr/bin/env bash
# Backup DR for Neon Postgres + Qdrant
# Usage: ./scripts/backup.sh [backup_dir]
set -euo pipefail
BACKUP_DIR=${1:-./backups}
DATE=$(date +%Y%m%d_%H%M%S)
mkdir -p "$BACKUP_DIR"

echo "=== Smart Doc Backup $DATE ==="

# 1. Postgres (Neon) via pg_dump
if [[ -n "${NEON_DATABASE_URL:-}" || -n "${SPRING_DATASOURCE_URL:-}" ]]; then
  DB_URL=${NEON_DATABASE_URL:-${SPRING_DATASOURCE_URL}}
  echo "[1/3] Postgres pg_dump -> $BACKUP_DIR/pg_$DATE.sql.gz"
  # Convert jdbc url if needed: jdbc:postgresql://host/db -> postgresql://host/db
  PG_URL=$(echo "$DB_URL" | sed 's/^jdbc://')
  pg_dump "$PG_URL" | gzip > "$BACKUP_DIR/pg_$DATE.sql.gz" || echo "WARN: pg_dump failed (check NEON_DATABASE_URL)"
  ls -lh "$BACKUP_DIR/pg_$DATE.sql.gz" || true
else
  echo "[1/3] SKIP Postgres (NEON_DATABASE_URL not set)"
fi

# 2. Qdrant snapshots
QDRANT_HOST=${QDRANT_HOST:-localhost}
QDRANT_PORT=${QDRANT_PORT:-6333}
QDRANT_API_KEY=${QDRANT_API_KEY:-}
echo "[2/3] Qdrant snapshot via API $QDRANT_HOST:$QDRANT_PORT"
for COL in documents supply_chain; do
  URL="http://$QDRANT_HOST:$QDRANT_PORT/collections/$COL/snapshots"
  HDR=""
  [[ -n "$QDRANT_API_KEY" ]] && HDR="-H api-key: $QDRANT_API_KEY"
  if curl -s $HDR -X POST "$URL" | grep -q "snapshot"; then
    echo "  snapshot $COL OK"
  else
    echo "  snapshot $COL SKIP/FAIL (collection may not exist)"
  fi
done

# 3. R2 versioning check
echo "[3/3] R2 bucket versioning: ensure R2_BUCKET_NAME=$R2_BUCKET_NAME has versioning enabled (Cloudflare dashboard)"

echo "Backup done -> $BACKUP_DIR"
ls -lh "$BACKUP_DIR" | tail -10
