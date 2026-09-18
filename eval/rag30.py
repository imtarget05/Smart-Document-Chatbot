# -*- coding: utf-8 -*-
# Data builder for rag_30_questions.json — 30 câu: 15 answered / 10 unanswerable / 5 conflict
# Dump ra JSON bằng: python3 eval/rag30.py

import json

QA = [
    # ===== 15 ANSWERED =====
    {
        "id": "A1",
        "question": "Luật Doanh nghiệp 2020 áp dụng từ ngày nào?",
        "expected_source_keywords": ["01/01/2021", "áp dụng"],
        "expected_section": "Điều 1.2",
        "expected_answer_hint": "Từ ngày 01/01/2021.",
        "type": "answered",
    },
    {
        "id": "A2",
        "question": "Theo văn bản này, doanh nghiệp được định nghĩa là gì?",
        "expected_source_keywords": ["Doanh nghiệp", "tư cách pháp nhân", "tài sản"],
        "expected_section": "Điều 2.1",
        "expected_answer_hint": "Tổ chức kinh tế có tư cách pháp nhân, có tài sản, hợp pháp độc lập, chịu trách nhiệm bằng tài sản của mình trước nhà nước và các chủ thể khác.",
        "type": "answered",
    },
    {
        "id": "A3",
        "question": "Hình thức doanh nghiệp nào được nhắc đến trong tài liệu?",
        "expected_source_keywords": ["công ty TNHH", "công ty cổ phần", "trách nhiệm hữu hạn"],
        "expected_section": "Điều 3.2",
        "expected_answer_hint": "Công ty TNHH, công ty cổ phần, doanh nghiệp trách nhiệm hữu hạn.",
        "type": "answered",
    },
    {
        "id": "A4",
        "question": "Ngày nào được coi là ngày có hiệu lực của giấy phép khởi nghiệp?",
        "expected_source_keywords": ["ngày cấp", "khởi nghiệp", "bắt đầu"],
        "expected_section": "Điều 3.3",
        "expected_answer_hint": "Ngày cấp là ngày bắt đầu, không phải ngày nộp hồ sơ.",
        "type": "answered",
    },
    {
        "id": "A5",
        "question": "Hồ sơ thành lập công ty cổ phần cần nhất định phải có gì (ít nhất)?",
        "expected_source_keywords": ["Giấy đặt tên", "Báo cáo tài chính dự kiến", "Danh sách tối thiểu cổ đông"],
        "expected_section": "Điều 4.1",
        "expected_answer_hint": "Giấy đặt tên, Báo cáo tài chính dự kiến, Danh sách tối thiểu cổ đông (tối thiểu 3 người), Giấy phép doanh nghiệp (nếu có).",
        "type": "answered",
    },
    {
        "id": "A6",
        "question": "Đơn vị tiền tệ nào được dùng trong báo cáo tài chính theo tài liệu này?",
        "expected_source_keywords": ["đồng Việt Nam", "VND"],
        "expected_section": "Điều 4.2",
        "expected_answer_hint": "Đồng Việt Nam (VND).",
        "type": "answered",
    },
    {
        "id": "A7",
        "question": "Cổ đông có quyền gì theo tài liệu?",
        "expected_source_keywords": ["cổ tức", "HĐQT", "biểu quyết", "mua lại cổ phần"],
        "expected_section": "Điều 5.1",
        "expected_answer_hint": "Nhận cổ tức, tham dự HĐQT, biểu quyết, khiển đại diện doanh nghiệp, yêu cầu mua lại cổ phần.",
        "type": "answered",
    },
    {
        "id": "A8",
        "question": "Cổ đông có quyền tiếp cận tài liệu kế toán tự do không?",
        "expected_source_keywords": ["không có quyền", "tài liệu kế toán", "HĐQT"],
        "expected_section": "Điều 5.2",
        "expected_answer_hint": "Không — chỉ khi được cấp bởi HĐQT.",
        "type": "answered",
    },
    {
        "id": "A9",
        "question": "Cổ đông chịu trách nhiệm bằng tài sản gì?",
        "expected_source_keywords": ["cổ phần đã đưa ra", "không phải tài sản riêng"],
        "expected_section": "Điều 6.1",
        "expected_answer_hint": "Bằng cổ phần đã đưa ra, không phải tài sản riêng.",
        "type": "answered",
    },
    {
        "id": "A10",
        "question": "Địa chỉ trụ sở chính của doanh nghiệp phải như thế nào?",
        "expected_source_keywords": ["thực tế", "liên lạc được", "địa chỉ ảo"],
        "expected_section": "Điều 7.2",
        "expected_answer_hint": "Phải là địa chỉ thực tế có thể liên lạc được, không phải địa chỉ ảo.",
        "type": "answered",
    },
    {
        "id": "A11",
        "question": "HĐQT có bao nhiêu thành viên tối thiểu và nhiệm kỳ tối đa?",
        "expected_source_keywords": ["03 thành viên", "nhiệm kỳ tối đa", "05 năm"],
        "expected_section": "Điều 8.1",
        "expected_answer_hint": "Tối thiểu 03 thành viên, nhiệm kỳ tối đa 05 năm.",
        "type": "answered",
    },
    {
        "id": "A12",
        "question": "Theo điều lệ, cổ tức được chia theo gì?",
        "expected_source_keywords": ["tỷ lệ cổ phần đã góp"],
        "expected_section": "Điều 9.1",
        "expected_answer_hint": "Theo tỷ lệ cổ phần đã góp, trừ khi Điều lệ có quy định khác.",
        "type": "answered",
    },
    {
        "id": "A13",
        "question": "Khi nào cổ tức được phân phối?",
        "expected_source_keywords": ["có lợi nhuận", "thanh toán thuế"],
        "expected_section": "Điều 9.2",
        "expected_answer_hint": "Khi doanh nghiệp có lợi nhuận sau khi thanh toán thuế thu nhập doanh nghiệp.",
        "type": "answered",
    },
    {
        "id": "A14",
        "question": "Báo cáo tài chính năm bao gồm những thành phần gì?",
        "expected_source_keywords": ["Bảng cân đối", "Kết quả hoạt động", "Lưu chuyển tiền mặt", "Ghi chú"],
        "expected_section": "Điều 10.2",
        "expected_answer_hint": "Bảng cân đối, Báo cáo kết quả hoạt động, Báo cáo lưu chuyển tiền mặt, Ghi chú.",
        "type": "answered",
    },
    {
        "id": "A15",
        "question": "Ghi chú báo cáo tài chính cần ghi rõ điều gì?",
        "expected_source_keywords": ["phương pháp kế toán", "cam kết", "biến động"],
        "expected_section": "Điều 10.3",
        "expected_answer_hint": "Phương pháp kế toán, chi tiết các mục lớn, cam kết và điều kiện chưa ghi nhận, các biến động trong năm.",
        "type": "answered",
    },
]

