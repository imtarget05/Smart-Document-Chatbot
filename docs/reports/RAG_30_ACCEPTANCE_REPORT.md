# Báo cáo nghiệm thu RAG — bộ 30 câu (rag_30)

**Ngày:** 2026-09-17 · **Commit:** `9f815aa` · **Trạng thái:** CHẠY THẬT HOÀN TẤT — chờ chấm thủ công (manual grading)

## 1. Kết quả đã hoàn thành

### 1.1 Bộ dữ liệu + fixture (DONE)
- `eval/fixtures/rag_nghithu_fixture.txt` — tài liệu tổng hợp "Luật Doanh nghiệp 2020 (bộ kiểm thử)", 110 dòng, 12 Điều, đánh dấu `LN2020-001`.
- `eval/rag_30_questions.json` — **30 câu đúng cấu trúc 15/10/5** (validated bằng script, ID duy nhất):
  - 15 `answered` (A1–A15, neo Điều 1.2 → 10.3)
  - 10 `unanswerable` (U1–U10, nội dung ngoài phạm vi tài liệu)
  - 5 `conflict` (C1–C5, mâu thuẫn/chưa rõ: Điều 3.3, 5.1, 8.3, 9.1↔9.3, 11.2)
- `eval/rag30.py` — builder sinh JSON + assert 15/10/5; `python3 eval/rag30.py` tái sinh được.
- Chấm điểm thiết kế: thủ công (PASS/PARTIAL/FAIL) trên trace; LLM-judge không phải ground truth.

### 1.2 Pipeline runner (DONE, đã chạy end-to-end)
- `eval/run_rag_30.py` — register → login (JWT) → CSRF → upload fixture → 30× `POST /chat/ask` (`{sessionId, documentId, message, mode:"rag"}`) → trace JSON.
- Trace mỗi câu chứa: `answer_from_backend`, `citations_backend` (sources), `source_chunks_backend`, `confidence_backend`, `confidence_score_backend`, `rag_strategy_backend`, `latency_ms`, các `expected_*`, `conflict_note`, và placeholder `result_manual` / `notes_manual`.
- Chạy verify trên mock backend (`eval/mock_backend.py`, port 8081): **RC=0, 30/30 câu, trace lưu `eval/results/rag_30_trace_mock.json`**, mọi field có giá trị (conf/strategy/citations không null), latency 7–39ms.
- Helper: `eval/inspect_trace.py` — thống kê nhanh trace.

### 1.3 Trạng thái LoRA / training-job orchestration (UPDATED 2026-09-18)

> **Thay đổi hợp đồng (plan 2026-09-18): adapter không được serve cho tới khi
> promote.** Luồng Airflow cũ (`POST /v1/agent/retrain` + kiểm tra file adapter
> tồn tại) đã bị thay bằng hợp đồng training-job có thể kiểm chứng:
>
> - Agent service: `POST /v1/training-jobs` → `{job_id, status}`;
>   `GET /v1/training-jobs/{job_id}` → `{status, adapter_uri, sha256,
>   metrics, model_version}` (xem `agent/training_jobs.py`).
> - Airflow DAG (`airflow/dags/model_retrain_pipeline.py`): build dataset →
>   submit job → poll tới trạng thái terminal → validate adapter URI, SHA-256,
>   version và quality-gate của **đúng job này**; stale artifact từ run cũ bị
>   từ chối theo fingerprint job (`result_fingerprint`).
> - GPU training vẫn ở ngoài Airflow (runner qua `TRAINING_RUNNER_URL`);
>   Airflow chỉ orchestrate + validate.
> - Rollout: job SUCCEEDED chỉ đăng ký version `Candidate` trong registry;
>   serving traffic chỉ đổi qua endpoint promote xác thực riêng
>   (`POST /v1/training-jobs/{job_id}/promote`), rollback có thể đảo ngược
>   (`.../rollback`); `/v1/agent/retrain` giờ là evaluation gate + submit job.

