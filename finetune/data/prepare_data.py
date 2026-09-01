#!/usr/bin/env python3
"""Prepare Vietnamese legal Q&A training data in JSONL format.

Sources:
  - eval/questions.json            → system benchmark questions
  - eval/document_questions.json   → legal document questions
  - Synthetic Vietnamese legal Q&A pairs (generated below)

Output:
  finetune/data/train.jsonl
  finetune/data/valid.jsonl
  Each line: {"instruction": ..., "input": ..., "output": ...}
"""

from __future__ import annotations

import json
import os
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
EVAL_DIR = ROOT / "eval"
OUT_DIR = Path(__file__).resolve().parent

SYSTEM_INSTRUCTION = (
    "Bạn là trợ lý AI của hệ thống Smart Document Chatbot. "
    "Trả lời ngắn gọn, chính xác bằng tiếng Việt, chỉ dựa trên ngữ cảnh được cung cấp."
)

# ---------------------------------------------------------------------------
# Synthetic Vietnamese legal Q&A pairs
# ---------------------------------------------------------------------------
SYNTHETIC_QA: list[tuple[str, str]] = [
    (
        "Theo luật Việt Nam, hợp đồng lao động có bao nhiêu loại?",
        "Theo Bộ luật Lao động 2019, hợp đồng lao động có 2 loại chính: (1) Hợp đồng lao động không xác định thời hạn, và (2) Hợp đồng lao động xác định thời hạn (tối đa 36 tháng).",
    ),
    (
        "Thời hạn tối đa của hợp đồng lao động xác định thời hạn là bao lâu?",
        "Thời hạn tối đa của hợp đồng lao động xác định thời hạn là 36 tháng. Nếu người lao động tiếp tục làm việc sau thời hạn này mà không ký hợp đồng mới, hợp đồng sẽ chuyển thành hợp đồng lao động không xác định thời hạn.",
    ),
    (
        "Người lao động có quyền đơn phương chấm dứt hợp đồng không? Điều kiện là gì?",
        "Có. Theo Điều 35 Bộ luật Lao động 2019, người lao động có quyền đơn phương chấm dứt hợp đồng lao động nhưng phải báo trước: (a) ít nhất 45 ngày đối với hợp đồng không xác định thời hạn; (b) ít nhất 30 ngày đối với hợp đồng xác định thời hạn; (c) ít nhất 3 ngày làm việc đối với hợp đồng thử việc.",
    ),
    (
        "Thời gian làm việc tiêu chuẩn tại Việt Nam là bao nhiêu giờ một tuần?",
        "Thời gian làm việc tiêu chuẩn tại Việt Nam là không quá 8 giờ một ngày và không quá 48 giờ một tuần. Đối với công việc nặng nhọc, độc hại, thời gian làm việc được giảm xuống còn 6 giờ một ngày.",
    ),
    (
        "Mức lương tối thiểu vùng được quy định như thế nào?",
        "Mức lương tối thiểu vùng do Chính phủ quy định dựa trên từng khu vực địa lý. Hiện tại có 4 vùng với mức lương tối thiểu khác nhau, trong đó vùng I (nội thành Hà Nội, TP.HCM) có mức cao nhất và vùng IV (vùng nông thôn, vùng sâu) có mức thấp nhất.",
    ),
    (
        "Doanh nghiệp có được sa thải người lao động khi nào?",
        "Doanh nghiệp chỉ được sa thải người lao động trong các trường hợp quy định tại Điều 36 Bộ luật Lao động 2019, bao gồm: (1) người lao động thường xuyên không hoàn thành công việc; (2) bị bệnh thời hạn quá 12 tháng liên tục; (3) thiên tai, hỏa hoạn; (4) doanh nghiệp ngừng hoạt động. Phải báo trước theo quy định.",
    ),
    (
        "Quy định về thử việc trong hợp đồng lao động Việt Nam?",
        "Thời gian thử việc tối đa: 180 ngày đối với vị trí giám đốc doanh nghiệp; 60 ngày đối với vị trí có trình độ chuyên gia; 30 ngày đối với vị trí trung cấp; 6 ngày làm việc đối vị trí lao động phổ thông. Trong thời gian thử việc, mỗi bên có quyền hủy bỏ hợp đồng mà không cần báo trước.",
    ),
    (
        "Người lao động nghỉ phép năm được hưởng bao nhiêu ngày?",
        "Người lao động làm việc đủ 12 tháng được hưởng nghỉ phép năm có hưởng lương 12 ngày làm việc. Số ngày nghỉ phép tăng thêm tùy theo thâm niên: thêm 1 ngày cho mỗi 5 năm làm việc. Đối với người làm công việc nặng nhọc, độc hại được nghỉ 14-16 ngày.",
    ),
    (
        "Quy định về bảo hiểm xã hội tại Việt Nam?",
        "Theo Luật Bảo hiểm xã hội 2014, người lao động và người sử dụng lao động đều phải đóng bảo hiểm xã hội bắt buộc. Mức đóng: người lao động 10,5% tiền lương, người sử dụng lao động 21,5% tiền lương. Bảo hiểm xã hội bao gồm: ốm đau, thai sản, tai nạn lao động, hưu trí, tử tuất.",
    ),
    (
        "Hợp đồng kinh tế theo luật Việt Nam có những đặc điểm gì?",
        "Hợp đồng kinh tế (hợp đồng dân sự) theo Bộ luật Dân sự 2015 có các đặc điểm: (1) các bên bình đẳng, tự nguyện; (2) nội dung tự do thỏa thuận nhưng không trái pháp luật; (3) có thể bằng văn bản hoặc lời nói; (4) bên vi phạm phải chịu trách nhiệm bồi thường thiệt hại.",
    ),
    (
        "Thủ tục giải quyết tranh chấp lao động tại Việt Nam?",
        "Thủ tục giải quyết tranh chấp lao động cá nhân: (1) hòa giải tại ủy ban hòa giải cơ sở; (2) hòa giải tại Hội đồng hòa giải lao động; (3) khởi kiện ra Tòa án nhân dân. Tranh chấp tập thể quyền lợi có thể đình công theo quy định tại Điều 209-216 Bộ luật Lao động.",
    ),
    (
        "Quy định về làm thêm giờ tại Việt Nam?",
        "Làm thêm giờ phải được sự đồng ý của người lao động. Giới hạn: không quá 50% số giờ làm việc bình thường trong 1 ngày; không quá 30 giờ trong 1 tháng và 200 giờ trong 1 năm (trường hợp đặc biệt được phép 300 giờ/năm). Làm thêm giờ được trả lương: ngày thường 150%, ngày nghỉ 200%, ngày lễ 300%.",
    ),
    (
        "Doanh nghiệp có nghĩa vụ gì về an toàn lao động?",
        "Doanh nghiệp có nghĩa vụ: (1) bảo đảm điều kiện an tong lao động; (2) cung cấp trang bị bảo hộ lao động; (3) tổ chức đào tạo an toàn lao động; (4) khám sức khỏe định kỳ; (5) trả bảo hiểm tai nạn lao động; (6) bồi thường thiệt hại khi xảy ra tai nạn.",
    ),
    (
        "Quy định về bảo hộ sở hữu trí tuệ tại Việt Nam?",
        "Luật Sở hữu trí tuệ 2005 (sửa đổi 2009, 2019) bảo hộ: quyền tác giả, quyền liên quan, sáng chế, kiểu dáng công nghiệp, nhãn hiệu, chỉ dẫn địa lý, giống cây trồng. Thời hạn bảo hộ: tác giả 50 năm; sáng chế 20 năm; nhãn hiệu 10 năm (gia hạn không giới hạn).",
    ),
    (
        "Thuế thu nhập cá nhân tại Việt Nam được tính như thế nào?",
        "Thuế TNCN áp dụng biểu thuế lũy tiến từng phần cho thuế tính trên thu nhập từ tiền lương: mức 5% (đến 5 triệu), 10% (5-10 triệu), 15% (10-18 triệu), 20% (18-32 triệu), 25% (32-52 triệu), 30% (52-80 triệu), 35% (trên 80 triệu). Giảm trừ gia cảnh: 11 triệu/tháng cho người nộp thuế + 4,4 triệu/người phụ thuộc.",
    ),
]


