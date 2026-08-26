# Sửa Retrieval Tiếng Việt (no_evidence 31/31) — Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.
> Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Khắc phục tình trạng `no_evidence` 31/31 câu tiếng Việt trên staging (retrieval accuracy 0%), đưa retrieval accuracy ≥ 70% và hallucination ≤ 10% theo gate.

**Architecture:** Eval gọi thẳng Java backend trên Render (`/api`) → `ChatService` (CRAG loop) → `RetrievalService` (lexical scoring trên PostgreSQL chunks). Đường Python/Qdrant (`agent/tools/qdrant_tool.py`) là luồng agent-service, KHÔNG phải đường eval đang đo. Root cause nằm ở lớp lexical matching tiếng Việt phía Java + chất lượng embedding tiếng Anh (`bge-base-en-v1.5`) nếu dùng đường vector.

**Tech Stack:** Spring Boot 3.2, PostgreSQL, Qdrant, Cloudflare Workers AI (llm-router), pytest/mvn, eval harness tại `eval/eval.py`.

**Spec:** `SMART_DOCUMENT_CHATBOT_NAB_READY_BLUEPRINT.md` (mục #35 Retrieval Optimization: *"Do not change all parameters simultaneously. Benchmark each meaningful change."*) + kết quả eval `eval/results/full_eval.json` (14:19) và run 17:22.

---

## KẾT QUẢ KIỂM TRA TOÀN BỘ (verified facts)

| # | Phát hiện | Bằng chứng |
|---|---|---|
| 1 | Eval đo đường **Java Postgres**, không phải Python/Qdrant | `full_eval.json.base_url = smart-doc-backend-h4mt.onrender.com/api`; `ChatService.java:230-231` gọi `retrievalService.retrieve(...)` |
| 2 | `RetrievalService` là **pure lexical** (word coverage + frequency), bỏ term <3 ký tự | `RetrievalService.java:66-68` (`terms.removeIf(t -> t.length() < 3)`) |
| 3 | Đã có sẵn `LegalQueryNormalizer`: diacritic-folding + abbreviation expansion + article-ref extraction | javadoc `RetrievalService.java:52-64` |
| 4 | Fixture 3 câu **tiếng Anh** đạt 100%/100% → pipeline sống, lỗi riêng tiếng Việt | Report eval 17:22 + 14:19 |
| 5 | Embedding model là **bge-base-en-v1.5 — model TIẾNG ANH** cho corpus tiếng Việt | `agent/settings.py:66`, `llm-router/app/config.py:30`, `render.yaml:61-62` |
| 6 | BM25 tokeniser Python chỉ `text.lower().split()` — không xử lý dấu/tiếng Việt | `qdrant_tool.py:63-65` |
| 7 | Regression 17:22 (0%) vs 14:19 (9.68%): cùng 31 câu, cùng doc → nghi ngờ trạng thái doc/cache/redeploy, không phải code đổi (git sạch, HEAD 67ff5de) | git status sạch; commit `ci: tolerate Render redeploy races` |
| 8 | Có test unit sẵn cho retrieval | `backend/src/test/java/com/smartdocchat/service/RetrievalServiceTest.java`, `RetrievalServiceLegalTest.java` |
| 9 | Eval CLI: cần `--token`, `--document-id`; questions.json có **31 câu** tiếng Việt, không ghim document-id | `eval.py:524-563`, `questions.json` |
| 10 | Full eval gần nhất chạy trên **document_id=69** | `full_eval.json.summary.document_id = 69` |

**Khoảng trống chưa verify được offline (sẽ xử lý ở Phase A):**
- Trạng thái chunks của doc #69/#93 trên staging Postgres (rỗng? sai encoding?)
- Response thực tế của `/api/chat` cho câu tiếng Việt (strategy, sources, confidence)

---

## Global Constraints

- Gate mục tiêu: **retrieval accuracy ≥ 70%, answer correctness ≥ 60%, hallucination ≤ 10%** trên 31 câu tiếng Việt.
- Không đổi >1 tham số retrieval cùng lúc (Blueprint #35); mỗi thay đổi phải benchmark riêng.
- Không được claim capability không có evidence trong repo (nguyên tắc Blueprint).
- Staging URL: `https://smart-doc-backend-h4mt.onrender.com/api`. JWT cần quyền owner của document eval.
- Mọi thay đổi Java phải pass: `cd backend && mvn test` (~50s).
- Không commit trực tiếp lên main mà không chạy test; giữ convention commit hiện tại (`fix(...)`, `feat(...)` scopes).

---

## Phase A — Chẩn đoán trên staging (chỉ đọc, ~15 phút)

### Task A1: Lấy JWT + xác nhận trạng thái document

- [ ] Đăng nhập lấy token (user cung cấp credential, KHÔNG hardcode):
```bash
TOKEN=$(curl -s -X POST https://smart-doc-backend-h4mt.onrender.com/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"<user>","password":"<pass>"}' | python3 -c 'import sys,json;print(json.load(sys.stdin)["token"])')
echo $TOKEN | wc -c   # kỳ vọng > 100 ký tự
```
- [ ] Liệt kê documents, xác nhận doc #69 (eval cũ) và #93 còn tồn tại, trạng thái READY:
```bash
curl -s https://smart-doc-backend-h4mt.onrender.com/api/documents \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool | head -50
```
Expected: thấy id 69/93 với status READY. Nếu #93 FAILED/empty → vấn đề là indexing, dừng sửa retrieval, đi thẳng Task C2.

### Task A2: Probe 1 câu tiếng Việt qua /api/chat, đọc raw response

- [ ] Gửi đúng 1 câu từ `eval/questions.json` (id=1: "Hệ thống sử dụng framework backend nào?"):
```bash
curl -s -X POST https://smart-doc-backend-h4mt.onrender.com/api/chat \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"documentId":69,"message":"Hệ thống sử dụng framework backend nào?"}' \
  | python3 -m json.tool
```
Ghi lại: `rag_strategy`, `sources`, `confidence`, nội dung answer.
- [ ] So sánh với 1 câu tiếng Anh tương đương ("Which backend framework does the system use?").
- [ ] **Kết luận phân nhánh:**
  - Nếu TV trả `no_evidence` nhưng EN có evidence → lỗi lexical matching TV → **Phase B**.
  - Nếu cả hai đều `no_evidence` → chunks rỗng/hỏng trong DB → **Task C2 (re-index) trước**, Phase B sau.
  - Nếu 17:22 khác 14:19 trên cùng input → điều tra Redis cache/redeploy race → Task A3.

### Task A3 (điều kiện): Loại trừ nguyên nhân regression 17:22

- [ ] Chạy lại probe A2 3 lần cách nhau 60s (Render free tier cold-start); ghi latency + strategy từng lần.
- [ ] Nếu lần nào cũng `no_evidence` → ổn định, đi Phase B. Nếu lơ thơ → check log Render deploy quanh 17:22.

---

## Phase B — Sửa lexical retrieval tiếng Việt trong Java (P0, TDD)

### Task B1: Viết test tái hiện lỗi (RED)

**Files:**
- Modify: `backend/src/test/java/com/smartdocchat/service/RetrievalServiceTest.java`

- [ ] Thêm test dùng đúng câu hỏi thật + đoạn text tiếng Việt chứa đáp án:
```java
@Test
void retrievesVietnameseChunkForVietnameseQuestion() {
    // Chunk mô phỏng nội dung doc thật
    when(documentService.getDocumentChunks(DOC_ID, OWNER))
        .thenReturn(List.of(
            "Hệ thống sử dụng Spring Boot 3.2 làm framework backend chính, "
          + "kết hợp FastAPI cho dịch vụ agent.",
            "Vector database Qdrant lưu trữ embeddings của tài liệu."));
    when(documentService.getDocumentById(DOC_ID, OWNER))
        .thenReturn(new Document()); // theo pattern test hiện có

    List<RetrievalService.RetrievalResult> results =
        service.retrieve(OWNER, DOC_ID, "Hệ thống sử dụng framework backend nào?", 5);

    assertFalse(results.isEmpty(), "Phải tìm được chunk chứa đáp án");
    assertTrue(results.get(0).chunk().contains("Spring Boot"));
}
```
- [ ] Chạy: `cd backend && mvn test -Dtest=RetrievalServiceTest#retrievesVietnameseChunkForVietnameseQuestion`
Expected: **FAIL** (tái hiện đúng triệu chứng staging). Nếu PASS → triệu chứng chỉ xuất hiện với data thật, chuyển trọng tâm sang Task C2.

### Task B2: Sửa matching tiếng Việt trong `LegalQueryNormalizer` + scoring (GREEN)

**Files:**
- Modify: `backend/src/main/java/com/smartdocchat/util/LegalQueryNormalizer.java`
- Modify: `backend/src/main/java/com/smartdocchat/service/RetrievalService.java`

Thứ tự can thiệp (mỗi bước một commit, benchmark riêng theo Blueprint #35):

- [ ] **B2a — Diacritic folding áp cho cả HAI phía:** đảm bảo fold bỏ dấu ở query VÀ chunk content trước khi match (hiện chỉ rõ ràng ở query side). Sketch:
```java
private static String foldDiacritics(String s) {
    String n = java.text.Normalizer.normalize(s, java.text.Normalizer.Form.NFD);
    return n.replaceAll("\\p{M}+", "").replace('đ', 'd').replace('Đ', 'D');
}
```
Match trên bản folded của cả query-term và chunk-token.
- [ ] **B2b — Bigram tiếng Việt:** tiếng Việt là từ ghép nhiều âm tiết ("hệ thống", "framework backend"). Sau khi tách token, tạo thêm bigram từ cặp token liền kề và đưa vào tập terms với trọng số bằng token đơn. Không thêm infra mới — thuần logic trong normalizer.
- [ ] **B2c — Nới ngưỡng <3 ký tự một cách có điều kiện:** giữ removeIf(<3) cho term đơn lẻ mơ hồ, nhưng KHÔNG loại bigram/term nằm trong `expected_source_keywords` kiểu "ăn"/"bò" khi đi cùng context. Chỉ nới khi benchmark cho thấy không tăng false-positive.
- [ ] Chạy toàn bộ suite sau MỖI bước con:
```bash
cd backend && mvn test
```
Expected: test mới PASS + toàn bộ test cũ vẫn xanh (~50s). Đặc biệt chú ý `RetrievalServiceLegalTest` không bị hồi quy.
- [ ] Commit từng bước con:
```bash
git add backend/src/main/java/com/smartdocchat/util/LegalQueryNormalizer.java backend/src/test/java/com/smartdocchat/service/RetrievalServiceTest.java
git commit -m "fix(retrieval): diacritic-fold both query and chunk sides for Vietnamese matching"
```

### Task B3: Deploy staging + smoke test

- [ ] Push branch, mở PR, merge khi CI xanh (repo đã có CI + SonarCloud):
```bash
git checkout -b fix/vietnamese-lexical-retrieval
# ... các commit B1-B2 ...
git push -u origin fix/vietnamese-lexical-retrieval
```
- [ ] Chờ Render auto-deploy xong (theo dõi dashboard), rồi chạy lại probe A2 (1 câu TV).
Expected: `rag_strategy != no_evidence`, sources không rỗng.

---

## Phase C — Benchmark + gate (P0)

### Task C1: Full eval 31 câu sau khi vá lexical

- [ ] Chạy đúng tham số như lần baseline để so sánh công bằng:
```bash
cd ~/Downloads/Smart-Document-Chatbot && source .venv/bin/activate 2>/dev/null || true
python eval/eval.py \
  --base-url https://smart-doc-backend-h4mt.onrender.com/api \
  --token "$TOKEN" --document-id 69 \
  --questions eval/questions.json \
  --output eval/results/full_eval_$(date +%Y-%m-%d_%H%M)_post_lexical_fix.json
```
- [ ] **Gate:** retrieval ≥ 70%? 
  - Đạt → sang Phase D.
  - Chưa đạt nhưng tăng đáng kể (>30%) → tiếp **Task C3** (embedding đa ngôn ngữ).
  - Vẫn ~0% → quay lại Task A2, dữ liệu doc có vấn đề → **Task C2**.

### Task C2 (điều kiện): Re-index document trên staging

- [ ] Xoá + upload lại doc #69/#93 qua API (endpoint upload trong `DocumentController`), xác nhận chunk_count > 0.
- [ ] Nếu dùng đường agent/connector: kiểm tra `agent/ingestion/pipeline.py` logs — `_normalize_text` hiện chỉ chuẩn hoá whitespace, không đụng encoding.
- [ ] Chạy lại Task C1.

### Task C3 (điều kiện): Embedding đa ngôn ngữ `@cf/baai/bge-m3`

Chỉ làm nếu C1 chưa đạt gate. Đây là thay đổi hạ tầng lớn — cần reindex toàn bộ.

**Files:**
- Modify: `llm-router/app/config.py:30` → `CLOUDFLARE_EMBED_MODEL` default `@cf/baai/bge-m3`
- Modify: `agent/settings.py:66` → `llm_embedding_model` default `@cf/baai/bge-m3`
- Modify: `render.yaml:61-62` → giá trị env staging
- Modify: `agent/tools/qdrant_tool.py:63-65` → tokeniser BM25 có tách dấu:
```python
def _tokenize(text: str) -> List[str]:
    import unicodedata
    nfd = unicodedata.normalize("NFD", text.lower())
    folded = "".join(c for c in nfd if not unicodedata.combining(c)).replace("đ", "d")
    return folded.split()
```

- [ ] Lưu ý kỹ thuật bắt buộc: bge-m3 ra vector **1024 dims** (bge-base-en là 768) → collection Qdrant cũ **không tương thích**. Phải: tạo collection mới (pipeline tự `_create_collection` theo `len(embeddings[0])` — `pipeline.py:90,194`) → re-index toàn bộ document → huỷ Redis RAG cache (`FLUSHALL` hoặc đổi prefix key `rag_cache:` → `rag_cache_v2:` trong `qdrant_tool.py:60`).
- [ ] Test llm-router: `cd llm-router && pytest tests/ -q` — thêm test khẳng định response embeddings length == 1024 với mock.
- [ ] Deploy llm-router + agent trước, re-index, rồi mới chạy lại Task C1.
- [ ] Commit: `feat(llm-router): switch to bge-m3 multilingual embeddings (+1024-dim reindex)`.

### Task C4: Chốt benchmark cuối

- [ ] Chạy C1 lần cuối, lưu kết quả vào `eval/results/`.
- [ ] Cập nhật bảng so sánh before/after (14:19 baseline → sau fix) vào `docs/EVALUATION.md`.

---

## Phase D — Blueprint NAB-ready tiếp theo (P1)

### Task D1: Unanswerable handling
- [ ] Khi CRAG confidence thấp + web search không có → trả lời cấu trúc "không tìm thấy trong tài liệu" kèm lý do, thay vì để LLM tự do. File: `backend/.../service/ChatService.java` (nhánh `"no_evidence".equals(crag.strategy())` dòng 76-82, 128).
- [ ] Thêm eval case unanswerable vào `eval/questions.json` (3-5 câu ngoài tài liệu, kỳ vọng strategy=no_evidence và KHÔNG bị tính hallucination).

### Task D2: Citation quality
- [ ] Đảm bảo mỗi answer gắn citation (article/clause/point từ `RetrievalResult` metadata đã có sẵn) — kiểm tra response DTO của `/api/chat` có field citations; thiếu thì bổ sung map từ `RetrievalResult.chunkId/article/clause/point`.

### Task D3: Prompt-injection defense
- [ ] Sanitise chunk text trước khi đưa vào prompt (strip các mẫu "ignore previous instructions"), test unit tương ứng. Vị trí: lớp mới `backend/.../util/PromptSanitizer.java` + wire vào ChatService.

---

## Risks & Tradeoffs

| Risk | Impact | Giảm thiểu |
|---|---|---|
| bge-m3 reindex phá collection production | Downtime retrieval | Tạo collection MỚI song song, cut-over khi index xong |
| Nới ngưỡng <3 ký tự gây false-positive | Hallucination tăng | Benchmark riêng B2c, rollback nếu FP tăng |
| Render free tier cold-start nhiễu eval | Latency/strategy chập chờn | Warm-up 1 request trước mỗi run eval |
| Đổi 2 thứ cùng lúc (lexical + embedding) | Không biết cái nào hiệu quả | Trình tự B → C1 benchmark → C3 chỉ khi cần |
| Doc #93 chưa index đúng | Eval đo nhầm | Task A1 verify trước mọi thay đổi |

## Open Questions (cần user trước khi chạy)

1. **Credential staging** (username/password có quyền owner doc #69/#93) — để lấy JWT chạy Task A1/C1.
2. Nếu C1 chưa đạt gate sau fix lexical: có đồng ý nâng cấp **bge-m3 + reindex toàn bộ** ngay (Task C3), hay chấp nhận dừng ở mức lexical?
3. Phase D làm ngay sau gate hay để batch sau?

## Verification tổng thể cuối cùng

- [ ] `cd backend && mvn test` xanh toàn bộ
- [ ] `pytest eval/ -q` (validate-only) xanh
- [ ] Full eval 31 câu: retrieval ≥ 70%, correctness ≥ 60%, hallucination ≤ 10%
- [ ] Kết quả được ghi trong `docs/EVALUATION.md` + file JSON trong `eval/results/`
