# Production Redesign & Testing TODO

## Phase 0: Bug Fixes ✅
- [x] Fix `className` → `class` in `frontend/index.html`
- [x] Fix `tailwind.config.js` content path
- [x] Verify build + tests pass

## Phase 1: Design System Foundation ✅
- [x] Extend Tailwind config with Google Material Design tokens
- [x] Add CSS variables for colors, spacing, typography
- [x] Add Material animations (ripple, fade, slide)
- [x] Fix failing tests (LoginPage, ChatPage, App)

## Phase 2: Finalize LoginPage (Google-style) ✅
- [x] Review current WIP state of LoginPage
- [x] Complete Google-style layout (left panel + right panel)
- [x] Add responsive (hide left panel < 1024px)
- [x] Add loading states + password strength indicator
- [x] Add helper components (DocIcon, GoogleLogo, ErrorIcon, CheckIcon)
- [x] Use design tokens (google-blue, surface-dim, onsurface, outline, etc.)
- [x] Fix tests (getAllByText for duplicate text)
- [x] Verify build + tests pass

## Phase 3: New Layout Components ✅
- [x] Create `AppBar` — top navigation with logo, hamburger menu, user avatar
- [x] Create `Sidebar` — 280px drawer with New Chat, document list, upload button
- [x] Create `WelcomeScreen` — empty state with suggested prompts + upload CTA
- [x] Create `UserMenu` — dropdown with user info + logout
- [x] Verify build + tests pass

## Phase 4: Redesign ChatPage ✅
- [x] Integrate AppBar + Sidebar + WelcomeScreen
- [x] Always show input bar (not just when messages exist)
- [x] Material Design styling for messages area
- [x] FAB-style send button with Google blue
- [x] Upload error with Material banner
- [x] Vietnamese placeholders
- [x] Update tests for new layout
- [x] Verify build + tests pass

## Phase 5: Redesign Components ✅
- [x] `MessageBubble` — Material cards, user=Google blue, assistant=surface with avatar
- [x] `SourceCitations` — book icon, expandable Material cards with elevation
- [x] `EvidenceState` — Material banner with SVG icons, color-coded (green/yellow/red)
- [x] `DocumentViewer` — Material side sheet, slide-in animation, avatar + gradient
- [x] `ErrorBoundary` — Material dialog with error icon, Vietnamese
- [x] Verify build + tests pass

## Phase 6: E2E Test Suite ✅
- [x] Expand `auth.spec.ts` — 5 UI tests (login, register, validation, invalid creds, forgot password)
- [x] Create `chat-flow.spec.ts` — 2 UI + 3 API-contract tests
- [x] Create `documents.spec.ts` — API auth guards + UI placeholders
- [x] Create `admin-ui.spec.ts` — admin guard + UI contract tests
- [x] Create `chat-ui.spec.ts` — 4 tests (logged-in UI with mocked backend)
- [x] Extend `playwright.config.ts` — `E2E_BASE_URL` to run against production (skips local webServer)
- [x] Use Vietnamese text with diacritics + `getByPlaceholder` for floating-label inputs
- [x] Verify 13/13 UI E2E tests pass against production

## Phase 7: Production Deployment ✅
- [x] Run all unit tests (vitest) — 96/96 pass (56 original + 40 new from UserMenu/Sidebar/ChatPage/LoginPage test expansion)
- [x] Run hermetic E2E tests locally (playwright) — 12/12 pass (auth 5 + chat-ui 4 + admin-ui 3)
- [x] Run E2E against production URL (https://smart-doc-chatbot.pages.dev) — UI suites 18/18 pass
- [x] Deploy to Cloudflare Pages (auto via pages.yml on push to main)
- [x] Verify production URL works + serves new Google Material Design UI
- [x] Commit + push to origin/main (Cloudflare Pages auto-deploy)

## Verification (2026-09-02)

All phases verified by running tests + build:

| Suite | Before | After | Status |
|-------|--------|-------|--------|
| Frontend unit (vitest) | 56 pass | 96 pass | ✅ |
| Frontend E2E (hermetic) | — | 12/12 pass | ✅ |
| Frontend build | ✅ | ✅ | ✅ |
| Backend (Maven JDK17) | 259 pass | 259 pass | ✅ |
| Agent (pytest venv) | 213 pass | 213 pass | ✅ |
| Coverage (lines) | 60% gate | 80% gate | ✅ |

### CI pipeline (.github/workflows/ci.yml)
- Added `frontend-e2e` job: runs 4 hermetic `chat-ui.spec.ts` tests always;
  fullstack/API E2E opt-in via `E2E_API_URL` secret.
- Added `agent-test` job: runs 213 pytest tests.
- `docker-build` + `deploy` now depend on `frontend-e2e` + `agent-test`.
- Stale comment "(lines 0.60)" → fixed to "(lines 0.80, branches 0.70)".

## Phase 8: Agentic Features (Chat Integration) ✅
- [x] Add agent mode toggle (RAG vs Agent) in ChatPage input bar
- [x] Backend: `ChatService.processQueryStream` supports explicit `mode=agent` bypassing CRAG
- [x] Backend: `ChatResponse` includes `agentType` badge for agent responses
- [x] Frontend: Agent badge renders on messages processed by multi-agent orchestrator
- [x] Frontend: SSE streaming handles agent events (metadata with `agentType`, `chunk`, `complete`)
- [x] Tests: Agent mode toggle, agent badge rendering, mode=agent request payload

## Phase 9: Agent Infrastructure ✅
- [x] CI: Added `agent-test` job (213 pytest tests) to CI pipeline
- [x] CI: Added `frontend-e2e` job (hermetic Playwright tests)
- [x] CI: `docker-build` + `deploy` depend on `frontend-e2e` + `agent-test`
- [x] Eval: `eval/golden_dataset.json` with 12 golden reference Q&As for LLM-judge
- [x] Eval: `eval/agent_eval.py` wired with LLM-judge (`--llm-judge` / `--llm-judge-mock`)
- [x] Eval: `eval/agent_eval.py` outputs faithfulness, relevance, completeness, tone scores
- Root cause of the transient 503s: the rate-limiter was fail-closed when Redis was
  absent (`RateLimitInterceptor` returned 503 `rate_limit_unavailable`). Fixed by adding
  an in-memory fallback store (`InMemoryRateLimitStore`, `@ConditionalOnMissingBean`) so a
  Redis outage degrades to per-instance throttling instead of taking the whole API offline.
  Backend now returns 429 when over the limit, never 503.
- Also fixed a deploy blocker: `OAuth2Config` built a Google `ClientRegistration` via
  issuerUri()` without explicit endpoints -> `authorizationUri cannot be empty` -> app
  crashed at startup. Now sets explicit Google endpoints + wraps build in try/catch.
- E2E API auth-guard tests use `fetch(url, { redirect: 'manual' })` because Playwright's
  `page.request` follows the Spring Security 302 -> login redirect, masking whether an
  endpoint is actually protected.
- Unit tests added for `UserMenu` (13 tests), `Sidebar` (14 tests), expanded
  `ChatPage` (8 tests) and `LoginPage` (16 tests). Coverage now 100% on all
  components except `ChatPage.tsx` (84.75% — streaming-error + document-viewer
  paths) and `index.tsx` (entry point, intentionally untested).
- `eval/golden_dataset.json` created with 12 golden reference Q&As (semantic
  grounding for LLM-judge supplement). LLM-judge wired into `eval/agent_eval.py`
  via `--llm-judge` / `--llm-judge-mock` flags.
