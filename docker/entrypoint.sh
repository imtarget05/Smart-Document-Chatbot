#!/bin/bash
set -e

# --- 1. Postgres Initialization ---
if [ ! -s /var/lib/postgresql/15/main/PG_VERSION ]; then
    echo "Initializing PostgreSQL database..."
    chown -R postgres:postgres /var/lib/postgresql/15/main
    sudo -u postgres /usr/lib/postgresql/15/bin/initdb -D /var/lib/postgresql/15/main
    
    # Start postgres temporarily to create user/db
    sudo -u postgres /usr/lib/postgresql/15/bin/pg_ctl -D /var/lib/postgresql/15/main -l /var/log/postgresql/startup.log start
    
    echo "Creating database and user..."
    sudo -u postgres psql -c "CREATE USER postgres WITH PASSWORD 'postgres' SUPERUSER;" || true
    sudo -u postgres psql -c "CREATE DATABASE smart_doc_chatbot OWNER postgres;" || true
    
    sudo -u postgres /usr/lib/postgresql/15/bin/pg_ctl -D /var/lib/postgresql/15/main stop
fi

# --- 2. Ollama Model Pre-pull ---
echo "Starting Ollama to pre-pull models..."
ollama serve &
OLLAMA_PID=$!

# Wait for ollama to be ready
until curl -s http://localhost:11434/api/tags > /dev/null; do
    echo "Waiting for Ollama..."
    sleep 2
done

echo "Pulling models..."
ollama pull deepseek-r1:1.5b
ollama pull nomic-embed-text

echo "Stopping temporary Ollama process..."
kill $OLLAMA_PID
wait $OLLAMA_PID || true

# --- 3. Start Supervisord ---
echo "Starting all services via Supervisord..."
exec /usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf
