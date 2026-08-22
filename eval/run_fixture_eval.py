#!/usr/bin/env python3
"""Reproducible fixture benchmark.

End-to-end regression workflow:
  1. Register/login a throwaway evaluation user (owner isolation respected)
  2. Upload eval/fixtures/8d_failure_risk_fixture.txt as that user
  3. Run eval/eval.py against the owned document ID

Usage:
    python eval/run_fixture_eval.py \
        --base-url https://smart-doc-backend-h4mt.onrender.com/api \
        [--questions eval/agent_questions.json]

Credentials are created at runtime — no secrets are stored or printed.
Exit code: 0 only if the evaluation reports zero errors.
"""
import argparse
import importlib.util
import json
import pathlib
import sys
import time

import requests

HERE = pathlib.Path(__file__).resolve().parent
FIXTURE = HERE / "fixtures" / "8d_failure_risk_fixture.txt"


def load_eval_module():
    spec = importlib.util.spec_from_file_location("fixture_eval", HERE / "eval.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    ap = argparse.ArgumentParser(description="Run the fixture benchmark")
    ap.add_argument("--base-url", required=True,
                    help="Backend API base URL (includes /api context path)")
    ap.add_argument("--questions",
                    default=str(HERE / "agent_questions.json"))
    ap.add_argument("--output", default=str(HERE / "results" / "fixture_eval.json"))
    args = ap.parse_args()
    b = args.base_url.rstrip("/")

    s = requests.Session()

    def csrf():
        return s.get(f"{b}/api/csrf", timeout=60).json()["token"]

    # 1. Throwaway evaluation user
    u = f"fixtbench{int(time.time())}"
    h = {"X-XSRF-TOKEN": csrf()}
    s.post(f"{b}/auth/register", headers=h,
           json={"username": u, "email": f"{u}@test.local",
                 "password": "FixtureBench123!"}, timeout=120)
    r = s.post(f"{b}/auth/login", headers=h,
               json={"username": u, "password": "FixtureBench123!"}, timeout=120)
    jwt = r.json().get("token") or r.json().get("accessToken")
    if not jwt:
        print("FATAL: login failed", file=sys.stderr)
        return 1

    # 2. Upload fixture (owned by the evaluation user)
    r = s.post(f"{b}/documents/upload",
               headers={"Authorization": f"Bearer {jwt}",
                        "X-XSRF-TOKEN": csrf()},
               files={"file": (FIXTURE.name, FIXTURE.read_bytes(), "text/plain")},
               timeout=300)
    doc = r.json().get("documentId") if r.status_code == 200 else None
    if doc is None:
        print(f"FATAL: fixture upload failed (HTTP {r.status_code})", file=sys.stderr)
        return 1
    print(f"✅ Fixture uploaded: documentId={doc} (user={u})")

    # 3. Run the standard evaluator against the owned document
    eval_mod = load_eval_module()
    ns = argparse.Namespace(base_url=b, token=jwt, document_id=int(doc),
                            questions=args.questions, output=args.output,
                            mlflow=False, mlflow_uri="http://mlflow:5000")
    summary = eval_mod.run_evaluation(ns)
    errors = summary.get("error_count", 0)
    print(f"\nFIXTURE BENCHMARK: {'PASS' if errors == 0 else 'FAIL'} "
          f"(errors={errors}, results -> {args.output})")
    return 0 if errors == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
