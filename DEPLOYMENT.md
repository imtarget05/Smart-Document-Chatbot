# Deployment Guide

## Prerequisites
- Docker & Docker Compose
- OpenAI API Key
- Git
- 2GB+ available disk space

## Production Deployment

### Option 1: Railway (Recommended for Simplicity)

1. **Create Railway Account**
   - Go to https://railway.app
   - Sign up with GitHub

2. **Deploy Database**
   - Add PostgreSQL plugin
   - Configure environment variables

3. **Deploy Backend**
   ```bash
   railway link <backend-id>
   railway up
   ```

4. **Deploy Frontend**
   - Connect GitHub repository
   - Set build command: `npm run build`
   - Set start command: `npm start`

5. **Configure Environment**
   ```
   OPENAI_API_KEY=sk-...
   DATABASE_URL=postgresql://...
   ```

---

### Option 2: AWS EC2

1. **Launch EC2 Instance**
   - Ubuntu 22.04 LTS
   - t3.medium (2GB RAM recommended)
   - Security group: Open ports 80, 443, 8080

2. **Setup Instance**
   ```bash
   sudo apt update
   sudo apt install -y docker.io docker-compose git
   sudo usermod -aG docker $USER
   newgrp docker
   ```

3. **Clone & Deploy**
   ```bash
   git clone <your-repo>
   cd Smart\ Document\ Chatbot
   export OPENAI_API_KEY=sk-...
   docker-compose -f docker/docker-compose.yml up -d
   ```

4. **Setup Nginx Reverse Proxy**
   ```nginx
   server {
       listen 80;
       server_name your-domain.com;

       location / {
           proxy_pass http://localhost:3000;
           proxy_set_header Host $host;
       }

       location /api {
           proxy_pass http://localhost:8080/api;
           proxy_set_header Host $host;
       }
   }
   ```

---

### Option 3: DigitalOcean App Platform

1. **Connect Repository**
   - Link GitHub account

2. **Configure Services**
   - Backend: Docker (port 8080)
   - Frontend: React (port 3000)
   - Database: PostgreSQL

3. **Set Envs & Deploy**
   ```
   OPENAI_API_KEY=sk-...
   ```

---

## SSL/HTTPS Setup

### Using Let's Encrypt (Free)

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot certonly --nginx -d your-domain.com
```

### Nginx SSL Config
```nginx
server {
    listen 443 ssl;
    server_name your-domain.com;

    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;

    location / {
        proxy_pass http://localhost:3000;
    }
}
```

---

## Monitoring & Maintenance

### Health Checks
```bash
# Backend health
curl http://localhost:8080/actuator/health

# Frontend
curl http://localhost:3000

# Database
psql -h localhost -U postgres -d smart_doc_chatbot -c "SELECT 1"
```

### Logs
```bash
# Backend logs
docker logs smart_document_chatbot_backend_1

# Frontend logs
docker logs smart_document_chatbot_frontend_1

# Database logs
docker logs smart_document_chatbot_postgres_1
```

### Backup Database
```bash
docker exec postgres_container pg_dump \
  -U postgres \
  smart_doc_chatbot > backup_$(date +%Y%m%d).sql
```

### Auto-restart on Reboot
```bash
sudo systemctl enable docker
docker-compose -f docker-compose.yml up -d
```

---

## Performance Optimization

1. **Enable Caching**
   - Add Redis for session storage
   - Cache embeddings

2. **Database Optimization**
   - Create indexes on frequently queried columns
   - Archive old chat messages

3. **Vector DB Optimization**
   - Batch embeddings processing
   - Tune Qdrant search parameters

4. **Frontend Optimization**
   - Code splitting with React.lazy
   - Service workers for offline
   - Compression (gzip)

---

## Cost Estimation

### Monthly Costs (Approximate)
- **AWS EC2 t3.medium**: $35
- **OpenAI API** (1000 queries/day): $30-50
- **Storage** (100GB): $5
- **Total**: ~$70-90/month

### Cost Optimization
- Use GPT-3.5-turbo instead of GPT-4o-mini for faster queries
- Implement rate limiting
- Cache frequently asked questions
- Use smaller embedding models

---

## Rollback Procedure

```bash
# If new deployment fails
git checkout <previous-commit>
docker-compose -f docker/docker-compose.yml down
docker-compose -f docker/docker-compose.yml up --build -d

# Restore database from backup
docker exec postgres_container psql \
  -U postgres \
  smart_doc_chatbot < backup_latest.sql
```

---

## Support

For deployment issues:
1. Check application logs
2. Verify environment variables
3. Test connectivity to external APIs
4. Check disk space and memory
5. Review security group/firewall rules