UNCH = [
    {"id": "U1", "question": "Doanh nghiệp cần nộp hồ sơ gì để được cấp giấy phép xuất khẩu vàng?", "expected_source_keywords": ["xuất khẩu vàng"], "expected_section": "KHÔNG CÓ", "type": "unanswerable"},
    {"id": "U2", "question": "Nghĩa vụ cụ thể của cổ đông khi doanh nghiệp nợ vay ngân hàng 10 tỷ là gì?", "expected_source_keywords": ["nợ vay", "ngân hàng"], "expected_section": "KHÔNG CÓ", "type": "unanswerable"},
    {"id": "U3", "question": "Mức phí công bố thông tin doanh nghiệp hằng năm là bao nhiêu?", "expected_source_keywords": ["phí công bố", "hằng năm"], "expected_section": "KHÔNG CÓ", "type": "unanswerable"},
    {"id": "U4", "question": "Thủ tục thành lập doanh nghiệp tại Việt Nam cần bao nhiêu ngày làm việc?", "expected_source_keywords": ["ngày làm việc", "thủ tục"], "expected_section": "KHÔNG CÓ", "type": "unanswerable"},
    {"id": "U5", "question": "Cơ quan nào có thẩm quyền thu hồi giấy phép kinh doanh?", "expected_source_keywords": ["thu hồi", "thẩm quyền"], "expected_section": "KHÔNG CÓ", "type": "unanswerable"},
    {"id": "U6", "question": "Doanh nghiệp nhỏ và vừa được định nghĩa theo tiêu chí vốn và lao động như thế nào?", "expected_source_keywords": ["doanh nghiệp nhỏ và vừa", "tiêu chí"], "expected_section": "KHÔNG CÓ", "type": "unanswerable"},
    {"id": "U7", "question": "Doanh nghiệp có phải nộp báo cáo kiểm toán 90 ngày trước đại hội cổ đông không?", "expected_source_keywords": ["kiểm toán", "90 ngày"], "expected_section": "KHÔNG CÓ", "type": "unanswerable"},
    {"id": "U8", "question": "Tổ chức kiểm soát nội bộ phải được thành lập theo quy định nào?", "expected_source_keywords": ["kiểm soát nội bộ"], "expected_section": "KHÔNG CÓ", "type": "unanswerable"},
    {"id": "U9", "question": "Tỷ lệ biểu quyết tối thiểu để thông qua nghị quyết là bao nhiêu phần trăm?", "expected_source_keywords": ["phần trăm", "biểu quyết"], "expected_section": "KHÔNG CÓ (Điều 8.3 chỉ nói không quy định, theo Điều lệ)", "type": "unanswerable"},
    {"id": "U10", "question": "Doanh nghiệp phải nộp báo cáo tài chính trước ngày 31/3 hằng năm đúng không?", "expected_source_keywords": ["31/3", "nộp báo cáo"], "expected_section": "KHÔNG CÓ", "type": "unanswerable"},
]

