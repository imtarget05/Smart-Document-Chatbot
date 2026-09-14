# Checklist — AI Opencode Fix Queue

> Priority-ordered list of concrete fixes. Each item maps to a real coverage
> gap or CI gap verified by running tests on 2026-09-02.

## Priority 1 — Frontend unit-test coverage gaps

These files have **0 or partial coverage** — tests exist for other components
but these were left behind (confirmed via `npx vitest run --coverage`).

- [ ] **`src/components/UserMenu.tsx` — 0% coverage**
  - File: 83 lines, 0 statements covered. Create `UserMenu.test.tsx`.
  - Test cases: click toggles dropdown open/closed; initials from username;
    role labels (ADMIN→"Quản trị viên", ENGINEER→"Kỹ sư", VIEWER→"Người xem");
    outside-click closes; logout calls `onLogout` + closes; `aria-expanded`
    reflects state.

- [ ] **`src/components/Sidebar.tsx` — 72.72% coverage** (lines 26-29, 80-108)
  - Uncovered: mobile overlay, document list rendering, selected-doc styling,
    upload button, new-chat+onClose.
  - Tests: empty state vs populated list; clicking doc calls `onSelectDoc`
    + `onClose`; upload button calls `onUploadClick`; new-chat calls
    `onNewChat` + `onClose`; overlay clicks `onClose`; `selectedDoc` highlight.

- [ ] **`src/pages/LoginPage.tsx` — 72.96% coverage** (lines 128-143, 152-206)
  - Uncovered: password-reset flow, Google OAuth login, auth-error paths.
  - Tests: empty-form validation; successful login POST; register mode POST;
    Google login sets `window.location.href`; forgot-password → reset flow;
    API error renders inline error.

- [ ] **`src/pages/ChatPage.tsx` — 74% coverage** (lines 242-347, 381-385)
  - Uncovered: streaming error state, document viewer open/close, upload
    error, file-upload handler.
  - Tests: SSE chunk streaming → final message; SSE `error` event → renders
    `❌ Error`; `uploadError` banner dismisses; file-input `onChange` → calls
    upload API; DocumentViewer opens with citation; DocumentViewer close
    clears `viewingSource`.

## Priority 2 — E2E tests not run in CI

- [ ] **Add Playwright E2E to CI pipeline**
  - Currently `.github/workflows/ci.yml` runs only `vitest` (unit) + `docker-build`.
  - 6 spec files exist in `frontend/e2e/` (16 tests): auth, chat-flow,
    chat-ui, documents, admin-ui, fullstack-smoke. Add a job that runs:
    `npx playwright test --project=chromium` after frontend build.
  - `chat-ui.spec.ts` is hermetic (uses `page.route` mocks) — safe in CI.
  - `fullstack-smoke.spec.ts` + `chat-flow.spec.ts` + `documents.spec.ts` +
    `admin-ui.spec.ts` hit live backend — gate on `E2E_API_URL` env var,
    skip in PRs, run in nightly/staging.

## Priority 3 — Agent tests not in CI

- [ ] **Add agent test job to CI**
  - `agent/tests/` has 213 pytest tests (all passing on 2026-09-02 via venv
    Python 3.12). No CI workflow runs them.
  - Add job: `pip install -r agent/requirements.txt + pytest` → 213 tests.
  - Currently `eval.yml` only runs `tests/test_grader.py` (offline grader
    unit tests), not the full agent suite.

## Priority 4 — Eval gaps (from `docs/eval_state.md`)

- [ ] **Live eval job in CI**
  - Only `--validate-only` and mock-local eval run in CI.
  - Plan: add `eval-live` job on staging schedule when cloud secrets available.

- [ ] **Golden reference dataset**
  - No semantic golden answers exist; grading is deterministic lexical only.
  - Action: curate 10-20 high-value Q&As with golden reference answers.

- [ ] **Wire LLM-judge into eval pipeline**
  - `eval/llm_judge.py` exists (Faithfulness, Relevance, Completeness, Tone)
    but is not invoked by `eval/agent_eval.py`.
  - Action: integrate `LLMJudge.evaluate_all()` post-run into agent eval.

## Priority 5 — Coverage threshold review

- [ ] **Raise frontend coverage thresholds**
  - Current `vite.config.ts`: lines 0.60, functions 0.60, branches 0.50,
    statements 0.60 — below the gaps in P1.
  - After fixing P1, bump to: lines 0.80, functions 0.80, branches 0.70.
