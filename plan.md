


Làm theo đúng thứ tự Phase (0 → 7). Mỗi Phase phụ thuộc vào Phase trước.
Với mỗi Task, copy nguyên phần "Prompt cho AI" và dán cho Claude Code cùng với đường dẫn repo.
Sau khi AI code xong, kiểm tra theo "Definition of Done" trước khi qua task tiếp theo.
Review code + chạy test trước khi merge, kể cả khi AI báo "xong".



PHASE 0 — Chuẩn bị hạ tầng & Baseline

Task 0.1 — Audit codebase hiện tại

Mục tiêu: Có bản đồ chính xác cấu trúc code hiện tại trước khi sửa.
Prompt cho AI:

Hãy quét toàn bộ repo (frontend, backend Spring Boot, agent-service Python) và tạo file
docs/ARCHITECTURE_CURRENT.md mô tả:
- Danh sách module/package chính của từng service
- Các endpoint API hiện có (REST + SSE) kèm method, path, mô tả ngắn
- Danh sách agent trong LangGraph hiện tại, tool nào mỗi agent đang gọi
- Các bảng chính trong PostgreSQL và schema tóm tắt
- Biến môi trường (.env) đang được dùng ở mỗi service
Không sửa code, chỉ tạo tài liệu.

Definition of Done: File docs/ARCHITECTURE_CURRENT.md tồn tại, phản ánh đúng thực tế code (bạn đọc lướt và thấy khớp).

Task 0.2 — Chuẩn hóa Docker Compose cho môi trường dev

Mục tiêu: Một lệnh docker compose up chạy được toàn bộ hệ thống + n8n để dev thử nghiệm.
Prompt cho AI:

