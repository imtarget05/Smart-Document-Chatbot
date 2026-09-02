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
- [x] Run all unit tests (vitest) — 56/56 pass
- [x] Run all E2E tests locally (playwright)
- [x] Run E2E against production URL (https://smart-doc-chatbot.pages.dev) — UI suites 18/18 pass
- [x] Deploy to Cloudflare Pages (auto via pages.yml on push to main)
- [x] Verify production URL works + serves new Google Material Design UI
- [x] Commit + push to origin/main (Cloudflare Pages auto-deploy)

## Notes
- `fullstack-smoke.spec.ts` (csrf → register → login → upload → ask) hits Render free-tier
  rate limiter; a transient `503 rate_limit_unavailable` (Redis backend down) can fail it
  during cold starts. Retry shortly; not a code defect.
- PGP/thumbnail coverage for new components (`AppBar`, `Sidebar`, `UserMenu`) is pending unit
  tests — add for full coverage.
