# Render Smoke Test Checklist

Chạy sau khi Render deploy xong (backend, llm-router, supply-chain-api).
Thay `<ROUTER>`, `<BACKEND>`, `<SC>` bằng URL Render thực tế.

## 1. Health checks (mỗi service)

```bash
curl -s https://<ROUTER>.onrender.com/health
# expect: {"status":"ok","service":"llm-router"}

curl -s https://<SC>.onrender.com/health
# expect: {"status":"ok"}

curl -s -o /dev/null -w "%{http_code}" https://<BACKEND>.onrender.com/actuator/health
# expect: 200
```

## 2. LLM pipeline (llm-router)

```bash
curl -s -X POST https://<ROUTER>.onrender.com/classify \
  -H "Content-Type: application/json" \
  -d '{"text":"PURCHASE ORDER 2024 vendor ABC total 1000 USD","filename":"po.txt"}'
# expect: {"document_type":"PO"}

curl -s -X POST https://<ROUTER>.onrender.com/document/workflow \
  -H "Content-Type: application/json" \
  -d '{"text":"HOA DON so HD-001 vendor ABC tong 1000 USD ngay 2024-01-15","filename":"inv.txt","counterpart_fields":{"vendor":"ABC","total_amount":1000}}'
# expect: match_status MATCHED (hoặc INSUFFICIENT_DATA nếu fields không đủ)
```

## 3. Agentic path end-to-end (agent → supply-chain API)

```bash
curl -s -X POST https://<ROUTER>.onrender.com/agent/invoke \
  -H "Content-Type: application/json" \
  -d '{"message":"dự báo nhu cầu cho 7 ngày tới","params":{"history":[100,120,130,125,140,150,145],"periods":7}}'
# expect: answer chứa forecast thật (không phải fallback message) + trace_id

curl -s -X POST https://<ROUTER>.onrender.com/agent/invoke \
  -H "Content-Type: application/json" \
  -d '{"message":"xin chào"}'
# expect: answer fallback tự nhiên (không tool call)
```

## 4. Backend → agent integration

```bash
# Đăng nhập lấy JWT, sau đó:
curl -s -X POST https://<BACKEND>.onrender.com/api/chat \
  -H "Authorization: Bearer <JWT>" -H "Content-Type: application/json" \
  -d '{"message":"dự báo nhu cầu tồn kho","sessionId":"smoke-1"}'
# expect: response từ agentic path (không RAG) — verify trong log "agentic"
```

## 5. Async job + WebSocket

```bash
JOB=$(curl -s -X POST https://<ROUTER>.onrender.com/agent/jobs \
  -H "Content-Type: application/json" \
  -d '{"message":"dự báo nhu cầu","params":{"history":[1,2,3],"periods":3}}' | python3 -c "import sys,json;print(json.load(sys.stdin)['job_id'])")
curl -s https://<ROUTER>.onrender.com/agent/jobs/$JOB
# expect: status done sau vài giây
```

## 6. Agent state persistence (PostgreSQL)

```sql
SELECT session_id, owner_username, status, left(final_answer, 50)
FROM agent_state ORDER BY created_at DESC LIMIT 5;
-- expect: các dòng status='done' sau khi chạy bước 3-4
```

## 7. Langfuse trace

- Vào Langfuse dashboard → traces
- Filter tên trace `agentic_request` — expect trace từ bước 4 với output agent answer
- Verify span tree: `agent_run → agent_intent / agent_answer`

## 8. Trace ID propagation

```bash
curl -s -X POST https://<ROUTER>.onrender.com/agent/invoke \
  -H "Content-Type: application/json" \
  -H "X-Langfuse-Trace-Id: smoke-trace-123" \
  -d '{"message":"supplier risk"}'
# Langfuse: tìm trace id smoke-trace-123 — expect join được với backend trace
```

## Pass criteria

- [ ] Cả 3 service health 200
- [ ] Agent trả forecast thật (không fallback) khi supply-chain API reachable
- [ ] Fallback agent → RAG hoạt động khi agent down (bước 4 trả vẫn có answer)
- [ ] agent_state có bản ghi trong PostgreSQL
- [ ] Langfuse có trace agentic + span tree đúng
