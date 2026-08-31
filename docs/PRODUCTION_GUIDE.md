# Production Deployment Guide

## Prerequisites
- Docker & Docker Compose v2+
- PostgreSQL 15+ (or Neon serverless)
- Redis 7+ (for distributed rate limiting)
- Ollama (optional, for local LLM)
- Domain name with DNS configured

## Quick Start

### 1. Environment Configuration
```bash
cp .env.example .env
# Edit .env with production values:
# - JWT_SECRET (min 32 chars, base64 encoded)
# - DATABASE_URL (Neon or managed Postgres)
# - REDIS_URL (managed Redis)
# - OAUTH2_CLIENT_ID/SECRET (if using SSO)
```

### 2. SSL/TLS Setup
```bash
# Option A: Let's Encrypt (recommended)
sudo certbot certonly --standalone -d yourdomain.com
openssl pkcs12 -export -in /etc/letsencrypt/live/yourdomain.com/fullchain.pem \
  -inkey /etc/letsencrypt/live/yourdomain.com/privkey.pem \
  -out backend/src/main/resources/keystore.p12 -name smartdoc

# Option B: Corporate CA
# Follow your organization's certificate request process
```

### 3. Deploy
```bash
docker compose -f docker-compose.yml up -d
```

### 4. Verify
```bash
curl https://yourdomain.com/api/actuator/health
```

## SSO/OIDC Configuration

### Keycloak Example
```bash
# 1. Create realm: smartdoc
# 2. Create client: smartdoc-backend
#    - Client Protocol: openid-connect
#    - Access Type: confidential
#    - Valid Redirect URIs: https://yourdomain.com/api/login/oauth2/code/oidc
# 3. Get client secret
# 4. Set environment variables:
OAUTH2_CLIENT_ID=smartdoc-backend
OAUTH2_CLIENT_SECRET=your-client-secret
OAUTH2_ISSUER_URI=https://keycloak.yourdomain.com/realms/smartdoc
```

### Azure AD Example
```bash
OAUTH2_CLIENT_ID=your-app-registration-client-id
OAUTH2_CLIENT_SECRET=your-client-secret
OAUTH2_ISSUER_URI=https://login.microsoftonline.com/{tenant-id}/v2.0
OAUTH2_SCOPES=openid,profile,email,User.Read
```

### Okta Example
```bash
OAUTH2_CLIENT_ID=your-okta-client-id
OAUTH2_CLIENT_SECRET=your-okta-client-secret
OAUTH2_ISSUER_URI=https://your-domain.okta.com
```

## Redis Production Setup

### Option A: Managed Redis (Recommended)
- AWS ElastiCache, GCP Memorystore, Azure Cache for Redis
- Enable encryption in transit (TLS)
- Set `REDIS_SSL_ENABLED=true`

### Option B: Self-hosted Redis
```yaml
# docker-compose.yml addition
redis:
  image: redis:7-alpine
  command: redis-server --requirepass ${REDIS_PASSWORD} --tls-port 6380 --port 0 \
    --tls-cert-file /certs/redis.crt --tls-key-file /certs/redis.key \
    --tls-ca-cert-file /certs/ca.crt
  volumes:
    - ./certs:/certs
  ports:
    - "6380:6380"
```

## Load Testing
```bash
# Quick test (10 users, 30s)
python scripts/load_test.py --users 10 --duration 30

# Production simulation (100 users, 60s, 10s ramp-up)
python scripts/load_test.py --users 100 --duration 60 --ramp-up 10
```

## Monitoring
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3000 (admin/admin)
- Health: https://yourdomain.com/api/actuator/health
- Metrics: https://yourdomain.com/api/actuator/prometheus

## Backup Strategy
```bash
# PostgreSQL backup
pg_dump -h your-db-host -U postgres smartdoc > backup_$(date +%Y%m%d).sql

# Automated (cron)
0 2 * * * pg_dump -h your-db-host -U postgres smartdoc | gzip > /backups/smartdoc_$(date +\%Y\%m\%d).sql.gz
```

## Scaling
- Backend: Horizontal scaling with load balancer (min 2 instances)
- Redis: Required for multi-instance rate limiting
- Database: Use connection pooler (PgBouncer) for >50 connections
- Ollama: Use GPU instance or switch to Cloudflare for high throughput
