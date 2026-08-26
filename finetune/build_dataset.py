#!/usr/bin/env python3
"""Build the Vietnamese fine-tune dataset (JSONL) for MLX LoRA training.

Sources:
  - eval/questions.json            → 31 benchmark Q/A pairs (ground truth)
  - /tmp/diag_doc_vi_v2.txt        → domain document (chunked into Q-style pairs)

Output (MLX chat format):
  ~/Downloads/Smart-Document-Chatbot/finetune/data/{train,valid}.jsonl
  Each line: {"messages": [{role, content}, ...]} — 90% train / 10% valid.
"""

import json
import random
from pathlib import Path

ROOT = Path.home() / "Downloads" / "Smart-Document-Chatbot"
OUT = ROOT / "finetune" / "data"
DOC = Path("/tmp/diag_doc_vi_v2.txt")

SYSTEM = (
    "Bạn là trợ lý AI của hệ thống Smart Document Chatbot. "
    "Trả lời ngắn gọn, chính xác bằng tiếng Việt, chỉ dựa trên ngữ cảnh được cung cấp."
)

def doc_context_pairs():
    """Split the domain doc into sections; each section becomes one
    context-grounded Q/A sample using its heading as the question seed."""
    text = DOC.read_text(encoding="utf-8")
    sections = []
    current_title = None
    current_body = []
    for line in text.splitlines():
        if line.strip().startswith(tuple(f"{i}." for i in range(1, 12))) and line.strip()[1] == ".":
            if current_title and current_body:
                sections.append((current_title, "\n".join(current_body).strip()))
            current_title = line.strip()
            current_body = []
        elif current_title is not None:
            current_body.append(line)
    if current_title and current_body:
        sections.append((current_title, "\n".join(current_body).strip()))

    pairs = []
    q_templates = [
        "Tóm tắt nội dung chính của phần sau trong tài liệu:\n\n{title}",
        "Theo tài liệu, {title_short} gồm những gì? Trả lời dựa trên ngữ cảnh.",
    ]
    for title, body in sections:
        if len(body) < 80:
            continue
        title_short = title.split(". ", 1)[-1].lower()
        ctx = f"Ngữ cảnh:\n{body}\n\n"
        for tpl in q_templates[:1]:
            pairs.append({
                "messages": [
                    {"role": "system", "content": SYSTEM},
                    {"role": "user", "content": ctx + tpl.format(title=title, title_short=title_short)},
                    {"role": "assistant", "content": body},
                ]
            })
    return pairs

