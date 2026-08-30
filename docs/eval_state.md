# Evaluation Pipeline — Current State & Plan

Đây là tài liệu trung thực về trạng thái evaluation pipeline của Smart Document Chatbot, dành cho nhà tuyển dụng AI Engineer hỏi sâu về chất lượng đo lường hệ thống.

## Mục đích
Evaluation pipeline đo chất lượng ответ hệ thống RAG (classic Java CRAG) và Agent Service (Python LangGraph) theo 2 track riêng biệt. Mục tiêu: có con số measurable (retrieval accuracy, answer correctness, hallucination rate, latency) dùng cho continuous quality monitoring.

## Track 1 — Classic RAG evaluation (`/chat/ask`)

### Script
`eval/eval.py` — Python script dùng requests, deterministic grading, không phụ thuộc LLM-judge.

### Grading approach
**Deterministic lexical grading** (không semantic LLM-judge):

1. **Concept coverage (AND-logic)** — Mỗi câu hỏi có thể định nghĩa `expected_concepts` (structured list, từng concept có các approved surface forms). Answer được normalize (lowercase, whitespace collapse, simple plural singularization, possessive strip) và kiểm tra TẤT cả concepts có xuất hiện không. Nếu thiếu 1 concept → answer incorrect. AND-logic ngăn false-positive từ answers chỉ mention keywords nhưng không trả lời đúng câu hỏi.

2. **Legacy keyword fallback** — Nếu không có structured concepts, dùng field `expected_answer_contains` — chỉ cần ít nhất 1 keyword xuất hiện trong normalized answer.

3. **Retrieval accuracy** — Field `expected_source_keywords` phải xuất hiện trong `sourceChunks` trả về (chứng minh retrieval đúng document/không hallucination từ documents wrong).

4. **Provider-error filter** — Có list failure contract strings (`temporarily unavailable`, `cloudflare_error`, `http status error`, v.v.). Response chứa các strings này được tách riêng (provider_error = true), không tính vào answer-correctness hoặc retrieval-accuracy denominators. Giữ eval fair khi LLM router down (không penalize hệ thống vì infrastructure issue).

### Metrics output
- `total_questions`
- `successful_requests` (HTTP 200 + không provider_error)
- `retrieval_accuracy` = retrieval_accurate / successful
- `answer_correctness` = correct / successful
- `hallucination_rate` = hallucination_cases / successful
- `avg_latency_ms`, `p95_latency_ms`, `min_latency_ms`, `max_latency_ms`
- `error_count` (HTTP/application errors, exclude provider_errors)
- `provider_errors`, `provider_error_rate`
- `genuine_llm_responses`

Results lưu `eval/results/eval_results.json`.

### Hallucination heuristic
Không phải LLM-judge. Heuristik: answer confident (≥ medium) + retrieval không có source keywords + answer không chứa "không tìm thấy" → flag potential hallucination. Dùng để monitor trend, không dùng làm ground truth.

### Question set
`eval/questions.json` — 28 câu hỏi (easy/medium/hard) bao phủ backend, vector-db, embedding, CRAG, ETL, frontend state, streaming, fallback, LLM, document formats, auth, multi-document synthesis, monitoring, hallucination, rate limiting, error handling, privacy, authorization, backup, concurrency, scaling, thread safety, consistency, network error, versioning, code review, deployment.

## Track 2 — Agent evaluation (`/agent/invoke`)

### Script
`eval/agent_eval.py` — Python script gọi agent service ( thẳng qua FastAPI port 9000 hoặc qua Spring Boot proxy).

### Grading approach
Tương tự deterministic lexical, thêm supply-chain-specific metrics:

- **Intent routing accuracy** — Nếu câu hỏi có `expected_intent`, so sánh với `agent_type` trả về (agent routing đúng specialist không).
- **Answer completeness** — AND-logic trên `expected_answer_contains` keywords.
- **Retrieval accuracy** — `expected_source_keywords` trong source texts.
- **Source citation rate** — Tỷ lệ response có `sources` không rỗng.
- **Hallucination** — Similar heuristic: answer có + retrieval không có source keywords + confidence ≥ 0.45 + không chứa "not found"/"no relevant".

Có **confusion matrix** cho từng metric binary (TP/FP/FN/TN/accuracy) — hữu ích để phát hiện bias (ví dụ recall cao nhưng precision thấp).

### Target modes
- Spring Boot proxy mode: `--base-url http://localhost:8080/api --token <JWT>` → gọi qua `/api/agent/invoke`.
- Direct agent mode: `--base-url http://localhost:9000 --internal-token <token> --direct-agent` → gọi thẳng FastAPI agent service.

## CI integration (current)

Chưa có CI job chạy evaluation thực tế (cần backend live + JWT + document đã upload).

Có `--validate-only` mode trong `eval/eval.py`: kiểm tra cấu trúc question set (có question text, expected answer field, lists đúng type) mà không cần backend. Dùng cho CI-safe validation.

### CI job thêm vào
Đã thêm `eval-questions-validate` job vào `.github/workflows/ci.yml`:
- Chạy `python eval/eval.py --validate-only --questions eval/questions.json`
- Validate cấu trúc question set mà không cần backend
- evaluation-as-code: question set 合 lệ → CI green

