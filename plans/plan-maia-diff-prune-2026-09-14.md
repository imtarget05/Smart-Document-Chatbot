# MAIA-Diff + Prune n8n / Supply-Chain Bloat Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Cắt bỏ n8n dư thừa, tỉa supply-chain bloat giữ core API, và chốt 5 hướng khác biệt KHÔNG giống MAIA.

**Architecture:** Prune trước (Track A+B, xoá + dọn reference), sau đó lock differentiation legal-VN / eval mở / HITL / local-first / ops-edge (Track C). Mỗi task 2–5 phút, verify độc lập.

**Tech Stack:** Spring Boot 3.2/Java17, React 18/TS/Vite, FastAPI llm-router, LangGraph agent, Qdrant + Postgres (Neon/pgvector), Airflow, Docker/Render.

**Spec:** Yêu cầu user 2026-09-14: "đọc toàn bộ codebase so sánh với MAIA, chọn điểm khác biệt làm tiếp không làm giống, xoá hướng dư thừa n8n, supply chain". Nguồn MAIA: https://www.getmaia.ai/en, https://en.getmaia.ai/, https://docs.getmaia.ai/en/help/collections/4233333-release-notes.

## Global Constraints

- Không code khi chưa có "go"/duyệt rõ ràng.
- Xoá n8n toàn bộ; supply-chain chỉ tỉa bloat, giữ core API (graph.py + SupplyChainController + frontend service).
- Không phá migration V1–V11; V12 xử lý bằng drop-if-exists.
- Chốt port supply-chain chuẩn 8020 (khớp docker-compose.dev.yml + api/Dockerfile).
- Mọi task có lệnh verify + expected rõ ràng.

---

## File Structure

- Xoá: `n8n-workflows/` (01-document-ingestion.json, 02-ai-chat-automation.json, 03-scheduled-summary.json, README.md)
- Dọn: `docker/docker-compose.yml:141-183`, `docker/docker-compose.dev.yml:107-141`, `.env.example:74-78`, `README.md:215`, `backend/.../V12__n8n_analytics.sql`
- Tỉa: `supply-chain-module/*.ipynb` (6 files), `supply-chain-module/mlruns/`, `supply-chain-module/mlops/mlflow.db`, `supply-chain-module/Dockerfile` (port 8000 sai), archive `supply-chain-module/dashboard/app.py`
- Giữ: `supply-chain-module/api/main.py`, `api/services.py`, `api/mlflow_models.py`, `api/requirements.txt`, `backend/.../SupplyChain*`, `llm-router/agent/graph.py:36-98`, `frontend/src/services/supplyChainApi.ts`
- Lock diff: `docs/`, `eval/`, `agent/hitl.py`, `llm-router/app/main.py`, `tasks/notes/decision-maia-diff-2026-09-14.md`

---

### Task 1: Xoá folder n8n-workflows

**Files:**
- Delete: `n8n-workflows/01-document-ingestion.json`, `n8n-workflows/02-ai-chat-automation.json`, `n8n-workflows/03-scheduled-summary.json`, `n8n-workflows/README.md`
- Test: none (filesystem check)

**Interfaces:**
- Consumes: không có
- Produces: folder `n8n-workflows/` biến mất; Task 2 dọn reference còn lại

- [ ] **Step 1: Xóa folder**
```bash
rm -rf n8n-workflows
```
- [ ] **Step 2: Verify đã xoá**
Run: `ls n8n-workflows 2>&1; grep -r "webhook/document-uploaded\|chat-question" --include="*.json" . 2>&1 | head`
Expected: `No such file or directory`, grep rỗng
- [ ] **Step 3: Commit**
```bash
git add -A && git commit -m "chore: remove n8n-workflows demo (duplicate ingestion/chat/summary)"
```

### Task 2: Dọn reference n8n trong compose/env/README

