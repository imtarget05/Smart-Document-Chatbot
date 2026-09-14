# Hybrid Production Plan — Cloudflare Pages + Render + Free-tier (Không mất chức năng)

**Chốt 2026-09-02**: Frontend Cloudflare Pages, Langfuse Cloud ON, SSO prod ON. Mục tiêu: hybrid localhost (dev) ↔ cloud (prod) **100% không tắt/mất chức năng**, free-tier tối ưu, hợp đồng đủ kiểm test.

## 1. Kiến trúc

```
Browser → Cloudflare Pages (frontend vite, VITE_API_URL=https://<backend>.onrender.com/api)
         → Render smart-doc-backend (Spring Boot prod, Neon PG, R2, Langfuse Cloud, SSO)
         → Render smart-doc-llm-router → Cloudflare Workers AI (@cf/meta/llama-3.3-70b)
         → Render smart-doc-agent (9000, experimental, giữ nguyên)
         → Qdrant Cloud 1GB + Neon 512MB + R2 10GB (free)
Local fallback: docker-compose.dev.yml (postgres 5432/qdrant 6333/redis 6379/Ollama) — không xóa
```

## 2. Phân pha

| Phase | Việc | File |
|---|---|---|
| **P1 Secrets** | Rotate JWT/R2/CF token đã lộ disk, dedup env | render.yaml, .env.example |
| **P2 Frontend Pages** | wrangler.toml + VITE_API_URL build | frontend/wrangler.toml |
| **P3 Langfuse Cloud** | bật LANGFUSE_* trên Render | render.yaml, application-prod.yml |
| **P4 SSO prod** | bật SSO_OIDC_* trên Render, prod profile | render.yaml, application-prod.yml |
| **P5 Blocking bugs** | cd.yml FRONTEND_IMAGE, render CORS, AGENT_PORT, Dockerfile *.jar, LLM_BASE_URL | cd.yml, render.yaml, Dockerfile.backend |
| **P6 Test review** | 254 backend + 54 frontend + eval 31Q + E2E hermetic | ci.yml |

## 3. Free-tier cam kết
Neon 512MB, Qdrant 1GB, R2 10GB, Pages unlimited, Workers AI free, Render free (sleep 15m → keep-alive cron), GHCR free.

## 4. Không mất chức năng
- Storage: local|r2|supabase 3 branches giữ
- Vector: lexical PG + agent Qdrant song song giữ
- LLM: local Ollama + Cloudflare dual giữ
- Agent/n8n/airflow/monitoring: deploy Render nhưng code không xóa, env no-op khi tắt