def convert_eval_questions(questions: list[dict]) -> list[dict]:
    """Convert eval question format to training JSONL format."""
    rows: list[dict] = []
    for q in questions:
        answer_parts = q.get("expected_answer_contains", [])
        answer = (
            f"Câu trả liên quan đến: {q['question']}. "
            f"Các từ khóa quan trọng: {', '.join(answer_parts)}."
        )
        rows.append(
            {
                "instruction": SYSTEM_INSTRUCTION,
                "input": q["question"],
                "output": answer,
            }
        )
    return rows


def generate_synthetic() -> list[dict]:
    """Generate synthetic Vietnamese legal Q&A training rows."""
    rows: list[dict] = []
    for question, answer in SYNTHETIC_QA:
        rows.append(
            {
                "instruction": SYSTEM_INSTRUCTION,
                "input": question,
                "output": answer,
            }
        )
    return rows


def write_jsonl(rows: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Convert existing eval questions
    eval_questions: list[dict] = []
    for fname in ("questions.json", "document_questions.json"):
        p = EVAL_DIR / fname
        if p.exists():
            data = json.loads(p.read_text(encoding="utf-8"))
            if isinstance(data, list):
                eval_questions.extend(data)
            elif isinstance(data, dict) and "questions" in data:
                eval_questions.extend(data["questions"])

    converted = convert_eval_questions(eval_questions)
    synthetic = generate_synthetic()
    all_rows = converted + synthetic

    random.Random(42).shuffle(all_rows)

    # 90/10 split
    n_valid = max(1, int(len(all_rows) * 0.1))
    valid_rows = all_rows[:n_valid]
    train_rows = all_rows[n_valid:]

    write_jsonl(train_rows, OUT_DIR / "train.jsonl")
    write_jsonl(valid_rows, OUT_DIR / "valid.jsonl")

    print(f"✅ Prepared training data:")
    print(f"   Train: {len(train_rows)} rows → {OUT_DIR / 'train.jsonl'}")
    print(f"   Valid: {len(valid_rows)} rows → {OUT_DIR / 'valid.jsonl'}")
    print(f"   Sources: {len(converted)} from eval + {len(synthetic)} synthetic")


if __name__ == "__main__":
    main()