**Files:**
- Modify: `docker/docker-compose.yml:141-183` (xoá services n8n/n8n-postgres + volumes n8n_data), `docker/docker-compose.dev.yml:107-141`, `.env.example:74-78`, `README.md:215`
- Test: `docker compose config` dry-run

**Interfaces:**
- Consumes: Task 1 (folder đã xoá)
- Produces: zero `grep -rn n8n` ngoài docs lịch sử

- [ ] **Step 1: Xoá blocks n8n trong 2 compose + env + README**
```yaml
# Xoá toàn bộ block này trong docker/docker-compose.yml:141-183
# n8n:
#   image: n8nio/n8n
#   ports: ["5678:5678"]
# n8n-postgres: ...
```
```bash
# .env.example:74-78 xoá:
# N8N_HOST / N8N_PORT / N8N_POSTGRES_* (optional automation)
```
- [ ] **Step 2: Verify**
Run: `grep -rn "n8n" docker/ .env.example README.md 2>&1 | grep -v AUDIT_REPORT | grep -v PLAN_HYBRID || echo CLEAN`
Expected: `CLEAN`
Run: `docker compose -f docker/docker-compose.yml config -q && echo COMPOSE_OK`
Expected: `COMPOSE_OK`
- [ ] **Step 3: Commit**
```bash
git add docker/docker-compose.yml docker/docker-compose.dev.yml .env.example README.md && git commit -m "chore: purge n8n references from compose/env/docs"
```

### Task 3: Xử lý migration V12 n8n (an toàn)

**Files:**
- Modify: create `backend/src/main/resources/db/migration/V13__drop_n8n_analytics.sql`
- Test: `backend` migration test

**Interfaces:**
- Consumes: Task 1-2
- Produces: 3 bảng `document_analytics/escalation_queue/document_summaries` drop-if-exists

- [ ] **Step 1: Viết migration drop**
```sql
DROP TABLE IF EXISTS document_analytics;
DROP TABLE IF EXISTS escalation_queue;
DROP TABLE IF EXISTS document_summaries;
```
- [ ] **Step 2: Verify**
Run: `ls backend/src/main/resources/db/migration/ | grep V1; grep -r "n8n_analytics\|escalation_queue" backend/src --include="*.java" | head`
Expected: V1–V13 liệt kê đủ; không entity Java nào đọc 3 bảng này
- [ ] **Step 3: Commit**
```bash
git add backend/src/main/resources/db/migration/V13__drop_n8n_analytics.sql && git commit -m "chore: drop n8n analytics tables (V13)"
```

### Task 4: Tỉa supply-chain bloat (ipynb + mlruns + db)

**Files:**
- Delete: `supply-chain-module/supply_chain_eda.ipynb`, `demand_forecasting.ipynb`, `inventory_optimization.ipynb`, `route_optimization.ipynb`, `supplier_risk.ipynb`, `anomaly_detection.ipynb`, `supply-chain-module/mlruns/`, `supply-chain-module/mlops/mlflow.db`
- Keep: `supply-chain-module/api/main.py:1-101`, `api/services.py:1-292`
- Test: `supply-chain-module/api/tests/test_api.py`

**Interfaces:**
- Consumes: không có
- Produces: core API nguyên vẹn; Task 5-7 dựa vào đó

- [ ] **Step 1: Xoá bloat**
```bash
rm -f supply-chain-module/*.ipynb && rm -rf supply-chain-module/mlruns supply-chain-module/mlops/mlflow.db
```
- [ ] **Step 2: Verify core còn + test pass**
Run: `ls supply-chain-module/*.ipynb 2>&1; ls supply-chain-module/api/main.py supply-chain-module/api/services.py && python -m pytest supply-chain-module/api/tests/test_api.py -v`
Expected: `No such file`, 9 tests PASS
- [ ] **Step 3: Commit**
```bash
git add -A && git commit -m "chore: trim supply-chain bloat, keep core api"
```

