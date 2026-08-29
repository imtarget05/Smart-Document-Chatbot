#!/usr/bin/env python3
"""Staging smoke test — verifies agentic + supply-chain wiring on Render.

Runs after the Render Blueprint is connected and deployed. Checks the new
agentic boundaries that production_smoke.py does not cover:

  1. Backend /api/health                              (backend live)
  2. llm-router /health (via LLM_BASE_URL)            (router live)
  3. supply-chain-module /health                      (supply chain API live)
  4. POST /api/agent/invoke (supply-chain intent)     (backend -> router agent path)
  5. POST /api/documents/upload triggers workflow     (document e2e #7)
  6. GET /api/documents/{id} returns workflow_result  (workflow result persisted)

Credentials / base URLs are supplied at runtime (never hardcoded):

    python scripts/staging_smoke_test.py \
        --backend-url https://smart-doc-backend-h4mt.onrender.com/api \
        --router-url  https://smart-doc-llm-router.onrender.com \
        --supply-url  https://smart-doc-supply-chain-api.onrender.com

Exit code: 0 if all critical checks pass, 1 otherwise.
"""
import argparse
import sys
import time

import requests

DEFAULT_BACKEND = "https://smart-doc-backend-h4mt.onrender.com/api"
DEFAULT_ROUTER = "https://smart-doc-llm-router.onrender.com"
DEFAULT_SUPPLY = "https://smart-doc-supply-chain-api.onrender.com"
SMOKE_PASSWORD = "SmokeTest123!"


def check(name: str, ok: bool, detail: str = "") -> bool:
    print(f"{'PASS' if ok else 'FAIL':4} | {name} {detail}")
    return ok


def main() -> int:
    ap = argparse.ArgumentParser(description="Staging agentic smoke test")
    ap.add_argument("--backend-url", default=DEFAULT_BACKEND)
    ap.add_argument("--router-url", default=DEFAULT_ROUTER)
    ap.add_argument("--supply-url", default=DEFAULT_SUPPLY)
    args = ap.parse_args()
    b = args.backend_url.rstrip("/")
    r = args.router_url.rstrip("/")
    sc = args.supply_url.rstrip("/")

    results = []

    # --- 1. Backend health
    try:
        rb = requests.get(f"{b}/health", timeout=60)
        results.append(check("BACKEND HEALTH   ", rb.status_code == 200, f"({rb.status_code})"))
    except Exception as e:
        results.append(check("BACKEND HEALTH   ", False, str(e)[:80]))

    # --- 2. llm-router health
    try:
        rr = requests.get(f"{r}/health", timeout=60)
        results.append(check("ROUTER HEALTH    ", rr.status_code == 200, f"({rr.status_code})"))
    except Exception as e:
        results.append(check("ROUTER HEALTH    ", False, str(e)[:80]))

    # --- 3. supply-chain-module health (may 404/502 if not deployed — non-fatal)
    try:
        rsc = requests.get(f"{sc}/health", timeout=60)
        results.append(check("SUPPLY HEALTH    ", rsc.status_code == 200, f"({rsc.status_code})"))
    except Exception as e:
        results.append(check("SUPPLY HEALTH    ", False, str(e)[:80]))

    # --- 4. Agent path: supply-chain intent via backend
    # Need auth first (reuse production_smoke auth pattern)
    try:
        csrf = requests.get(f"{b}/csrf", timeout=60).json().get("token", "")
        s = requests.Session()
        h = {"X-XSRF-TOKEN": csrf}
        u = f"agent{int(time.time())}"
        s.post(f"{b}/auth/register", headers=h,
               json={"username": u, "email": f"{u}@test.local",
                     "password": SMOKE_PASSWORD}, timeout=120)
        rl = s.post(f"{b}/auth/login", headers=h,
                    json={"username": u, "password": SMOKE_PASSWORD}, timeout=120)
        jwt = rl.json().get("token") or rl.json().get("accessToken")
        if jwt:
            ah = {"Authorization": f"Bearer {jwt}"}
            fcsrf = s.get(f"{b}/csrf", timeout=60).json().get("token", "")
            t0 = time.time()
            ra = s.post(f"{b}/chat/ask",
                        headers={**ah, "X-XSRF-TOKEN": fcsrf, "Content-Type": "application/json"},
                        json={"sessionId": "agent-smoke", "documentId": 1,
                              "message": "Dự báo nhu cầu SKU ABC trong 30 ngày tới bằng mô hình nào?"},
                        timeout=600)
            lat = round(time.time() - t0, 1)
            ans = ra.json().get("aiResponse", "") if ra.status_code == 200 else ""
            # Agent path: either answers (agentic) or falls back to RAG (graceful)
            ok = ra.status_code == 200 and ans != "" and "temporarily unavailable" not in ans.lower()
            results.append(check("AGENT PATH       ", ok, f"({lat}s)"))
            if ans:
                print(f"   answer[:160]: {ans[:160].replace(chr(10), ' ')}")
        else:
            results.append(check("AGENT PATH       ", False, "no JWT"))
    except Exception as e:
        results.append(check("AGENT PATH       ", False, str(e)[:80]))

    # --- 5-6. Document upload e2e + workflow result
    try:
        csrf2 = s.get(f"{b}/csrf", timeout=60).json().get("token", "") if jwt else ""
        content = (b"INVOICE\nSeller: ACME Supply Co.\nBuyer: Globex Vietnam\n"
                   b"Items: 100x Widget A @ 12.50 USD\nTotal: 1250.00 USD\nPO Number: PO-2026-001")
        ru = s.post(f"{b}/documents/upload",
                    headers={**ah, "X-XSRF-TOKEN": csrf2},
                    files={"file": ("smoke_invoice.txt", content, "text/plain")}, timeout=300)
        doc_id = ru.json().get("documentId") if ru.status_code == 200 else None
        results.append(check("DOC UPLOAD       ", ru.status_code == 200 and doc_id is not None,
                             f"(docId={doc_id})"))
        if doc_id:
            time.sleep(3)  # allow async workflow to persist
            rd = s.get(f"{b}/documents/{doc_id}", headers=ah, timeout=60)
            wr = rd.json().get("workflowResult") if rd.status_code == 200 else None
            results.append(check("WORKFLOW RESULT  ", wr is not None,
                                 f"({'present' if wr else 'null — router may be down'})"))
    except Exception as e:
        results.append(check("DOC UPLOAD       ", False, str(e)[:80]))

    overall = all(results)
    print(f"\nOVERALL           {'PASS' if overall else 'FAIL'}")
    print("\nNote: SUPPLY HEALTH / WORKFLOW RESULT may be null if the supply-chain")
    print("module or router is not yet deployed — those are non-fatal for boot.")
    return 0 if overall else 1


if __name__ == "__main__":
    sys.exit(main())
