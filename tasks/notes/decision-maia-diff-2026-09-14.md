# Quyết định MAIA-diff + prune (2026-09-14)

## Nguồn
- Skill: `writing-plans` + `repo-harness-plan` đã đọc.
- MAIA: Prodlane MAIA (getmaia.ai) — DACH industrial, 49€/seat, High Precision Mode, Insight Hub, reranking đóng, SharePoint/Confluence, GPT-5/Claude, GDPR/EU.

## Tradeoff
1. **n8n xoá toàn bộ (4 files + compose/env/README + V15 drop — V13/V14 đã tồn tại nên dùng V15):** duplicate ingestion/chat/summary, sai contract (legal-chunks, confidence), zero reference. Rủi ro thấp.
2. **supply-chain KHÔNG xoá toàn bộ:** backend SupplyChainController + llm-router/agent/graph.py:36-98 + frontend supplyChainApi + render.yaml còn phụ thuộc. Xoá hết = gãy forecast/route/risk thành fallback. Chỉ tỉa: 6 ipynb, mlruns/, mlflow.db, Dockerfile port 8000 sai, archive dashboard Streamlit.
3. **Không giống MAIA:** không clone Insight Hub / SharePoint sync / Automodel GPT-5. Làm tiếp: legal-VN citation Điều/Khoản/Điểm + abstention, eval 31Q mở, HITL approve/TTL, local-first Ollama qwen3:8b cost-zero, supply-chain ops-edge kho/xưởng TV.

## Open Q cần duyệt
- V12 đã chạy prod chưa? Rồi → V13 drop; chưa → xoá file V12 luôn.
- Dashboard archive hay xoá khỏi render.yaml hẳn?
- Scope legal-VN vs industrial-EN chốt trước khi build reranking riêng.

## Track C verify (2026-09-14)

### T7 — Core supply-chain còn nguyên (không xoá)
- Hook tồn tại: `llm-router/agent/graph.py:36` (`SUPPLY_CHAIN_ENDPOINTS` forecast/route/risk + deterministic fallback khi URL rỗng), `backend/.../SupplyChainController.java:18`, `frontend/src/services/supplyChainApi.ts:95`.
- `python3 -m pytest llm-router/tests -q`: collection ERROR ở `test_document_graph.py` (thiếu dep `langfuse`, pre-existing); bỏ qua file đó → 61 passed, 10 failed toàn do thiếu plugin `pytest-asyncio` (pre-existing, không liên quan supply-chain).

### T8 — Quyết định: Legal-VN depth > MAIA industrial-generic
- Mọi answer phải có citation Điều/Khoản/Điểm, nếu không đủ chunk → abstain "không đủ căn cứ".
- Không build Insight Hub kiểu MAIA; build audit trail bất biến.
- Hook đã có: `ChatService.java` gọi `messageHandler.buildAbstentionResponse()` (4 điểm: 186/212/282/331), `LegalStructureParser.java` nhận diện Chương/Điều/Khoản/Điểm, `CragConfig.abstainEnabled` + `application.yml:117 abstain-enabled: true`.

### T9 — Eval harness mở (khác reranking đóng MAIA)
- `python3 -m pytest eval/ -q`: 0 tests collected (harness là script, không phải pytest suite — expected).
- Hook đã có: `eval/eval.py` + `eval/agent_eval.py` nhận `--llm_judge` (`LLMJudge`), `eval/questions.json` 31 câu. Không đổi algorithm.

### T10 — Lock HITL + local-first + ops-edge
- HITL: tool gửi mail/Jira/webhook phải pause-approve qua `agent/hitl.py` (`HITLStore`, approve/rejected, TTL cấu hình `settings.hitl_approval_ttl_seconds`, default 3600s).
- Local-first: opt-in `LOCAL_OLLAMA_URL` (`.env.example:75-85`, `llm-router/app/config.py:53-59`, providers `local_ollama`); default model `llama3.2`, `qwen3:8b` chỉ là ví dụ trong `service.py:23`.
- Ops-edge: giữ supply-chain forecast/route/risk cho kho/xưởng tiếng Việt (xem T7).