### Task 5: Gộp Dockerfile chốt port 8020

**Files:**
- Delete: `supply-chain-module/Dockerfile` (port 8000 sai)
- Modify: `supply-chain-module/api/Dockerfile` (giữ EXPOSE 8020)
- Test: `docker build`

**Interfaces:**
- Consumes: Task 4
- Produces: port chuẩn 8020 khớp `docker-compose.dev.yml:159-174` + `render.yaml:3-25`

- [ ] **Step 1: Xoá Dockerfile gốc sai port**
```bash
rm supply-chain-module/Dockerfile
```
- [ ] **Step 2: Verify**
Run: `grep -rn "8000\|8020" supply-chain-module/*/Dockerfile supply-chain-module/Dockerfile docker/docker-compose.dev.yml render.yaml 2>&1 | head -n 20`
Expected: chỉ còn 8020, không còn `supply-chain-module/Dockerfile:8000`
- [ ] **Step 3: Commit**
```bash
git add -A && git commit -m "fix: unify supply-chain port to 8020"
```

### Task 6: Archive dashboard Streamlit sai URL

**Files:**
- Move: `supply-chain-module/dashboard/app.py` → `supply-chain-module/_archive/dashboard_app.py`
- Test: `grep -r dashboard render.yaml`

**Interfaces:**
- Consumes: Task 4-5
- Produces: dashboard không còn block deploy chính

- [ ] **Step 1: Archive**
```bash
mkdir -p supply-chain-module/_archive && git mv supply-chain-module/dashboard/app.py supply-chain-module/_archive/dashboard_app.py
```
- [ ] **Step 2: Verify**
Run: `ls supply-chain-module/dashboard/ 2>&1; grep -rn "SUPPLY_CHAIN_API_URL" supply-chain-module/_archive/dashboard_app.py | head -n 3`
Expected: folder rỗng/mất; URL cũ `127.0.0.1:8000` lộ rõ để sửa sau nếu un-archive
- [ ] **Step 3: Commit**
```bash
git add -A && git commit -m "chore: archive supply-chain dashboard (stale 8000 url)"
```

### Task 7: Khóa core supply-chain còn dùng (không xoá)

**Files:**
- Keep/Verify: `backend/src/main/java/com/smartdocchat/controller/SupplyChainController.java:15-46`, `llm-router/agent/graph.py:36-98`, `frontend/src/services/supplyChainApi.ts`, `frontend/src/pages/SupplyChainPage.tsx`
- Test: `llm-router` + frontend build

**Interfaces:**
- Consumes: Task 4-6
- Produces: chain forecast/route/risk còn chạy; là điểm diff ops-edge vs MAIA

- [ ] **Step 1: Ghi chú giữ (không xoá code)**
```bash
grep -rn "SUPPLY_CHAIN_ENDPOINTS\|SupplyChainController\|supplyChainApi" llm-router/agent/graph.py backend/src/frontend/src 2>&1 | head -n 10
```
- [ ] **Step 2: Verify**
Run: `python -m pytest llm-router/tests -q 2>&1 | tail -n 5`
Expected: PASS (fallback deterministic khi URL rỗng vẫn chạy)
- [ ] **Step 3: Commit (notes)**
```bash
git add tasks/notes/decision-maia-diff-2026-09-14.md && git commit -m "docs: lock supply-chain core as ops-edge diff vs MAIA"
```

### Task 8: Differentiation 1+2 — Legal-VN citation + abstention (khác MAIA DACH)

**Files:**
- Modify: `tasks/notes/decision-maia-diff-2026-09-14.md`
- Verify: `backend/.../service/ChatService.java`, `eval/questions.json` (31Q)
- Test: eval keyword check

**Interfaces:**
- Consumes: Task 7
- Produces: spec citation Điều/Khoản/Điểm + từ chối khi thiếu căn cứ

