# Quick Reference

## Commands

### Start Development
```bash
# All in Docker
docker-compose -f docker/docker-compose.yml up --build

# Or locally
cd backend && mvn spring-boot:run &
cd frontend && npm start
```

### Stop Development
```bash
docker-compose -f docker/docker-compose.yml down
# Or Ctrl+C for local instances
```

### Reset Database
```bash
docker-compose -f docker/docker-compose.yml down -v
docker-compose -f docker/docker-compose.yml up
```

### View Logs
```bash
docker logs container_name -f
docker logs container_name --tail 50
```

### Build Only
```bash
cd backend && mvn clean package -DskipTests
cd frontend && npm run build
```

### Run Tests
```bash
cd backend && mvn test
cd frontend && npm test
```

---

## URLs

| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| Backend | http://localhost:8080 |
| Backend Docs | http://localhost:8080/swagger-ui (TODO) |
| PostgreSQL | localhost:5432 |
| Qdrant | http://localhost:6333 |
| Qdrant Dashboard | http://localhost:6333/dashboard |

---

## Database Credentials

```
PostgreSQL:
  Host: localhost
  Port: 5432
  Database: smart_doc_chatbot
  User: postgres
  Password: postgres

Qdrant:
  Host: localhost
  Port: 6333
  Collection: documents
```

---

## File Sizes

| File Type | Max Size |
|-----------|----------|
| PDF | 50MB |
| Word (.docx) | 50MB |
| Text (.txt) | 50MB |

---

## API Quick Test

```bash
# Upload
curl -F "file=@document.pdf" http://localhost:8080/api/documents/upload

# Get docs
curl http://localhost:8080/api/documents

# Ask question
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{"sessionId":"test","documentId":1,"message":"What is this?"}' \
  http://localhost:8080/api/chat/ask

# Chat history
curl http://localhost:8080/api/chat/history/test
```

---

## Common Issues & Fixes

### Port 8080 in use
```bash
lsof -ti:8080 | xargs kill -9
```

### Port 3000 in use
```bash
lsof -ti:3000 | xargs kill -9
```

### Docker volume errors
```bash
docker volume prune
docker-compose -f docker/docker-compose.yml up --build
```

### Out of memory
```bash
docker update --memory 2g container_name
```

### Database locked
```bash
docker-compose down
docker volume rm smart_document_chatbot_postgres_data
docker-compose up
```

---

## Environment Variables Quick Copy

```bash
export OPENAI_API_KEY=sk-your-key-here
export SPRING_DATASOURCE_URL=jdbc:postgresql://localhost:5432/smart_doc_chatbot
export SPRING_DATASOURCE_USERNAME=postgres
export SPRING_DATASOURCE_PASSWORD=postgres
export QDRANT_HOST=localhost
export QDRANT_PORT=6333
```

---

## Feature Checklist

- [x] Document upload (PDF/Word/TXT)
- [x] Project structure
- [x] Database setup
- [x] API endpoints
- [x] Frontend UI
- [ ] OpenAI integration
- [ ] Qdrant integration
- [ ] Stream responses
- [ ] WebSocket real-time chat
- [ ] Authentication (JWT)
- [ ] Rate limiting
- [ ] Error handling improvements
- [ ] Deployment scripts
- [ ] Monitoring/logging

---

## Useful Commands

```bash
# Install dependencies
cd backend && mvn install
cd frontend && npm install

# Format code
cd backend && mvn spotless:apply
cd frontend && npm run lint -- --fix

# Generate JAR
cd backend && mvn package

# Clean
cd backend && mvn clean
cd frontend && rm -rf node_modules build

# Check Java version
java -version

# Check Node version
node --version && npm --version

# Database backup
docker exec postgres_container pg_dump -U postgres smart_doc_chatbot > backup.sql

# Database restore
docker exec -i postgres_container psql -U postgres smart_doc_chatbot < backup.sql
```

---

## Documentation Files

- **README.md** - Project overview
- **SETUP.md** - Installation & initial setup
- **API.md** - API documentation
- **DEPLOYMENT.md** - Production deployment
- **DEVELOPMENT.md** - Development guide
- **QUICK_REFERENCE.md** - This file

---

## Support Resources

- GitHub Issues: Report bugs
- Discussions: Ask questions
- Pull Requests: Submit features
- Wiki: Community docs

---

Last Updated: 2024
