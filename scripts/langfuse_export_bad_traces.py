#!/usr/bin/env python3
"""Export low-quality Langfuse traces for re-evaluation (Phase 3).

Pulls traces whose metadata indicates a failure mode (llmError set, or
strategy == no_evidence / general_knowledge, or low confidence) and writes
them to eval/results/ in the same shape eval.py consumes, so the eval
harness can re-run on real-world bad cases.

Usage:
  python scripts/langfuse_export_bad_traces.py \
      --host https://cloud.langfuse.com \
      --project-id <pid> \
      --out eval/results/bad_traces_$(date +%F).json \
      --from-date 2026-08-01

Auth: LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY env vars (Basic auth).
"""
from __future__ import annotations

import argparse
import base64
import datetime as dt
import json
import os
import sys

try:
    import requests
except ImportError:
    print("requests is required: pip install requests", file=sys.stderr)
    raise SystemExit(2)


def auth_header() -> str:
    pk = os.getenv("LANGFUSE_PUBLIC_KEY", "")
    sk = os.getenv("LANGFUSE_SECRET_KEY", "")
    if not pk or not sk:
        raise SystemExit("Set LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY")
    token = base64.b64encode(f"{pk}:{sk}".encode()).decode()
    return f"Basic {token}"


def list_traces(host: str, project_id: str, from_date: str, limit: int = 100):
    url = f"{host}/api/public/traces"
    params = {"pageSize": limit, "fromTimestamp": from_date}
    if project_id:
        params["projectId"] = project_id
    resp = requests.get(url, headers={"Authorization": auth_header()}, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json().get("data", [])


def get_trace(host: str, trace_id: str) -> dict:
    resp = requests.get(f"{host}/api/public/traces/{trace_id}",
                        headers={"Authorization": auth_header()}, timeout=30)
    resp.raise_for_status()
    return resp.json()


FAIL_STRATEGIES = {"no_evidence", "general_knowledge"}


def is_bad(trace: dict) -> tuple[bool, str]:
    meta = trace.get("metadata") or {}
    if meta.get("llmError"):
        return True, f"llm_error:{meta['llmError']}"
    strategy = meta.get("strategy")
    if strategy in FAIL_STRATEGIES:
        return True, f"strategy:{strategy}"
    conf = meta.get("confidence")
    if isinstance(conf, (int, float)) and conf < 0.45:
        return True, f"low_confidence:{conf}"
    return False, ""


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default=os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com"))
    ap.add_argument("--project-id", default=os.getenv("LANGFUSE_PROJECT_ID", ""))
    ap.add_argument("--from-date", default="2026-08-01")
    ap.add_argument("--out", required=True)
    ap.add_argument("--limit", type=int, default=200)
    args = ap.parse_args()

    traces = list_traces(args.host, args.project_id, args.from_date, args.limit)
    bad = []
    for t in traces:
        ok, reason = is_bad(t)
        if not ok:
            continue
        full = get_trace(args.host, t["id"])
        meta = full.get("metadata") or {}
        question = (full.get("input") or {}).get("query") or t.get("name") or ""
        bad.append({
            "trace_id": t["id"],
            "timestamp": t.get("timestamp"),
            "failure_reason": reason,
            "strategy": meta.get("strategy"),
            "confidence": meta.get("confidence"),
            "document_id": meta.get("documentId"),
            "query": question,
            "observations": [
                {"name": o.get("name"), "type": o.get("type"), "model": o.get("model")}
                for o in (full.get("observations") or [])
            ],
        })

    out = {"exported_at": dt.datetime.now().isoformat(), "count": len(bad), "traces": bad}
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"Wrote {len(bad)} bad traces -> {args.out}")


if __name__ == "__main__":
    main()