Cập nhật docker-compose.yml (hoặc tạo docker-compose.n8n.yml riêng) để thêm service n8n:
- image: n8nio/n8n:latest
- port 5678:5678
- volume ~/.n8n để lưu workflow
- biến môi trường: N8N_BASIC_AUTH_ACTIVE=true, N8N_BASIC_AUTH_USER, N8N_BASIC_AUTH_PASSWORD
- N8N_HOST, N8N_PROTOCOL, WEBHOOK_URL trỏ về địa chỉ local (http://localhost:5678)
- Kết nối n8n vào cùng network Docker với agent-service và PostgreSQL để có thể gọi nội bộ
- Thêm PostgreSQL riêng cho n8n (hoặc dùng schema riêng trong Postgres hiện có) để lưu execution history
Cập nhật README.md thêm hướng dẫn chạy n8n cục bộ.

Definition of Done: docker compose up n8n chạy được, truy cập http://localhost:5678 thấy giao diện n8n, đăng nhập bằng basic auth đã cấu hình.


Lưu ý lựa chọn triển khai: Bạn chọn cả self-host Docker (cho dev/test và production nội bộ) và n8n Cloud (cho production khi cần uptime/SLA cao hoặc không muốn tự quản lý hạ tầng). Khuyến nghị: dùng self-host Docker cho môi trường dev/staging, đánh giá chuyển sang n8n Cloud cho production sau khi workflow đã ổn định — vì n8n Cloud có sẵn backup, scaling, và bạn không cần lo update version. Task 0.3 xử lý việc này.



Task 0.3 — Thiết lập song song 2 môi trường n8n

Mục tiêu: Có cấu hình sẵn sàng chuyển đổi giữa self-host và Cloud mà không phải sửa code Agent Service.
Prompt cho AI:

Tạo file agent-service/config/n8n_config.py (hoặc tương đương ở ngôn ngữ dự án) với:
- Đọc biến môi trường N8N_BASE_URL, N8N_WEBHOOK_PATH, N8N_API_KEY từ .env
- Một hàm get_n8n_webhook_url(workflow_name: str) trả về URL đầy đủ, không hardcode domain
- File .env.example thêm 2 block mẫu:
  # Self-host
  N8N_BASE_URL=http://n8n:5678
  # Cloud (comment lại khi dùng self-host)
  # N8N_BASE_URL=https://<your-instance>.app.n8n.cloud
Viết docs/N8N_DEPLOYMENT_OPTIONS.md so sánh ngắn gọn 2 lựa chọn và cách chuyển đổi.

Definition of Done: Đổi N8N_BASE_URL trong .env là chuyển được môi trường mà không cần sửa code.


PHASE 1 — RBAC & Audit Logging (nền tảng bắt buộc trước khi mở rộng Action Agent)

Task 1.1 — Thiết kế schema RBAC

Prompt cho AI:

Trong backend Spring Boot, thiết kế và tạo migration (Flyway/Liquibase, dùng đúng công cụ
migration hiện có trong repo) cho các bảng:
- users (nếu chưa có đầy đủ)
- roles (id, name, description) — seed sẵn: ADMIN, EDITOR, VIEWER, AGENT_OPERATOR
- permissions (id, code, description) — seed: DOC_UPLOAD, DOC_DELETE, CHAT_USE,
  AGENT_ACTION_EXECUTE, REPORT_GENERATE, ADMIN_PANEL_ACCESS
- role_permissions (role_id, permission_id)
- user_roles (user_id, role_id)
Viết entity/repository tương ứng theo pattern đang dùng trong dự án (JPA).

Definition of Done: Migration chạy thành công, seed data có trong DB, entity map đúng quan hệ.

Task 1.2 — Middleware/Filter kiểm tra quyền

Prompt cho AI:

Tạo annotation @RequirePermission("AGENT_ACTION_EXECUTE") dùng trên controller method,
kết hợp Spring Security AOP để chặn request nếu user không có quyền tương ứng.
Áp dụng annotation này cho các endpoint: upload tài liệu, xóa tài liệu, thực thi Action Agent,
truy cập trang admin. Trả về HTTP 403 kèm message rõ ràng khi bị từ chối.
Viết unit test cho middleware này (test case: user có quyền → pass, không có quyền → 403).

Definition of Done: Test pass, gọi thử API bằng user không đủ quyền trả về 403.

Task 1.3 — Audit Logging Service

Prompt cho AI:

Tạo bảng audit_logs (id, user_id, action_type, resource_type, resource_id, metadata JSONB,
ip_address, created_at). Tạo AuditLogService với method log(userId, actionType, resourceType,
resourceId, metadata).
Gắn log tự động (qua AOP hoặc interceptor) cho các hành động nhạy cảm:
- upload/xóa tài liệu
- agent thực thi action (gửi email, tạo ticket, gọi webhook)
- thay đổi role của user
- đăng nhập/đăng xuất
Thêm endpoint GET /api/admin/audit-logs (chỉ ADMIN) hỗ trợ filter theo user, action_type, khoảng
thời gian, có phân trang.

Definition of Done: Thực hiện một hành động (vd upload file) → thấy record mới trong audit_logs; endpoint admin trả về đúng dữ liệu có phân trang.

Task 1.4 — Frontend: màn hình quản lý Role & Audit Log

Prompt cho AI:

Trong frontend React, tạo trang /admin/users để ADMIN gán role cho user, và trang
/admin/audit-logs hiển thị bảng log có filter (user, loại hành động, khoảng ngày) và phân trang.
Dùng component/style pattern đã có sẵn trong dự án. Ẩn menu này với user không phải ADMIN.

Definition of Done: ADMIN đăng nhập thấy 2 trang mới, user thường không thấy menu, dữ liệu hiển thị đúng và filter hoạt động.


PHASE 2 — Tích hợp n8n với Action Agent

Task 2.1 — Chuẩn hóa contract webhook Agent ↔ n8n

Prompt cho AI:

Tạo file docs/N8N_WEBHOOK_CONTRACT.md mô tả chuẩn payload JSON gửi từ Action Agent đến n8n:
{
  "action_id": "uuid",
  "action_type": "send_email | create_jira_ticket | create_notion_page | call_webhook",
  "requested_by": "user_id",
  "requires_approval": true,
  "payload": { ... tùy action_type ... },
  "callback_url": "URL agent-service để n8n gọi lại báo kết quả"
}
Và chuẩn response n8n trả về agent-service:
{
  "action_id": "uuid",
  "status": "success | failed | pending_approval",
  "result": { ... },
  "error": null
}
Định nghĩa rõ từng action_type cần field gì trong payload (email cần to/subject/body,
jira cần project_key/summary/description, v.v.)

Definition of Done: File contract rõ ràng, đủ chi tiết để 2 team (agent-service + n8n workflow) làm độc lập theo cùng 1 chuẩn.

Task 2.2 — Sửa Action Agent gọi qua n8n thay vì gọi trực tiếp API ngoài

Prompt cho AI:

Trong agent-service (Python), refactor Action Agent hiện tại (email/webhook/Jira/Notion):
- Tạo class N8nActionDispatcher với method dispatch(action_type, payload, requires_approval)
- Method này gọi HTTP POST đến webhook n8n tương ứng (dùng N8N_BASE_URL từ config Task 0.3)
- Timeout 10s, retry tối đa 2 lần với backoff nếu lỗi mạng
- Ghi log request/response (không log dữ liệu nhạy cảm như token, password)
- Thay thế các đoạn code gọi trực tiếp SMTP/Jira API/Notion API hiện có bằng dispatcher này
  (giữ code cũ trong file _legacy nếu cần rollback)
Viết unit test mock HTTP call, test cả case success/fail/timeout.

Definition of Done: Action Agent gọi n8n thành công (kiểm tra qua log n8n execution), test unit pass.

Task 2.3 — Xây workflow n8n: Send Email

Prompt cho AI (mô tả để bạn tự làm trong n8n UI, hoặc export/import JSON):

Tạo workflow n8n tên "agent-send-email":
1. Webhook node: nhận POST tại /webhook/agent-send-email, validate có đủ field to/subject/body
2. IF node: kiểm tra requires_approval
   - true → gửi thông báo Slack/Email cho người duyệt kèm nút Approve/Reject (dùng Wait node +
     webhook resume), hoặc đơn giản hơn: ghi vào bảng "pending_actions" và dừng lại
   - false → đi thẳng bước gửi mail
3. Send Email node (SMTP hoặc Gmail node) gửi mail theo payload
4. HTTP Request node: gọi lại callback_url của agent-service báo kết quả (theo contract Task 2.1)
5. Error Trigger: nếu lỗi ở bất kỳ bước nào, gọi callback_url với status=failed
Export workflow ra file n8n/workflows/agent-send-email.json và commit vào repo.

Definition of Done: Test gửi 1 email thật qua webhook, agent-service nhận được callback đúng trạng thái.

Task 2.4 — Xây workflow n8n: Jira / Notion / Generic Webhook

Prompt cho AI:

Tương tự Task 2.3, tạo thêm 3 workflow n8n:
- agent-create-jira-ticket (dùng Jira node hoặc HTTP Request đến Jira REST API v3)
- agent-create-notion-page (dùng Notion node)
- agent-generic-webhook (HTTP Request node linh hoạt, cho phép Agent gọi bất kỳ webhook nào
  agent tự cấu hình dạng payload URL + method + body, có whitelist domain để tránh SSRF)
Mỗi workflow đều tuân thủ contract callback giống Task 2.3.
Export tất cả ra n8n/workflows/*.json, viết README trong n8n/workflows/README.md hướng dẫn
import vào instance n8n mới.

Definition of Done: 3 workflow hoạt động, test thử mỗi loại action, dữ liệu tạo đúng trên Jira/Notion, generic webhook chặn được domain lạ.

Task 2.5 — Endpoint callback nhận kết quả từ n8n

Prompt cho AI:

Trong agent-service, tạo endpoint POST /internal/n8n-callback nhận payload theo chuẩn Task 2.1.
- Xác thực request đến từ n8n bằng shared secret header (X-N8N-Signature), không public endpoint
  này ra ngoài
- Cập nhật trạng thái action trong bảng agent_actions (tạo bảng này nếu chưa có: id, action_type,
  status, payload, result, created_at, updated_at)
- Nếu có SSE session đang chờ (chat đang chờ agent hoàn thành action), push cập nhật realtime
  cho frontend qua kênh SSE hiện có

Definition of Done: Gọi thử callback giả lập → thấy agent_actions cập nhật đúng, frontend (nếu đang mở chat) nhận được cập nhật realtime.


PHASE 3 — Chuẩn hóa Tool Schema cho toàn bộ Agent

Task 3.1 — Định nghĩa Tool Registry chung

Prompt cho AI:

Trong agent-service, tạo module tools/registry.py:
- Định nghĩa base class Tool với: name, description, input_schema (Pydantic model),
  async def execute(input) -> ToolResult
- Tạo ToolRegistry quản lý danh sách tool, có method register(tool) và get_tool(name)
- Migrate các tool hiện có (search document, generate report, compare documents,
  web research, call n8n action) sang format chuẩn này
- Tool "n8n_action" bọc quanh N8nActionDispatcher (Task 2.2) như một tool bình thường,
  để bất kỳ agent nào (không chỉ Action Agent) cũng có thể gọi
Viết test đảm bảo mỗi tool cũ vẫn hoạt động đúng sau khi migrate.

Definition of Done: Toàn bộ tool cũ chạy qua registry mới, test hồi quy pass, không phá vỡ chức năng hiện có.

Task 3.2 — Chuẩn hóa function-calling schema cho LLM

Prompt cho AI:

Viết hàm export_tools_as_llm_schema() sinh danh sách tool ở định dạng function-calling chuẩn
(OpenAI-compatible / phù hợp với LLM router đang dùng trong dự án), lấy dữ liệu từ ToolRegistry
(Task 3.1) thay vì định nghĩa tay rải rác trong từng agent như hiện tại.
Cập nhật LangGraph nodes để lấy schema từ hàm này khi gọi LLM.

Definition of Done: Tất cả agent lấy tool schema từ 1 nguồn duy nhất, không còn định nghĩa trùng lặp trong code.


PHASE 4 — Orchestrator Agent (Multi-Agent Routing)

Task 4.1 — Thiết kế Orchestrator node trong LangGraph

Prompt cho AI:

Thiết kế và cài đặt OrchestratorAgent trong agent-service dùng LangGraph:
- Node đầu vào nhận câu hỏi/yêu cầu user + lịch sử hội thoại
- Dùng LLM để phân loại intent và sinh ra "execution plan": danh sách bước, mỗi bước gọi
  1 agent chuyên biệt hiện có (RAG, Report, Comparator, Researcher, Action, Engineering)
- Hỗ trợ plan tuần tự (bước sau phụ thuộc kết quả bước trước) và plan song song (độc lập)
- Nếu 1 bước trong plan là hành động có tác động ra ngoài (Action Agent), chèn bước
  "human approval" trước khi thực thi (dùng lại cơ chế Task 2.3 requires_approval)
- Log toàn bộ plan + kết quả từng bước vào bảng agent_execution_logs để debug
Viết test case cho ít nhất 3 kịch bản: (1) chỉ cần RAG đơn giản, (2) cần RAG + Report,
(3) cần Researcher + Action (có approval).

Definition of Done: 3 test case chạy đúng, plan sinh ra hợp lý, log đầy đủ trong DB.

Task 4.2 — API endpoint cho Orchestrator

Prompt cho AI:

Tạo/cập nhật endpoint POST /api/chat/orchestrated (SSE streaming) để frontend gọi Orchestrator
Agent thay vì gọi thẳng RAG agent như hiện tại. Giữ nguyên endpoint /api/chat cũ để không breaking
change, đánh dấu deprecated trong docs.
Stream về frontend: từng bước đang chạy (ví dụ "Đang tìm tài liệu liên quan...",
"Đang tạo báo cáo...") để UI hiển thị tiến trình.

Definition of Done: Gọi thử endpoint mới, frontend (hoặc Postman với SSE) nhận được stream các bước tiến trình rõ ràng.


PHASE 5 — Memory Layer (Short-term + Long-term)

Task 5.1 — Short-term memory (session)

Prompt cho AI:

Kiểm tra cơ chế lưu lịch sử chat hiện tại (theo Task 0.1 đã audit). Nếu chưa có, tạo bảng
chat_sessions và chat_messages (nếu đã có thì bỏ qua bước tạo bảng).
Đảm bảo Orchestrator Agent (Task 4.1) luôn nhận đủ N tin nhắn gần nhất (cấu hình được, mặc định
10) làm context, kể cả khi câu hỏi hiện tại không liên quan trực tiếp đến tài liệu.

Definition of Done: Hỏi 1 câu tham chiếu ngữ cảnh câu trước ("còn cái thứ 2 thì sao?") → agent trả lời đúng nhờ nhớ ngữ cảnh.

Task 5.2 — Long-term memory theo user/dự án

Prompt cho AI:

Tạo bảng user_memory (id, user_id, project_id, memory_type, content, embedding_vector,
created_at). Tạo MemoryService:
- extract_memory_candidates(conversation): dùng LLM tóm tắt các thông tin đáng nhớ dài hạn
  từ hội thoại (sở thích định dạng báo cáo, thông tin lặp lại nhiều lần, quyết định đã chốt)
- store_memory(user_id, project_id, content): embed và lưu vào Qdrant (collection riêng
  "user_memory") + bảng user_memory
- retrieve_relevant_memory(user_id, project_id, query): semantic search trả về top-k memory
  liên quan để đưa vào context của Orchestrator Agent
Chạy extract_memory_candidates bất đồng bộ sau mỗi phiên chat kết thúc (không block response).

Definition of Done: Sau vài phiên chat có thông tin lặp lại, agent tự nhớ và áp dụng ở phiên chat mới mà không cần user nhắc lại.


PHASE 6 — Mở rộng Connector

Task 6.1 — Chuẩn hóa Connector Interface

Prompt cho AI:

Tạo interface DocumentConnector (Python) với method list_files(), fetch_file(file_id),
get_metadata(file_id), tương tự cách n8n định nghĩa credentials/node.
Refactor local file ingestion hiện có thành LocalFileConnector implement interface này.
Thiết kế sao cho thêm connector mới chỉ cần implement interface, không sửa pipeline ingestion.

Definition of Done: Local ingestion vẫn hoạt động y hệt sau refactor, có thể thêm connector mới bằng cách implement 1 class.

Task 6.2 — Google Drive Connector (qua n8n)

Prompt cho AI:

Tạo workflow n8n "sync-google-drive" dùng Google Drive node: theo lịch (cron mỗi 15 phút hoặc
trigger watch), phát hiện file mới/sửa đổi trong 1 thư mục chỉ định, tải file và gọi API
agent-service (endpoint ingest hiện có) để đưa vào pipeline xử lý.
Tạo GoogleDriveConnector phía agent-service implement DocumentConnector (Task 6.1) chỉ để
tra cứu metadata khi cần, còn việc đồng bộ chính do n8n đảm nhiệm.

Definition of Done: Thêm 1 file mới vào thư mục Google Drive theo dõi → sau tối đa 15 phút file xuất hiện trong danh sách tài liệu đã ingest.


PHASE 7 — CI/CD & Đánh giá chất lượng Agent

Task 7.1 — Bộ test đánh giá RAG (eval set)

Prompt cho AI:

Tạo thư mục eval/ chứa bộ câu hỏi mẫu (tối thiểu 30 câu) kèm câu trả lời mong đợi/tài liệu nguồn
đúng, dựa trên tài liệu mẫu có sẵn trong dự án.
Viết script eval/run_eval.py: chạy RAG agent với từng câu hỏi, so sánh câu trả lời với đáp án
mong đợi (dùng LLM-as-judge chấm điểm relevance/faithfulness/citation-accuracy thang 1-5),
xuất báo cáo eval/report.md.

Definition of Done: Chạy script ra báo cáo điểm số rõ ràng, có thể chạy lại sau mỗi thay đổi lớn để so sánh regression.

Task 7.2 — Pipeline CI/CD

Prompt cho AI:

Tạo/cập nhật GitHub Actions workflow (.github/workflows/ci.yml):
- job build & test cho frontend (npm test/build)
- job build & test cho backend Spring Boot (mvn test)
- job build & test cho agent-service (pytest)
- job chạy eval/run_eval.py (Task 7.1), fail pipeline nếu điểm trung bình giảm quá ngưỡng
  so với lần chạy trước (lưu baseline trong repo hoặc artifact)
- job build Docker image và push registry khi merge vào nhánh main
Thêm badge trạng thái CI vào README.md.

Definition of Done: Push code → pipeline chạy tự động, fail đúng lúc cần (vd cố tình phá test), pass khi code ổn.


Tổng quan phụ thuộc giữa các Phase

Phase 0 (hạ tầng)
    │
Phase 1 (RBAC/Audit) ──► bắt buộc trước Phase 2 vì Action Agent cần kiểm soát quyền
    │
Phase 2 (n8n + Action Agent)
    │
Phase 3 (Tool Registry) ──► dọn code trước khi thêm Orchestrator
    │
Phase 4 (Orchestrator Agent)
    │
Phase 5 (Memory Layer) ──► có thể làm song song với Phase 6
    │
Phase 6 (Connector mở rộng)
    │
Phase 7 (CI/CD & Eval) ──► nên bắt đầu sớm song song, hoàn thiện cuối cùng

Ghi chú triển khai n8n (Self-host + Cloud)

Self-host Dockern8n CloudDùng choDev, staging, production nội bộ ít trafficProduction cần uptime cao, không muốn tự vận hànhChi phíServer + công vận hànhSubscription theo executionCập nhật versionTự làmTự độngĐộ trễ webhook nội bộThấp (cùng network Docker)Cao hơn (qua internet) — cân nhắc với action cần tốc độKhuyến nghị lộ trìnhDùng ngay từ Task 0.2Đánh giá chuyển sau khi Phase 2 ổn định, dùng song song để so sánh độ ổn định trước khi quyết định hẳn  