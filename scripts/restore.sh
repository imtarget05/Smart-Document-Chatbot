#!/usr/bin/env bash
# Restore DR for Neon Postgres + Qdrant
# Usage: ./scripts/restore.sh <backup_file.sql.gz>
set -euo pipefail
FILE=${1:?Usage: restore.sh <backup_file.sql.gz>}
if [[ ! -f "$FILE" ]]; then echo "File not found: $FILE"; exit 1; fi
echo "Restoring Postgres from $FILE"
DB_URL=${NEON_DATABASE_URL:-${SPRING_DATASOURCE_URL:?set NEON_DATABASE_URL}}
PG_URL=$(echo "$DB_URL" | sed 's/^jdbc://')
echo "Target: $PG_URL"
read -p "Confirm restore? This will overwrite data (y/N): " CONF
[[ "$CONF" == "y" ]] || { echo "Abort"; exit 1; }
gunzip -c "$FILE" | psql "$PG_URL"
echo "Restore done. Verify with: psql \$PG_URL -c 'select count(*) from documents;'"
echo "Qdrant restore: upload snapshot file to http://\$QDRANT_HOST:6333/collections/{name}/snapshots/recover"