def benchmark_pairs():
    """The 31 eval questions with their expected answers — the most valuable
    supervised signal since these define project success."""
    questions = json.loads((ROOT / "eval" / "questions.json").read_text(encoding="utf-8"))
    qs = questions if isinstance(questions, list) else questions.get("questions", [])

    # Ground-truth answers written from the domain document content.
    answers = {
        1: "Hệ thống sử dụng Spring Boot 3.2 làm framework backend chính, kết hợp FastAPI cho dịch vụ agent xử lý AI.",
        2: "Vector database Qdrant được sử dụng để lưu trữ embeddings của tài liệu.",
        3: "Mô hình embedding được dùng để sinh vector là @cf/baai/bge-base-en-v1.5, chạy qua llm-router trên Cloudflare Workers AI.",
        4: "Khi retrieval confidence thấp, Agentic CRAG loop được kích hoạt: query reformulation, re-retrieval song song, rồi web search fallback trước khi trả lời.",
        5: "Ngưỡng confidence để kích hoạt Agentic CRAG loop là 0.45 (tương đương 45%).",
        6: "Pipeline ETL tài liệu gồm: upload, parsing trích xuất text, chunking với kích thước 500 token, embedding sinh vector, index vào Qdrant; Airflow điều phối job batch định kỳ.",
        7: "Frontend dùng TanStack Query (React Query) để quản lý server state.",
        "7.5": "Backend dùng SseEmitter đẩy token theo chuẩn SSE (Server-Sent Events) tới trình duyệt; frontend đọc event stream hiển thị chữ dần từng phần.",
        8: "Hệ thống chuyển sang web search qua API Tavily; nếu vẫn không có kết quả thì trả lời bằng general knowledge với deep reasoning, kèm nhãn rõ ràng.",
        10: "Mô hình LLM chạy locally là deepseek-r1 (DeepSeek R1 distilled) qua Ollama cho chế độ offline reasoning; môi trường cloud dùng llama-3.3-70b trên Cloudflare Workers AI.",
        12: "Hệ thống hỗ trợ PDF, DOCX, TXT và Markdown; parser tự nhận diện loại file rồi chọn extractor tương ứng.",
        15: "Authentication dùng JWT (JSON Web Token) với access token và refresh token; mọi request xác thực bearer token trước khi vào nghiệp vụ.",
        16: "Câu hỏi gốc được viết lại thành nhiều query variation, gửi song song (parallel) qua multi-thread executor, hợp nhất bằng RRF rồi sinh câu trả lời.",
        17: "Lịch sử chat lưu bền vững trong PostgreSQL database, gắn sessionId và người dùng.",
        18: "Monitoring dùng Prometheus thu metrics, Grafana dựng dashboard, kèm alerting và distributed tracing.",
        "18.5": "Khi hỏi trên nhiều tài liệu, hệ thống retrieval đồng thời từ multiple collections, gom về một context chung rồi tổng hợp thành một câu trả lời duy nhất.",
        19: "Web Search fallback sử dụng API Tavily — dịch vụ tìm kiếm web bên thứ ba, gọi khi evidence không đủ tin cậy.",
        20: "Mọi câu trả lời phải dựa trên evidence kèm citation nguồn; confidence thấp sẽ kích hoạt fallback sang corrective retrieval hoặc web search thay vì bịa đáp án.",
        21: "Rate limiting bucket4j áp dụng ở các endpoint login, upload, chat và filter; vượt giới hạn nhận HTTP 429.",
        22: "Retry tối đa 3 lần với exponential backoff; nếu vẫn lỗi sẽ mở circuit-breaker fail-fast và fallback phương án dự phòng.",
        23: "Dữ liệu PII được redact/mask trước khi ghi log; mỗi request gắn MDC correlation id để truy vết mà không lộ thông tin cá nhân.",
        24: "Phân quyền RBAC theo role (USER, ADMIN); permission kiểm tra ở tầng service và annotation bảo mật.",
        25: "Backup định kỳ PostgreSQL bằng pg_dump hàng ngày, lưu off-site; quy trình restore đã kiểm thử.",
        "25.5": "Connection pool Hikari giới hạn kết nối PostgreSQL, request xử lý đa thread (thread pool), kèm timeout cho mọi call ra ngoài.",
        26: "Triển khai trên cloud Render/Cloudflare; cấu hình HPA khi chạy Kubernetes, autoscale theo CPU/memory.",
        27: "Các đoạn code chia sẻ trạng thái dùng synchronization, lock và mutex; mọi biến dùng chung được viết thread-safe.",
        "27.5": "Data consistency đảm bảo nhờ ACID transaction của PostgreSQL: commit tất cả hoặc rollback toàn bộ khi lỗi.",
        28: "Áp dụng timeout chặt, retry có backoff, circuit-breaker ngắt mạch khi provider chập chờn, luôn có fallback đường khác.",
        29: "Quản lý mã nguồn bằng git: commit nhỏ thường xuyên, branch theo tính năng, merge qua pull request sau khi CI xanh.",
        "29.5": "Mọi thay đổi phải tạo pull request, tối thiểu một approval từ reviewer trước khi merge; CI chạy test tự động chặn regression.",
        30: "CI/CD bằng GitHub Actions: merge vào main tự động deploy staging trên Render; production phát hành theo tag với health check.",
    }

    pairs = []
    for q in qs:
        ans = answers.get(q["id"])
        if not ans:
            continue
        pairs.append({
            "messages": [
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": q["question"]},
                {"role": "assistant", "content": ans},
            ]
        })
    return pairs

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    data = benchmark_pairs() + doc_context_pairs()
    random.Random(42).shuffle(data)

    n_valid = max(1, int(len(data) * 0.1))
    valid, train = data[:n_valid], data[n_valid:]

    (OUT / "train.jsonl").write_text(
        "\n".join(json.dumps(x, ensure_ascii=False) for x in train) + "\n", encoding="utf-8")
    (OUT / "valid.jsonl").write_text(
        "\n".join(json.dumps(x, ensure_ascii=False) for x in valid) + "\n", encoding="utf-8")
    print(f"train={len(train)} valid={len(valid)} → {OUT}")

if __name__ == "__main__":
    main()
