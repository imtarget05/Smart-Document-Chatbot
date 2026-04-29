# Setup Instructions

## Prerequisites

- Docker & Docker Compose installed
- OpenAI API key (get from https://platform.openai.com/api-keys)
- Git

## Quick Start (Recommended)

### 1. Clone & Navigate
```bash
cd Smart\ Document\ Chatbot
```

### 2. Set Environment Variables
```bash
# Linux/Mac
export OPENAI_API_KEY="sk-your-api-key-here"

# Windows PowerShell
$env:OPENAI_API_KEY="sk-your-api-key-here"

# Windows CMD
set OPENAI_API_KEY=sk-your-api-key-here
```

### 3. Build & Run with Docker Compose
```bash
docker-compose -f docker/docker-compose.yml up --build
```

This will start:
- PostgreSQL on port 5432
- Qdrant on port 6333
- Backend (Spring Boot) on port 8080
- Frontend (React) on port 3000

### 4. Access the Application
- Frontend: http://localhost:3000
- Backend API: http://localhost:8080/api
- Qdrant Dashboard: http://localhost:6333/dashboard

---

## Local Development Setup

### Backend Setup

```bash
cd backend

# Install Java dependencies
mvn clean install

# Set environment variables (in IDE or terminal)
export OPENAI_API_KEY=sk-...
export SPRING_DATASOURCE_URL=jdbc:postgresql://localhost:5432/smart_doc_chatbot
export SPRING_DATASOURCE_USERNAME=postgres
export SPRING_DATASOURCE_PASSWORD=postgres

# Run Spring Boot
mvn spring-boot:run

# Server: http://localhost:8080
```

### Frontend Setup

```bash
cd frontend

# Install Node dependencies
npm install

# Start development server
npm start

# App: http://localhost:3000 (auto-opens)
```

### Database Setup

```bash
# Start PostgreSQL
docker run -d \
  --name postgres-smart-doc \
  -e POSTGRES_DB=smart_doc_chatbot \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -p 5432:5432 \
  postgres:15-alpine

# Start Qdrant
docker run -d \
  --name qdrant-smart-doc \
  -p 6333:6333 \
  qdrant/qdrant:latest
```

---

## Testing

### Test Backend
```bash
cd backend
mvn test
```

### Test Frontend
```bash
cd frontend
npm test
```

---

## Troubleshooting

### Port Already in Use
```bash
# Find and kill process on port
lsof -ti:8080 | xargs kill -9  # Linux/Mac
netstat -ano | findstr :8080   # Windows
```

### Database Connection Error
```bash
# Check PostgreSQL is running
docker ps | grep postgres

# If not running:
docker-compose -f docker/docker-compose.yml up postgres
```

### OpenAI API Error
- Check API key is valid
- Check account has credits
- Check rate limits not exceeded

### Build Issues
```bash
# Clean and rebuild
cd backend
mvn clean install -DskipTests

cd ../frontend
npm ci
npm run build
```

---

## Configuration Files

### Backend: application.yml
Located at `backend/src/main/resources/application.yml`
- Database connection
- OpenAI settings
- Qdrant settings
- Server port

### Frontend: environment variables
Create `.env` file in frontend directory:
```
REACT_APP_API_URL=http://localhost:8080/api
REACT_APP_WS_URL=ws://localhost:8080/ws
```

---

## Next Steps

1. ✅ System is running
2. 📄 Upload a test document (PDF/Word)
3. 💬 Ask questions about the document
4. 🔍 Check chat history
5. 🚀 Deploy to production (see DEPLOYMENT.md)

---

For issues: Check logs with `docker logs <container_name>`
