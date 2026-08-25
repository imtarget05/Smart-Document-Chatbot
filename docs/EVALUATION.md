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

---

## Grading Contract v2

The evaluator supports two grading modes, selected per question:

### Legacy keyword mode (default, unchanged)

When a question only defines `expected_answer_contains`, grading is unchanged:
case-insensitive substring match, PASS when at least one keyword is found.

This mode is kept for backward compatibility with existing question files.

### Structured concept mode (opt-in)

Questions can define structured concepts — either inline via
`expected_concepts` on the question object, or through the side file
`eval/concepts_overrides.json` (maps `question_id` → concepts). The side
file keeps "question definition" separate from "grading hints".

```json
{
  "agent-003": {
    "expected_concepts": [
      {"concept": "compares failure causes",
       "forms": ["similarities", "failure causes", "root cause", "caused by"]},
      {"concept": "compares mitigation actions",
       "forms": ["differences", "mitigation actions", "corrective action", "preventive action"]}
    ]
  }
}
```

Matching rules:

- Answers are normalized: lowercase, whitespace/punctuation collapse,
  simple plural collapse (`risks→risk`, `differences→difference`,
  `actions→action`, ...). No NLP stemmer, no external dependencies.
- A concept is **covered** when at least one approved surface form appears.
- `answer_correct = (concepts_covered == concepts_expected)` — AND logic,
  not OR. This is stricter than legacy mode and prevents false positives
  such as *"Both documents discuss completely unrelated issues"*.

Structured output adds per-question fields: `concepts_expected`,
`concepts_covered`, `concept_details`, and `evidence_supported`
(sources present and RAG strategy is not `no_evidence`).

Three distinct metrics are reported separately and must not be conflated:

| Metric | Meaning |
|---|---|
| `retrieval_success` | expected source keywords found in retrieved chunks |
| `evidence_supported` | retrieval produced usable evidence for answering |
| `answer_correct` | all required concepts covered in the answer |

### Why exact keyword matching was insufficient (Q3 case study)

Decision 9 showed Q3 ("Compare these documents...") produced semantically
correct answers in 10/10 production runs, but the lexical grader passed
only 5/10. The LLM alternated between section headings
(`Similarities / Differences` → pass) and question-structured headings
(`Failure Causes / Mitigation Actions` → false negative). Concept-based
grading accepts both phrasings while still failing answers that lack an
actual comparison of both required aspects.

### Limitations

**This is deterministic concept coverage, NOT semantic LLM judging.**
It does not understand negation ("there are no differences" may still
match the form "difference"), deep semantics, or entailment. Surface-form
groups are human-curated per question. If true semantic evaluation is
needed later, it should be a separate decision (e.g., LLM-as-judge or
embedding similarity) — deliberately excluded here to keep CI
reproducible, dependency-free, and deterministic.

### Regression testing instructions

```bash
# Offline grader unit tests (no backend/LLM needed)
python3 -m pytest tests/test_grader.py -v

# Full fixture benchmark against an environment
python eval/run_fixture_eval.py --base-url "$BASE_URL"
```

Baseline expectations: HTTP 3/3, Retrieval 100%, Errors 0;
answer correctness should be read against concept coverage detail.