CONF = [
    {"id": "C1", "question": "Ngày có hiệu lực của giấy phép khởi nghiệp là ngày cấp hay ngày nộp hồ sơ?", "expected_source_keywords": ["ngày cấp", "ngày nộp hồ sơ"], "expected_section": "Điều 3.3", "conflict_note": "Điều 3.3 nói rõ 'ngày cấp là ngày bắt đầu, không phải ngày nộp hồ sơ' — mô hình phải trả lời đúng một phía theo tài liệu, không được mô hồ.", "type": "conflict"},
    {"id": "C2", "question": "Cổ đông có quyền khiển đại diện doanh nghiệp — liệu mọi cổ đông hay chỉ cổ đông chiếm đa số?", "expected_source_keywords": ["khiển đại diện", "cổ đông"], "expected_section": "Điều 5.1", "conflict_note": "Tài liệu không làm rõ điều kiện — mô hình phải nêu tài liệu không quy định chi tiết, không suy diễn.", "type": "conflict"},
    {"id": "C3", "question": "Tỷ lệ cổ phần biểu quyết tối thiểu của HĐQT là bao nhiêu — luật có quy định cụ thể không?", "expected_source_keywords": ["biểu quyết", "Điều lệ"], "expected_section": "Điều 8.3", "conflict_note": "Điều 8.3 ghi 'không quy định (theo Điều lệ công ty)' — mô hình phải thừa nhận luật không chốt con số, không bịa phần trăm.", "type": "conflict"},
    {"id": "C4", "question": "Cổ tức có thể chia giữa năm không, hay phải chờ đến cuối năm?", "expected_source_keywords": ["cổ tức", "cuối năm", "Điều lệ"], "expected_section": "Điều 9.1 / Điều 9.3", "conflict_note": "Điều 9.1 cho phép 'trừ khi Điều lệ có quy định khác' nhưng Điều 9.3 nói chờ HĐ năm — hai điều này mâu thuẫn nhẹ; mô hình phải chỉ ra cả hai điều.", "type": "conflict"},
    {"id": "C5", "question": "Giám đốc vi phạm có thể bị phạt cao hơn 50 triệu đồng không?", "expected_source_keywords": ["giám đốc", "phạt", "50 triệu"], "expected_section": "Điều 11.2", "conflict_note": "Điều 11.2 ghi mức 5–50 triệu cho cá nhân; Điều 11.3 chỉ nói phạt 'tương ứng mức độ' — mô hình phải trả lời theo Điều 11.2, không suy diễn mức cao hơn.", "type": "conflict"},
]

if __name__ == "__main__":
    with open("eval/rag_30_questions.json", "w", encoding="utf-8") as f:
        json.dump(
            {"answered": QA, "unanswerable": UNCH, "conflict": CONF},
            f,
            ensure_ascii=False,
            indent=2,
        )
    assert len(QA) == 15 and len(UNCH) == 10 and len(CONF) == 5, (
        f"bad split: {len(QA)}/{len(UNCH)}/{len(CONF)}"
    )
    print(
        "Wrote 30 questions:",
        f"{len(QA)} answered / {len(UNCH)} unanswerable / {len(CONF)} conflict",
    )
