#!/usr/bin/env python3
# Inspect rag_30 trace: counts, per-field fill-rate, sample rows.
import json
import sys
from collections import Counter

path = sys.argv[1] if len(sys.argv) > 1 else "eval/results/rag_30_trace_mock.json"
d = json.load(open(path, encoding="utf-8"))
t = d["trace"]
print("meta:", {k: d["meta"][k] for k in ("base_url", "document_id", "count")})
print("categories:", dict(Counter(x["category"] for x in t)))
answered = sum(1 for x in t if x["answer_from_backend"])
print("answered non-null:", answered, "/", len(t))
print("missing confidence:", sum(1 for x in t if not x["confidence_backend"]))
lat = [x["latency_ms"] for x in t]
print(f"latency ms: min={min(lat)} avg={sum(lat)//len(lat)} max={max(lat)}")
print()
for qid in ("A1", "U1", "C1"):
    x = next(i for i in t if i["id"] == qid)
    print(qid, "| conf:", x["confidence_backend"],
          "| strategy:", x["rag_strategy_backend"],
          "| ans:", (x["answer_from_backend"] or "")[:90])
    print("   citations:", len(x["citations_backend"] or []),
          "| chunks:", (x["source_chunks_backend"] or "")[:60])
