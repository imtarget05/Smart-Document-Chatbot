# Evaluation & Production Verification Guide

This document describes the reproducible regression workflow for verifying a
deployment of Smart Document Chatbot.

There are two independent assets:

1. **Production smoke test** — verifies infrastructure boundaries
   (CSRF, JWT, owner isolation, backend → router auth, LLM response).
2. **Fixture benchmark** — verifies that the CRAG + retrieval + LLM pipeline
   answers correctly against a known synthetic evidence set.

> Architectural note: the fixture is a **regression-test asset**, not part of
> the production knowledge base.

---

## 1. Production smoke test

```bash
python scripts/production_smoke.py \
  --base-url https://<backend-host>/api
```

The script creates its own throwaway user and test document at runtime, so it
does not depend on pre-existing production state. It never prints secrets or
JWTs and exits non-zero on any critical failure.

Expected output:

```text
PASS | CSRF
PASS | JWT
PASS | DOC UPLOAD
PASS | OWNER ISOLATION
PASS | CHAT
PASS | ROUTER AUTH
PASS | LLM RESPONSE

OVERALL           PASS
```

Interpretation:

- `CHAT` FAIL with HTTP 403 → CSRF/session handling broken.
- `ROUTER AUTH` FAIL ("temporarily unavailable") → internal-token mismatch
  between `INTERNAL_SERVICE_TOKEN` (backend) and `ROUTER_INTERNAL_TOKEN`
  (router).
- Any HTTP 4xx/5xx → inspect backend logs before changing code.

## 2. Fixture benchmark

The benchmark uses `eval/fixtures/8d_failure_risk_fixture.txt` — a clearly
marked **synthetic** evidence set containing failures / root cause / 5 Whys /
8D / corrective actions / risk assessment / mitigation / preventive actions /
similarities-differences, matching `eval/agent_questions.json`.

One-command run (creates user, uploads fixture, evaluates):

```bash
python eval/run_fixture_eval.py \
  --base-url https://<backend-host>/api \
  --output eval/results/fixture_eval.json
```

Manual equivalent:

```bash
# 1. Create/use an evaluation user (register + login via /api/auth/*)
# 2. Upload the fixture: POST /api/documents/upload (multipart)
# 3. Note the returned documentId (owned by the evaluation user)
# 4. Run:
python eval/eval.py \
  --base-url https://<backend-host>/api \
  --token "$JWT" \
  --document-id <OWNED_DOCUMENT_ID> \
  --questions eval/agent_questions.json
```

## 3. Current baseline (Decision 7/8, production, commit ceee8e8)

```text
Questions:          3
HTTP success:       3/3
Retrieval accuracy: 100%
Answer correctness: 3/3
Hallucination rate: 0%
Errors:             0
Avg latency:        ~4.5 s
```

These numbers are the **observed baseline**, not hardcoded grading
requirements. If a legitimate model/retrieval change moves them, the
benchmark should expose the delta rather than silently adapt to it.

Known limitation: document retrieval is lexical (no stemming), so fixture
content must use the exact terminology the questions/grader expect
(e.g. both singular "risk" and plural "risks" forms).

## 4. Deployment verification workflow

```text
deploy
  ↓
python scripts/production_smoke.py      # infrastructure PASS/FAIL
  ↓
python eval/run_fixture_eval.py         # pipeline regression PASS/FAIL
  ↓
report results separately:
  - Infrastructure (HTTP/security boundaries)
  - Answer quality (retrieval + correctness + hallucination)
```
