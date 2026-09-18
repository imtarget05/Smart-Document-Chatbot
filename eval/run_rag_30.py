#!/usr/bin/env python3
"""RAG acceptance eval: fixture upload + 30-question trace.

Pipeline: register -> login -> CSRF -> upload fixture -> 30x /chat/ask ->
trace JSON at eval/results/rag_30_trace.json with per-question backend fields
plus expected_* and empty manual-grading placeholders.

Usage:
    python eval/run_rag_30.py --base-url https://HOST/api
"""
import argparse
import json
import pathlib
import sys
import time
import uuid

import requests

HERE = pathlib.Path(__file__).resolve().parent
FIXTURE = HERE / "fixtures" / "rag_nghithu_fixture.txt"
QUESTIONS = HERE / "rag_30_questions.json"
OUTPUT = HERE / "results" / "rag_30_trace.json"


def flatten_questions(data: dict) -> list:
    """answered/unanswerable/conflict -> ordered list of 30 dicts with category."""
    out = []
    for category in ("answered", "unanswerable", "conflict"):
        for q in data.get(category, []):
            q = dict(q)
            q["category"] = category
            out.append(q)
    return out


def authenticate(base: str) -> tuple:
    """Register throwaway user, login, return (session, headers, username)."""
    s = requests.Session()
    u = f"rag30{int(time.time())}"
    csrf = csrf_token(s, base)
    reg = s.post(f"{base}/auth/register", headers={"X-XSRF-TOKEN": csrf}, json={
        "username": u, "email": f"{u}@test.local", "password": "RagBench123!",
    }, timeout=120)
    if reg.status_code not in (200, 201):
        print(f"register failed: {reg.status_code} {reg.text[:200]}", file=sys.stderr)
    r = s.post(f"{base}/auth/login", headers={"X-XSRF-TOKEN": csrf_token(s, base)},
               json={"username": u, "password": "RagBench123!"}, timeout=120)
    if r.headers.get("content-type", "").startswith("application/json"):
        token = r.json().get("token") or r.json().get("accessToken")
    else:
        token = None
        print(f"login non-JSON: {r.status_code} {r.text[:200]}", file=sys.stderr)
    if not token:
        raise SystemExit(f"FATAL: login failed {r.status_code}: {r.text[:300]}")
    return s, {"Authorization": f"Bearer {token}"}, u


def csrf_token(s: requests.Session, base: str) -> str:
    return s.get(f"{base}/csrf", timeout=60).json()["token"]


def upload(s: requests.Session, base: str, auth: dict) -> int:
    """Upload the fixture document; retry transient failures."""
    for attempt in range(1, 4):
        try:
            h = dict(auth)
            h["X-XSRF-TOKEN"] = csrf_token(s, base)
            r = s.post(f"{base}/documents/upload", headers=h,
                       files={"file": (FIXTURE.name, FIXTURE.read_bytes(),
                                       "text/plain")},
                       timeout=300)
            doc = r.json().get("documentId") if r.status_code == 200 else None
            if doc is not None:
                return int(doc)
            print(f"upload attempt {attempt}: {r.status_code} {r.text[:200]}",
                  file=sys.stderr)
        except requests.RequestException as exc:
            print(f"upload attempt {attempt} failed: {exc}", file=sys.stderr)
        time.sleep(10 * attempt)
    raise SystemExit("FATAL: fixture upload failed after retries")


def ask(s: requests.Session, base: str, auth: dict, doc_id: int,
        message: str) -> tuple:
    """POST /chat/ask; return (response_json_or_None, latency_ms)."""
    payload = {"sessionId": str(uuid.uuid4()), "documentId": doc_id,
               "message": message, "mode": "rag"}
    h = dict(auth)
    h["X-XSRF-TOKEN"] = csrf_token(s, base)
    t0 = time.time()
    try:
        r = s.post(f"{base}/chat/ask", headers=h, json=payload, timeout=300)
        latency = int((time.time() - t0) * 1000)
        body = r.json() if r.status_code == 200 else None
        if body is None:
            print(f"  ask {r.status_code}: {r.text[:150]}", file=sys.stderr)
        return body, latency
    except requests.RequestException as exc:
        latency = int((time.time() - t0) * 1000)
        print(f"  ask error: {exc}", file=sys.stderr)
        return None, latency


def main() -> int:
    ap = argparse.ArgumentParser(description="Run the 30-question RAG eval")
    ap.add_argument("--base-url", required=True,
                    help="Backend API base URL (includes /api)")
    ap.add_argument("--output", default=str(OUTPUT))
    args = ap.parse_args()
    base = args.base_url.rstrip("/")

    data = json.loads(QUESTIONS.read_text(encoding="utf-8"))
    questions = flatten_questions(data)
    if len(questions) != 30:
        raise SystemExit(f"FATAL: expected 30 questions, got {len(questions)}")

    s, auth, user = authenticate(base)
    print(f"logged in as {user}")
    doc_id = upload(s, base, auth)
    print(f"fixture uploaded: documentId={doc_id}")

    trace = []
    for q in questions:
        print(f"asking {q['id']} ({q['category']}) ...", flush=True)
        body, latency = ask(s, base, auth, doc_id, q["question"])
        body = body or {}
        trace.append({
            "id": q["id"],
            "category": q["category"],
            "question": q["question"],
            "answer_from_backend": body.get("aiResponse"),
            "citations_backend": body.get("sources"),
            "source_chunks_backend": body.get("sourceChunks"),
            "confidence_backend": body.get("confidence"),
            "confidence_score_backend": body.get("confidenceScore"),
            "rag_strategy_backend": body.get("ragStrategy"),
            "latency_ms": latency,
            "expected_source_keywords": q.get("expected_source_keywords"),
            "expected_section": q.get("expected_section"),
            "expected_answer_hint": q.get("expected_answer_hint"),
            "conflict_note": q.get("conflict_note"),
            "result_manual": "",
            "notes_manual": "",
        })
        time.sleep(1)

    out = pathlib.Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({
        "meta": {"base_url": base, "document_id": doc_id, "user": user,
                 "fixture": FIXTURE.name, "count": len(trace),
                 "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z")},
        "trace": trace,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"trace saved: {out} ({len(trace)} items)")
    return 0


if __name__ == "__main__":
    sys.exit(main())