> Cập nhật 2026-09-18: adapter MLX cũ (`finetune/adapters/adapters.safetensors` +
> checkpoint step 100/200 trên `mlx-community/Qwen3-4B-Instruct-2507-4bit`) đã bị xoá
> khỏi repo (`git rm`). Adapter hiện hành: **PEFT LoRA trên `Qwen/Qwen2.5-1.5B-Instruct`**
> tại `finetune/adapters/lora-t4/` (train trên Colab T4, `r=8`, `alpha=32`, `dropout=0.05`).
> Muốn xem lại artifact cũ: `git show HEAD~1:finetune/adapters/adapters.safetensors`.
- Adapter hiện tại: `finetune/adapters/lora-t4/adapter_model.safetensors` (PEFT, r=8, alpha=32, dropout 0.05, targets q/k/v/o/gate/up/down_proj) + `adapter_config.json`.
- Config: PEFT LoRA trên `Qwen/Qwen2.5-1.5B-Instruct`, rank 8, alpha 32, dropout 0.05, targets q/k/v/o/gate/up/down_proj (luồng Colab T4 hiện hành).
- **Serving không load adapter**: không có `load_adapter`/`PeftModel` nào trong backend; backend chạy LLM Cloudflare Workers AI (`@cf/meta/llama-3.3-70b`) qua llm-router (application.yml). Airflow retrain DAG chỉ verify artifact tồn tại, không áp vào serving path.
- Kết luận: **LoRA ở trạng thái "đã train, chỉ là Candidate — chưa serve"**:
  serving không load adapter cho tới khi promote hiển danh; rollback về
  version đã duyệt trước đó luôn khả dụng. Rollout runner/artifact-store:
  cần `TRAINING_RUNNER_URL` (GPU runner ngoài), artifact-store cho
  `adapter_uri`, và `RETRAIN_TOKEN` khớp `INTERNAL_SERVICE_TOKEN`.

## 2. Chạy thật trên backend Docker (HOÀN TẤT 2026-09-17)

- Stack: `docker compose --env-file .env -f docker/docker-compose.yml up -d llm-router smart-document` → backend **healthy** (Neon PG + Qdrant Cloud + llm-router/Cloudflare Workers AI).
- Lệnh: `python3 eval/run_rag_30.py --base-url http://localhost:8080/api` → **RC=0, 30/30 câu**.
- Trace thật: `eval/results/rag_30_trace.json` (documentId=255, latency 1.3–3.0s/câu).
- Kết quả hệ thống: CRAG strategy **28 direct + 2 no_evidence**; confidence **28 high + 2 low**; mỗi câu có 3 citations thật (sourceType=USER, score 0.64–1.0) và chunks trích đúng fixture.
- Điểm sáng: câu conflict C4 retrieve được cả Điều 9.3 lẫn Điều 9.2 (đúng thiết kế mâu thuẫn); câu U4 (unanswerable) retrieve chunk liên quan nhưng thiếu đủ thông tin — đúng kịch bản chấm "không bịa".

### Bug đã vá trong quá trình dựng
1. `docker/Dockerfile.backend` — base image `eclipse-temurin:17-jre-alpine` / `maven:3.9-eclipse-temurin-17-alpine` đã bị gỡ khỏi Docker Hub → đổi sang Debian (`maven:3.9-eclipse-temurin-17`, `eclipse-temurin:17-jre`) + apt-get thay apk.
2. `llm-router/Dockerfile` — file repo có permission 700 → `COPY --chown=10001:10001` để user runtime đọc được.
3. `docker/docker-compose.yml` — (a) interpolation `${JWT_SECRET}` đọc `docker/.env` không tồn tại → phải chạy với `--env-file .env`; (b) pgjdbc **không hỗ trợ `user:password@` trong JDBC URL** → sinh biến `NEON_JDBC_URL` (credentials chuyển vào query params) bằng `eval/derive_env.py`.
4. `eval/run_rag_30.py` — register/login cần header `X-XSRF-TOKEN` (đã thêm, bám `run_fixture_eval.py`).

## 3. Còn pending — chấm thủ công
- `result_manual` / `notes_manual` trong trace đang rỗng (chủ ý — chấm PASS/PARTIAL/FAIL bằng tay theo thiết kế, LLM-judge không phải ground truth).
- Chấm theo category: 15 answered (đúng Điều + keyword), 10 unanswerable (phải từ chối/trình bày giới hạn, không bịa), 5 conflict (phải nêu cả hai điều/trình bày giới hạn, không suy diễn).

## 4. File list (mới, chưa commit)
| File | Vai trò |
|---|---|
| `eval/fixtures/rag_nghithu_fixture.txt` | Fixture tài liệu 110 dòng |
| `eval/rag30.py` | Builder bộ 30 câu (assert 15/10/5) |
| `eval/rag_30_questions.json` | Dataset 30 câu |
| `eval/run_rag_30.py` | Pipeline runner (auth→upload→30 ask→trace) |
| `eval/inspect_trace.py` | Helper thống kê trace |
| `eval/results/rag_30_trace_mock.json` | Trace verify harness (mock, không dùng chấm) |
| `docs/reports/RAG_30_ACCEPTANCE_REPORT.md` | Báo cáo này |
