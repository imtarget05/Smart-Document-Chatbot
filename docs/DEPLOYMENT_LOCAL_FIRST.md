# DEPLOYMENT CHỐT — Local-First (Hybrid by Classification)

Ngày chốt: 2026-09-18. Deployment duy nhất: **LOCAL-FIRST**.

## Chốt

1. **Training duy nhất**: Colab LLM Fine-tuning (LoRA Llama-3.2/Qwen) —
   `colab/finetune_lora_T4.ipynb`.
2. **Serve duy nhất**: Ollama/vLLM (model LoRA đã finetune) + Qdrant local
   là mặc định (`LOCAL_OLLAMA_URL=http://localhost:11434`).
3. **Cloud fallback** (Cloudflare Workers AI) **CHỈ** cho tài liệu **PUBLIC**.
4. **CONFIDENTIAL + local lỗi** → `403 policy_violation`, **không lén đẩy cloud**.
5. **Reranker**: pretrained `bge-reranker-v2-m3` inference thuần (không finetune).

## Bảng phân loại

| Classification | Local OK | Local lỗi → |
|:---|:---:|:---|
| PUBLIC | serve local | fallback Cloudflare Workers AI |
| CONFIDENTIAL | serve local | ⛔ 403 `policy_violation` — không ra cloud |

## Code

- Chặn: `llm-router/app/service.py::LLMRouter._active` (normalize
  `strip().lower()`, chặn mọi biến thể hoa/thường).
- HTTP: `llm-router/app/main.py::chat` — `policy_violation` → 403, còn lại → 503.
- Test: `llm-router/tests/test_service.py` — `test_policy_guard_*`.

## Verify

```bash
grep -rn "Local-First\|CONFIDENTIAL\|PUBLIC" README.md .env.example docs/DEPLOYMENT_LOCAL_FIRST.md plans/ tasks/ llm-router/app | head -30
cd llm-router && python3 -m pytest tests/test_service.py -q
```
