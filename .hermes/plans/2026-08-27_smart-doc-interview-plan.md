# Smart Document Chatbot — Plan Phỏng Vấn (2026-08-27)

**Mục tiêu:** Đồ án ready để phỏng vấn — production chạy thật, eval metrics cải thiện, gap analysis biến thành câu chuyện portfolio.

**Priority:** 1. Interview readiness → 2. Eval metrics → 3. Production verification → 4. Local fallback → 5. qwen3-vi PoC → 6. LangGraph/n8n (optional)

---

## Phase 1 — Tổng duyệt + checklist (ngay)

**1.1. Đọc + tóm tắt toàn bộ tính năng**
- Đọc `README.md` (400 dòng) — architecture, tech stack, API, eval, deployment.
- Đọc `docs/EVALUATION.md`, `docs/OBSERVABILITY.md`, `docs/BENCHMARK_LOCAL_QWEN_VS_CLOUD.md`, `docs/FINETUNE_MLX_LORA_REPORT.md`.
- Đọc eval results: `eval/results/full_eval_2026-08-26_diag_doc101.json` — retrieval 70.97%, hallucination 9.68%, 31 questions.
- Tạo file `docs/INTERVIEW_READINESS.md` summarizing:
  - Architecture diagram: Spring Boot + React + LLM Router + Cloudflare Workers AI + Ollama fallback.
  - Mọi tính năng production-ready: auth JWT, owner isolation, CRAG loop, SSE streaming, prompt-injection defense, rate limiting (bucket4j), circuit breaker, graceful shutdown, Flyway migrations, 23 unit tests.
  - Observability: Prometheus + Actuator, RAG metrics, structured JSON logs, OTEL tracing, Grafana/Promtail/Alertmanager.
  - Security: CSRF, JWT, rate limiting, prompt-injection heuristic, secret strength validator, security headers.
  - CI/CD: GitHub Actions — test → build → Trivy scan → SonarCloud.
  - Eval pipeline: `eval/eval.py` + `eval/run_fixture_eval.py`, grading contract v2, baseline commit ceee8e8 (3 questions, 100% retrieval, 0% hallucination).
  - LLM stack: primary llama-3.3-70b (Cloudflare), fallback qwen3:8b (Ollama), finetune qwen3-vi (MLX LoRA PoC).
  - Gaps: LangGraph agent (port 9000) chưa nối, qwen3:8b chưa integrate production, qwen3-vi có artifact, eval metrics thấp, Vietnamese stemming chưa có, n8n chưa workflow.

**1.2. Review eval pipeline**
- Đọc `eval/eval.py` + `eval/run_fixture_eval.py` — đảm bảo regression test chạy được.
- Đảm bảo baseline commit ceee8e8 có 3 questions 100% retrieval — có thể chạy lại.

**1.3. Review 30 commits gần**
- Ánh xạ mỗi feat commit → 1 dòng mô tả cho phỏng vấn.
- Commits gần: `292dfc5` Langfuse tracing, `347f8b5` Vietnamese stopword filtering, `9aa2e21` bucket4j rate limiting, `a4b452e` circuit breaker Cloudflare, `7624929` e2e smoke spec.

---

## Phase 2 — Cải thiện eval metrics (priority cao)

**2.1. Vietnamese stemming/lexical boost**
- Hiện tại: chỉ stopword filtering + phrase bonus (commit `347f8b5`).
- Cần thêm stemming cho Vietnamese queries — VD: `vn_stemmer` hoặc custom rules.
- Target: retrieval 70.97% → 85%+.

**2.2. Doc content review — fix 3 hallucinations**
- 3 hallucinations: Q25 backup/postgresql — No retrieval nhưng lại tái dựng thông tin sai.
- Đọc doc tương ứng, xem có thể cải thiện document chunking/content.

**2.3. Chạy lại eval production sau mỗi thay đổi**
- Đảm bảo có script để chạy eval production → đo retrieval_accuracy + answer_correctness.

---

## Phase 3 — Production verification (smoke test)

**3.1. Staging health check**
- `curl https://smart-doc-backend-h4mt.onrender.com/api/health` → 200.

**3.2. Smoke test**
- Chạy `scripts/production_smoke.py` → pass.

**3.3. Chạy eval production baseline**
- Chạy `eval/run_fixture_eval.py` → 3 questions, 100% retrieval, 0% hallucination.

---

## Phase 4 — Productionize local fallback (qwen3:8b)

**4.1. Đọc `llm-router/` code**
- Hiểu cách router gọi Cloudflare Workers AI, circuit breaker hiện tại.

**4.2. Integrate qwen3:8b vào router**
- Làm fallback khi Cloudflare rate-limited (429) hoặc timeout.
- Đảm bảo fallback thực sự hoạt động (test scenario: mock Cloudflare failure → router fallback qwen3:8b).

**4.3. Benchmark cập nhật**
- Viết vào `docs/BENCHMARK_LOCAL_QWEN_VS_CLOUD.md` cập nhật: latency, quality so sánh Cloud vs local fallback.

---

## Phase 5 — Fix qwen3-vi PoC (hoặc document thành story)

**5.1. Đọc `finetune/` + `docs/FINETUNE_MLX_LORA_REPORT.md`**
- Hiểu pipeline, artifact `<tool_call>`.

**5.2. Fix artifact**
- Option A: thêm `PARAMETER stop` vào Modelfile.
- Option B: post-process strip `<tool_call>` token + echo question.
- Option C: re-train với chat template chuẩn Qwen3, dataset ≥500 samples.

**5.3. Nếu không fix được, document thành story NAB**
- "Evidence-driven local adaptation — fine-tune qwen3-vi cho Vietnamese, đo lường artifact, đề xuất hướng giải quyết."

---

## Phase 6 — LangGraph agent + n8n (optional)

**6.1. Đọc `agent/` + `docs/agent_architecture.md`**
- Đảm bảo hiểu endpoint `/v1/agent/*`, mục đích service.

**6.2. Quyết định Option A hoặc B**
- Option A: Nối vào luồng chat chính.
- Option B: Giữ experimental, ghi chú rõ trong docs.

**6.3. n8n workflow (nếu cần)**
- Định nghĩa workflow đơn giản trong repo.

---

## Phase 7 — Final verification + portfolio prep

**7.1. Staging health check** — `curl .../api/health` → 200.

**7.2. Eval production chạy lại** → metrics cải thiện (retrieval ≥85%, hallucination ≤5%).

**7.3. Local fallback test** — mock Cloudflare failure → router fallback qwen3:8b → response đúng.

**7.4. Smoke test** — `production_smoke.py` chạy → pass.

**7.5. README.md** — đảm bảo đầy đủ: architecture, tech stack, API, eval, deployment.

**7.6. `docs/INTERVIEW_READINESS.md`** — hoàn thiện, ready để phỏng vấn.

---

## Acceptance Criteria (khi nào gọi "xong")

- [ ] `docs/INTERVIEW_READINESS.md` tồn tại, summarizing mọi tính năng + metrics + story.
- [ ] Eval metrics cải thiện: retrieval ≥85%, hallucination ≤5% (hoặc có story rõ ràng nếu không cải thiện được).
- [ ] Staging health check pass (`curl .../api/health` → 200).
- [ ] Smoke test pass (`production_smoke.py`).
- [ ] Local fallback qwen3:8b integrate vào router (hoặc document rõ ràng là PoC).
- [ ] qwen3-vi PoC: fix artifact hoặc document thành story NAB.
- [ ] README.md đầy đủ, mọi tính năng có mô tả.
- [ ] LangGraph agent + n8n: có trong docs (dù chưa nối) — trung thực về status.
