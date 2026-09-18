#!/usr/bin/env python3
"""Show full sample answers + strategy/confidence distribution."""
import json
import sys
from collections import Counter

path = sys.argv[1] if len(sys.argv) > 1 else "eval/results/rag_30_trace.json"
t = json.load(open(path, encoding="utf-8"))["trace"]

print("strategy:", dict(Counter(x["rag_strategy_backend"] for x in t)))
print("confidence:", dict(Counter(x["confidence_backend"] for x in t)))
print()
for qid in ("A5", "U4", "C4"):
    x = next(i for i in t if i["id"] == qid)
    print(f"===== {qid} ({x['category']}) =====")
    print("Q:", x["question"])
    print("A:", (x["answer_from_backend"] or "")[:400])
    src = x["citations_backend"] or []
    print("citations:", [(c.get("sourceType"), str(c.get("score"))[:5])
                         for c in src][:3])
    print()
