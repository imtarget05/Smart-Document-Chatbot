#!/usr/bin/env bash
#
# E2E curl smoke test — Smart Document Chatbot
#
# Verified live against backend on port 8082 (context-path /api).
# All paths below are CORRECT:
#   - Chat endpoints:  /api/chat/ask  and  /api/chat/ask-stream  (NOT /api/ask)
#   - Auth:            /api/auth/register , /api/auth/login
#   - Documents:       /api/documents/upload
#
# Auth note:
#   - JwtAuthenticationFilter accepts BOTH the `Authorization: Bearer <token>`
#     header AND the httpOnly `jwt_token` cookie -> header is the easy path for curl.
#   - CSRF is ignored for /auth/**, /documents/**, /chat/** (see SecurityConfig),
#     so no X-XSRF-TOKEN header is needed when using the Bearer header.
#   - Password must be 12-100 chars (AuthRequest @Size(min=12)) -> "admin" won't pass.
#   - No admin user is seeded by Flyway; register the user you want first.
#
# Requirements: curl, jq

set -euo pipefail

# Change to your running instance (E2E run used 8082; default is 8080).
BASE_URL="${BASE_URL:-http://localhost:8082}"

# ── 1. Register + login → get JWT token ───────────────────────────────────────
# Register first (idempotent-ish: will 400 if username already taken).
curl -s -X POST "$BASE_URL/api/auth/register" \
  -H 'Content-Type: application/json' \
  -d '{"username":"testuser","password":"testpassword123"}' >/dev/null || true

TOKEN=$(curl -s -X POST "$BASE_URL/api/auth/login" \
  -H 'Content-Type: application/json' \
  -d '{"username":"testuser","password":"testpassword123"}' | jq -r .token)

if [[ -z "$TOKEN" || "$TOKEN" == "null" ]]; then
  echo "ERROR: login failed — check credentials. (password must be 12-100 chars)" >&2
  exit 1
fi
echo "Token acquired (${#TOKEN} chars)"

# ── 2. Upload a document (PDF/DOCX/TXT) ───────────────────────────────────────
curl -s -X POST "$BASE_URL/api/documents/upload" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@/tmp/rag_demo.txt" | jq

# Note the returned documentId (e.g. 2) and pass it into the chat request below.

# ── 3. Chat (correct endpoint, sessionId required) ────────────────────────────
#    documentId given + keywords IN the document  -> strategy "direct" / "corrective"
curl -s -X POST "$BASE_URL/api/chat/ask" \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"sessionId":"test-session-1","documentId":2,"message":"Nội dung về <từ khóa có trong file> là gì?"}' \
  | jq '{ragStrategy, confidence, confidenceScore, documentId, sourceChunks, sources}'

#    Omit / null documentId  (or use keywords absent from the doc)
#     -> strategy "general_knowledge"  (correct CRAG fallback by design)
curl -s -X POST "$BASE_URL/api/chat/ask" \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"sessionId":"test-session-1","message":"...","documentId":null,"webSearch":false}' \
  | jq '{ragStrategy, confidence, confidenceScore, documentId}'

# ── 4. Streaming variant (SSE) ────────────────────────────────────────────────
#    Emits: event:metadata → event:chunk (xN) → event:complete
curl -N -X POST "$BASE_URL/api/chat/ask-stream" \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"sessionId":"test-session-2","documentId":2,"message":"..."}'