- [ ] **Step 1: Ghi quyết định vào notes**
```markdown
# Quyết định: Legal-VN depth > MAIA industrial-generic
- Mọi answer phải có citation Điều/Khoản/Điểm, nếu không đủ chunk → abstain "không đủ căn cứ".
- Không build Insight Hub kiểu MAIA; build audit trail bất biến.
```
- [ ] **Step 2: Verify**
Run: `grep -rn "abstain\|không đủ căn cứ\|citation" backend/src eval/*.py 2>&1 | head`
Expected: thấy hook để gắn (hoặc TODO có chủ)
- [ ] **Step 3: Commit**
```bash
git add tasks/notes/decision-maia-diff-2026-09-14.md && git commit -m "docs: decide legal-VN citation diff vs MAIA"
```

### Task 9: Differentiation 3 — Eval harness mở (khác reranking đóng MAIA)

**Files:**
- Modify: `docs/EVALUATION.md`, `eval/eval.py:79-100`
- Test: `python -m pytest eval/ -q`

**Interfaces:**
- Consumes: Task 8
- Produces: benchmark recall/hallucination công khai

- [ ] **Step 1: Mở eval 31Q + llm_judge**
```python
# eval/eval.py đã có: run_eval(questions.json, llm_judge) -> precision/recall log
# Task này chỉ gắn badge + công khai kết quả, không đổi algorithm
```
- [ ] **Step 2: Verify**
Run: `python -m pytest eval/ -q 2>&1 | tail -n 5`
Expected: PASS
- [ ] **Step 3: Commit**
```bash
git add docs/EVALUATION.md eval/eval.py && git commit -m "docs: open eval harness diff vs MAIA closed rerank"
```

### Task 10: Differentiation 4+5 — HITL guard + local-first + ops-edge (khác MAIA 49€/seat)

**Files:**
- Verify: `agent/hitl.py`, `agent/graph/workflow.py`, `llm-router/app/main.py:28-43`, `docs/agent_architecture.md`
- Test: `npm run test` / `pytest agent`

**Interfaces:**
- Consumes: Task 7-9
- Produces: agentic có approve/TTL + Ollama-first cost-zero + supply-chain hiện trường

- [ ] **Step 1: Khóa spec (không code lớn)**
```markdown
- HITL: mọi tool gửi mail/Jira/webhook phải pause-approve, TTL 15p (agent/hitl.py).
- Local-first: Ollama qwen3:8b + pgvector fallback khi Cloudflare tắt.
- Ops-edge: giữ supply-chain forecast/route/risk cho kho/xưởng tiếng Việt.
```
- [ ] **Step 2: Verify**
Run: `grep -rn "approve\|HITL\|TTL" agent/hitl.py 2>&1 | head; grep -rn "ollama\|qwen3" llm-router/app/main.py .env.example 2>&1 | head`
Expected: thấy hook HITL + Ollama fallback
- [ ] **Step 3: Commit**
```bash
git add tasks/notes/decision-maia-diff-2026-09-14.md docs/agent_architecture.md && git commit -m "docs: lock HITL+local-first+ops diff vs MAIA"
```

## Self-Review

- Spec coverage: prune n8n (T1-3) đủ; tỉa supply bloat giữ core (T4-7) đủ; diff MAIA 5 hướng gom 3 tasks (T8-10) đủ, không làm Insight Hub/SharePoint/GPT-5 clone.
- Placeholder scan: không TBD/TODO; mọi step có lệnh + expected cụ thể.
- Type consistency: port 8020 xuyên suốt; V13 drop-if-exists không gãy V1-V11; core API tên giữ nguyên.

## Execution Handoff

Plan complete and saved to `plans/plan-maia-diff-prune-2026-09-14.md`. Two execution options:

1. Subagent-Driven (recommended) - dispatch fresh subagent per task, review between tasks
2. Inline Execution - batch execution with checkpoints

Which approach?
