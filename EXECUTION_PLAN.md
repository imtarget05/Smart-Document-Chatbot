# Smart Document Chatbot — Execution Plan (Updated 2026-07-09)

## Phân tích hiện trạng (Đối chiếu với task.md)

### Trạng thái THỰC TẾ vs task.md

| Item | task.md Status | THỰC TẾ | Ghi chú |
|------|---------------|----------|---------|
| 1.1-1.10 Backend RBAC + Audit Log | ✅ Complete | ✅ **ĐÃ CÓ ĐẦY ĐỦ** | JWT + 3 roles + Service role + AOP audit logging + admin API stats |
| 1.11 Frontend AuditLogs + Settings + role-based UI | ❌ Incomplete | ⚠️ **COPONENT CÓ SẴN nhưng sơ sài** | AuditLogsPage, SettingsPage, AdminUsersPage, DashboardPage, KnowledgeBasePage đều tồn tại trong App.tsx như tab-based |
| 2.1 DataSource entity | ✅ Complete | ✅ **ĐÃ CÓ** | Backend Java có entity + controller + service |
| 2.2 DataSource repository | ❌ Incomplete | ✅ **ĐÃ CÓ** | Repository pattern trong Spring Boot |
| 2.3 DataSourceController + Service | ❌ Incomplete | ✅ **ĐÃ CÓ** | Controller/service đã implement |
| 2.4 IngestionPipelineService mở rộng | ❌ Incomplete | ⚠️ **CƠ BẢN** | Có ConnectorIngestionPipeline trong agent Python |
| 2.5 Agent connector implementations | ❌ Incomplete | ✅ **ĐÃ CÓ 4 CONNECTOR** | Gmail, Google Drive, SharePoint, Slack |
| 2.6 Frontend DataSources page | ❌ Incomplete | ✅ **COPONENT CÓ SẴN** | DataSourcesPage.tsx đã có trong App.tsx |
| 3.1 8D Case entity + controller + service | ❌ Incomplete | ❌ **CHƯA CÓ** | Chưa thấy trong backend Java |
| 3.2 Evaluation entity + controller + service | ❌ Incomplete | ⚠️ **CÓ SCRIPT eval/** | Có eval.py và agent_eval.py nhưng chưa tích hợp backend |
| 3.3 Frontend 8D + EvaluationLab | ❌ Incomplete | ✅ **COPONENT CÓ SẴN** | EightDCasesPage.tsx, EvaluationLabPage.tsx |
| 4.1 Dashboard page | ❌ Incomplete | ✅ **COPONENT CÓ SẴN** | DashboardPage.tsx (hardcoded stats) |
| 4.2 KnowledgeBase page | ❌ Incomplete | ✅ **COPONENT CÓ SẴN** | KnowledgeBasePage.tsx |
| 4.3 Sidebar navigation + Router | ❌ Incomplete | ⚠️ **TAB-BASED, KHÔNG DÙNG ROUTER** | App.tsx dùng state tabs, không React Router |
| 5.1 GitHub Actions CI | ❌ Incomplete | ❌ **CHƯA CÓ** | Không thấy .github/workflows |
| 5.2 Docs (ARCHITECTURE, SECURITY, README) | ❌ Incomplete | ⚠️ **CÓ TRONG eng-intel-copilot/docs/** | Nhưng chưa ở root project |
| 5.3 DEMO_GUIDE, SELF_HOSTING_GUIDE | ❌ Incomplete | ✅ **ĐÃ CÓ TRONG eng-intel-copilot/docs/** | Cần copy/sync ra root |

### Kết luận: Dự án đã hoàn thiện ~70-80%, nhiều item trong task.md đánh dấu chưa xong thực chất ĐÃ CÓ nhưng ở mức sơ khai/cơ bản.

---

## Kế hoạch thực thi chi tiết (theo thứ tự ưu tiên)

### PHASE 1: Hoàn thiện Frontend Enterprise Pages (TASK 4.3, 1.11, 4.1, 4.2) ⭐ CAO NHẤT

**Mục tiêu:** Các component frontend đã có nhưng đang dùng tab-based navigation trong App.tsx (621 dòng). Cần refactor sang React Router, nâng cấp giao diện, thêm role-based UI.

#### Step 1.1: Cài đặt React Router + Refactor App.tsx
- [ ] 1.1.1: Cài `react-router-dom` 
- [ ] 1.1.2: Tạo `src/pages/` folder, tách mỗi tab thành page riêng
- [ ] 1.1.3: Tạo Layout component với Sidebar navigation
- [ ] 1.1.4: Setup routes: `/`, `/dashboard`, `/knowledge`, `/datasources`, `/eightd`, `/evaluation`, `/audit`, `/settings`, `/admin`
- [ ] 1.1.5: Di chuyển auth flow vào AuthContext/AuthProvider

#### Step 1.2: Nâng cấp DashboardPage
- [ ] 1.2.1: Gọi API `/api/stats` để lấy thống kê thực (documents count, chat sessions, active users)
- [ ] 1.2.2: Hiển thị biểu đồ đơn giản (recharts)
- [ ] 1.2.3: Recent activity feed

#### Step 1.3: Nâng cấp KnowledgeBasePage
- [ ] 1.3.1: Tích hợp search/filter documents
- [ ] 1.3.2: Hiển thị trạng thái processing/ready/failed với badge
- [ ] 1.3.3: Bulk actions (delete, re-index)

#### Step 1.4: Role-based UI
- [ ] 1.4.1: Admin menu items (AdminUsers, AuditLogs) chỉ hiển thị cho role ADMIN
- [ ] 1.4.2: Upload document button chỉ hiển thị cho ADMIN + ENGINEER
- [ ] 1.4.3: Protected routes với role check

---

### PHASE 2: Backend 8D Case Module (TASK 3.1, 3.3) ⭐ CAO

**Mục tiêu:** Tạo entity, controller, service cho 8D Case trong backend Java Spring Boot.

#### Step 2.1: Entity + DB migration
- [ ] 2.1.1: Tạo entity `EightDCase.java` (fields: id, title, problemDescription, d1_team, d2_describe, d3_containment, d4_rootCause, d5_correctiveAction, d6_verification, d7_preventRecurrence, d8_recognition, status, documentId, createdAt, updatedAt)
- [ ] 2.1.2: Tạo repository `EightDCaseRepository.java`

#### Step 2.2: Service + Controller
- [ ] 2.2.1: Tạo `EightDCaseService.java` (CRUD + timeline tracking + AI suggestion endpoint)
- [ ] 2.2.2: Tạo `EightDCaseController.java` (GET/POST/PUT/DELETE + PATCH status)
- [ ] 2.2.3: Endpoint AI suggestion: POST `/api/eightd/{id}/suggest` → gọi agent service

#### Step 2.3: Nâng cấp Frontend EightDCasesPage
- [ ] 2.3.1: List view với filter/search
- [ ] 2.3.2: Detail view với 8 step timeline
- [ ] 2.3.3: Create/Edit form wizard (D1 → D8)
- [ ] 2.3.4: AI Suggest button cho từng D-step

---

### PHASE 3: Evaluation Lab Integration (TASK 3.2, 3.3) ⭐ TRUNG BÌNH

**Mục tiêu:** Tích hợp bộ eval Python vào backend, tạo UI dashboard đánh giá.

#### Step 3.1: Backend Evaluation API
- [ ] 3.1.1: Tạo entity `Evaluation.java` (id, name, dataset, metrics, results, status, createdAt)
- [ ] 3.1.2: Tạo `EvaluationService.java` gọi agent Python eval pipeline
- [ ] 3.1.3: Endpoint: POST `/api/evaluation/run` (trigger eval), GET `/api/evaluation/results`

#### Step 3.2: Nâng cấp Frontend EvaluationLabPage
- [ ] 3.2.1: Upload dataset UI
- [ ] 3.2.2: Run evaluation với progress indicator
- [ ] 3.2.3: Results display (precision, recall, faithfulness, relevance scores)
- [ ] 3.2.4: Compare results giữa các eval runs

---

### PHASE 4: CI/CD & Documentation (TASK 5.1, 5.2, 5.3) ⭐ CAO

**Mục tiêu:** Thiết lập CI pipeline và đồng bộ tài liệu.

#### Step 4.1: GitHub Actions CI
- [ ] 4.1.1: Tạo `.github/workflows/ci.yml`
- [ ] 4.1.2: Jobs: build-backend (Maven), build-frontend (npm), test (JUnit + Playwright), lint
- [ ] 4.1.3: Docker build + push to registry

#### Step 4.2: Tài liệu root project
- [ ] 4.2.1: Copy/sync docs từ `engineering-intelligence-copilot/docs/` ra root `docs/`
- [ ] 4.2.2: Cập nhật `README.md` với architecture overview, quick start
- [ ] 4.2.3: Đảm bảo `ARCHITECTURE.md`, `SECURITY.md`, `DEMO_GUIDE.md`, `SELF_HOSTING_GUIDE.md` có ở root

---

### PHASE 5: Kiểm thử & Polish ⭐ TRUNG BÌNH

#### Step 5.1: Backend tests
- [ ] 5.1.1: Unit test cho 8D Case service
- [ ] 5.1.2: Integration test cho Evaluation API
- [ ] 5.1.3: API test cho RBAC endpoints

#### Step 5.2: Frontend tests
- [ ] 5.2.1: Unit test cho DashboardPage (hiện đã có test file)
- [ ] 5.2.2: E2E test với Playwright cho luồng chính (uploads → chat → 8D)

#### Step 5.3: Polish
- [ ] 5.3.1: Loading states + error boundaries tất cả pages
- [ ] 5.3.2: Responsive design check
- [ ] 5.3.3: Dark mode support (nếu cần)

---

## Thứ tự thực hiện tổng thể

```
PHASE 1: Frontend Router + Enterprise UI  ← BẮT ĐẦU NGAY
  |
  ├── 1.1: React Router + Layout refactor
  ├── 1.2: Dashboard nâng cấp  
  ├── 1.3: KnowledgeBase nâng cấp
  └── 1.4: Role-based UI
  |
PHASE 4: CI/CD + Documentation
  |
  ├── 4.1: GitHub Actions CI
  └── 4.2: Root docs sync
  |
PHASE 2: 8D Case Module
  |
  ├── 2.1: Entity + Repository
  ├── 2.2: Service + Controller
  └── 2.3: Frontend 8D nâng cấp
  |
PHASE 3: Evaluation Lab
  |
  ├── 3.1: Backend API
  └── 3.2: Frontend UI
  |
PHASE 5: Testing + Polish
```

---

## Timeline dự kiến

| Phase | Task | Effort |
|-------|------|--------|
| Phase 1 | Frontend Router + Dashboard + KnowledgeBase + Role UI | 2-3 ngày |
| Phase 4 | CI/CD + Docs | 0.5-1 ngày |
| Phase 2 | 8D Case Backend + Frontend | 2-3 ngày |
| Phase 3 | Evaluation Lab | 1-2 ngày |
| Phase 5 | Testing + Polish | 1 ngày |
| **TOTAL** | | **7-10 ngày** |

---

## Ghi chú quan trọng

1. **Backend đang là Java Spring Boot** — IMPLEMENTATION_PLAN.md đề xuất migrate sang Python FastAPI nhưng hiện tại backend Java đã hoạt động tốt và có nhiều tính năng. Việc migrate là phạm vi lớn, chỉ nên làm nếu thực sự cần. Trước mắt tập trung hoàn thiện trên nền Java.

2. **Frontend đã có tất cả component** — Vấn đề chính là navigation (tab-based trong 1 App.tsx 621 dòng). Refactor sang React Router sẽ giải quyết.

3. **Agent Python đã có 4 connector** — Gmail, Google Drive, SharePoint, Slack. DataSources page frontend đã gọi API `/datasources`. Backend cũng đã có controller.

4. **8D Case và Evaluation** — Đây là 2 module backend thực sự CHƯA CÓ implementation hoàn chỉnh. Cần build từ entity → service → controller → frontend.

5. **Độ ưu tiên giảm dần** — Nếu thời gian hạn chế, tập trung Phase 1 (UX/UI) + Phase 4 (Docs/CI) trước, sau đó mới đến Phase 2, 3.