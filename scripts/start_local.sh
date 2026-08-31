#!/bin/bash
# Start local development stack with Ollama + LLM Router

set -e

echo "🚀 Starting Smart Document Chatbot — Local Dev Stack"
echo "===================================================="

# Check if Ollama is running on host
if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "⚠️  Ollama not running on host. Starting Ollama..."
    if command -v ollama &> /dev/null; then
        ollama serve &
        sleep 5
    else
        echo "❌ Ollama not installed. Install from https://ollama.com"
        echo "   Or run: brew install ollama"
        exit 1
    fi
fi

# Pull required models if not present
echo "📦 Checking Ollama models..."
if ! curl -s http://localhost:11434/api/tags | grep -q "llama3.2"; then
    echo "   Pulling llama3.2 (this may take a while)..."
    ollama pull llama3.2
fi
if ! curl -s http://localhost:11434/api/tags | grep -q "nomic-embed-text"; then
    echo "   Pulling nomic-embed-text..."
    ollama pull nomic-embed-text
fi

# Start infrastructure
echo "🏗️  Starting infrastructure (Postgres + Qdrant + Redis)..."
docker compose -f docker/docker-compose.local.yml up -d postgres qdrant redis

# Wait for services
echo "⏳ Waiting for services to be healthy..."
sleep 10

# Start LLM Router (uses host Ollama)
echo "🧠 Starting LLM Router..."
cd llm-router
pip install -r requirements.txt -q
LOCAL_OLLAMA_URL=http://localhost:11434 LOCAL_OLLAMA_MODEL=llama3.2 \
    uvicorn main:app --host 0.0.0.0 --port 8000 &
cd ..

# Start Backend
echo "⚙️  Starting Backend..."
cd backend
source ../.env.local
export $(cat ../.env.local | grep -v '^#' | grep -v '^$' | xargs)
mvn spring-boot:run &
cd ..

# Start Frontend
echo "🎨 Starting Frontend..."
cd frontend
npm run dev &
cd ..

echo ""
echo "✅ All services started!"
echo "   Frontend:    http://localhost:3000"
echo "   Backend:     http://localhost:8080/api"
echo "   LLM Router:  http://localhost:8001"
echo "   Ollama:      http://localhost:11434"
echo "   Postgres:    localhost:5434"
echo "   Qdrant:      localhost:6333"
echo "   Redis:       localhost:6379"
echo ""
echo "Press Ctrl+C to stop all services."

# Wait for interrupt
wait
