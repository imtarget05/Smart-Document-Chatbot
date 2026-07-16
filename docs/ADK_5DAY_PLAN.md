# ADK + 5-Day Video Coding Plan

## Mục tiêu

Bổ sung một mô hình Agent Development Kit (ADK) nhẹ và có thể mở rộng vào dự án này, phù hợp cho demo 5 ngày video coding. Mục tiêu không phải thay thế toàn bộ LangGraph hiện có, mà là tạo một lớp abstraction dễ hiểu để:
- mô tả agent bằng spec rõ ràng,
- chạy agent ở mode deterministic cho demo,
- chuẩn bị nền tảng cho ADK/LLM agent phức tạp hơn sau này.

## Phân tích hiện trạng

- Dự án đã có agent service Python với LangGraph và nhiều specialist agent.
- Các agent hiện tại tập trung vào orchestration, RAG, reporting, action, comparator, researcher, engineering.
- Để demo 5 ngày, tốt nhất nên thêm một "ADK layer" ở trên cùng, cung cấp:
  - agent spec,
  - execution wrapper,
  - testable contract,
  - optional integration với LangGraph later.

## Kế hoạch triển khai

### Phase 1 — Foundation (Ngày 1)
- Tạo module ADK nhẹ: `agent/adk_agent.py`
- Định nghĩa `AdkAgentSpec` và `AdkAgent`
- Viết unit test tối thiểu cho contract đầu ra
- Cấu hình import và docs

### Phase 2 — Integration (Ngày 2)
- Kết nối ADK wrapper với agent service hiện có
- Cho phép chọn agent mode: `langgraph` hoặc `adk-lite`
- Thêm endpoint mẫu / health hoặc /demo/adk

### Phase 3 — Demo workflow (Ngày 3)
- Xây dựng workflow 5-day demo:
  1. ingest document,
  2. analyze content,
  3. generate summary,
  4. create action items,
  5. produce report
- Mỗi bước dùng một agent spec riêng

### Phase 4 — Observability (Ngày 4)
- Ghi log input/output cho mỗi agent execution
- Thêm trạng thái `running/success/error`
- Chuẩn bị trace cho video demo

### Phase 5 — Polish (Ngày 5)
- Viết README demo ngắn
- Chuẩn bị sample prompt và expected output
- Cấu hình để chạy nhanh trên local machine

## Gợi ý kiến trúc

```text
User Request
  -> ADK Router
  -> Agent Spec
  -> Execution Adapter
  -> Tool Layer / LLM / Memory
  -> Response + Trace
```

## Khuyến nghị dùng cho dự án này

- Giữ `LangGraph` như engine chính cho workflow phức tạp.
- Thêm `ADK-lite` như lớp giao diện dễ học, dễ demo, dễ test.
- Không bắt bu chuyển hoàn toàn sang ADK trong sprint đầu.

## Deliverables cuối cùng

- Một module ADK nhẹ có thể chạy local
- Một workflow demo 5 ngày có thể trình bày trên video
- Tài liệu và test cơ bản