## Gaps (honest)

### 1. Không có golden reference answer
- Chỉ keywords/concepts → đo retrieval và coverage, không đo semantic correctness hoàn toàn.
- Ví dụ: question "Hệ thống xử lý thế nào khi retrieval confidence thấp?" → expected_keywords ["reformulation", "re-retrieval", "web search", "fallback"]. Answer nếu nói "hệ thống sẽ reformulation ثم re-retrieval" nhưng thiếu "fallback" → marked incorrect dù semantic có thể chấp nhận được.
- **Impact**: Answer correctness metric underestimate chất lượng thực nếu answer dùng từ khác nhưng đúng ý.

### 2. Không có LLM-judge supplement
- Không có LLM-based grader đo semantic alignment giữa answer và golden reference (hoặc giữa answer và question intent).
- Semantic correctness, hallucination detection chính xác hơn cần LLM-judge (cost + latency higher, nhưng accuracy tốt hơn heuristic).
- **Plan**: Tìm hiểu LLM-judge pattern (prompt: "Đánh giá answer có trả lời đúng question không, trích dẫn evidence từ source chunks, flag hallucination") cho Q3 roadmap.

### 3. Evaluation chưa chạy tự động trong CI
- Chỉ có `--validate-only` mode (kiểm tra cấu trúc, không cần backend).
- Evaluation thực tế cần backend live + JWT + document đã upload → không thể chạy trong CI không có cloud creds.
- **Plan**: Khi có cloud secrets, thêm CI job `eval-live` chạy evaluation thực tế (cần backend + document). Hoặc chạy evaluation trên staging environment schedule.

### 4. Golden reference dataset chưa có
- Không có dataset câu hỏi + golden reference answer (semantic) dùng cho LLM-judge hoặc manual grading.
- **Plan**: Xây golden reference dataset cho 10-20 câu hỏi quan trọng (multi-hop, supply-chain, hallucination-prone) để có ground truth cho LLM-judge.

## So sánh với production-grade evaluation

| Thành phần | Đã có | Chưa có |
|---|---|---|
| Deterministic grading (lexical) | ✅ | |
| Structured concept coverage (AND-logic) | ✅ | |
| Provider-error filter | ✅ | |
| Retrieval accuracy metric | ✅ | |
| Answer correctness metric | ✅ (lexical) | Semantic correctness (LLM-judge) |
| Hallucination detection | ✅ (heuristic) | LLM-based hallucination detection |
| Latency metrics (avg, p95) | ✅ | |
| Intent routing accuracy (agent) | ✅ | |
| Source citation rate (agent) | ✅ | |
| Confusion matrix | ✅ (agent) | |
| Golden reference answer | | ❌ |
| LLM-judge supplement | | ❌ |
| CI evaluation (live) | | ❌ (chỉ validate-only) |
| Golden reference dataset | | ❌ |
| Per-question evaluation detail | ✅ | |

## Kế hoạch

1. **Ngắn hạn (sẵn sàng phỏng vấn)**: Giữ deterministic evaluation hiện tại, nhấn mạnh tính tái lặp (repeatable), không phụ thuộc LLM cost. Nêu rõ limit: "chỉ đo lexical coverage, không semantic correctness — metric underestimate nếu answer dùng từ khác nhưng đúng".

2. **Trung hạn (Q3 roadmap)**: 
   - Xây golden reference dataset cho subset câu hỏi quan trọng.
   - Thử nghiệm LLM-judge supplement: grading LLM đo semantic alignment, flag hallucination từ source-grounded perspective.
   - Thêm CI job `eval-live` chạy evaluation trên staging khi có cloud secrets.

3. **Long-term**: Evaluation drift monitoring — track retrieval_accuracy, answer_correctness, hallucination_rate theo thời gian khi document corpus / LLM model / retrieval strategy thay đổi. Alert khi metric giảm đáng kể.

## Gợi ý trả lời phỏng vấn

**Q: "Evaluation pipeline của bạn đo cái gì?"**
A: "2 track: classic RAG evaluation đo retrieval_accuracy, answer_correctness (lexical concept coverage AND-logic), hallucination heuristic rate, latency (avg/p95); agent evaluation thêm intent routing accuracy, source citation rate, confusion matrix. Deterministic, không LLM-judge — repeatable, không cost."

**Q: "S strengths/limitations của evaluation hiện tại?"**
A: "Strong: deterministic, không phụ thuộc LLM cost, có concept coverage AND-logic ngăn false-positive, provider-error filter giữ eval fair. Limit: không có golden reference semantic answer, không LLM-judge supplement, chỉ đo lexical coverage — có thể underestimate chất lượng nếu answer dùng từ khác. Plan Q3: golden reference dataset + LLM-judge supplement."

**Q: "Evaluation có chạy trong CI không?"**
A: "Chưa có CI job chạy evaluation thực tế (cần backend live + JWT + document). Có CI job `eval-questions-validate` chạy `--validate-only` mode kiểm tra cấu trúc question set — evaluation-as-code cơ bản. Plan: thêm eval-live job khi có cloud secrets."

---

*Đây là document trung thực. Nếu nhà tuyển dụng hỏi sâu, trả lời theo nội dung này — không phóng đại.*
