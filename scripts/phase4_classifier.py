#!/usr/bin/env python3
"""Phase 4 — Trace classifier for analyzing Langfuse traces (offline/test mode).

Classifies a trace.json (exported by langfuse_export_bad_traces.py or a
hand-crafted test file) into failure categories:

  - retrieval_weak : low confidence + poor chunk retrieval evidence
  - hallucination   : LLM generated content with no cited source
  - wrong_tool     : LLM error / circuit breaker / router failure
  - direct_ok      : trace passed normal path (for comparison)

Usage (offline, no Langfuse key needed):

  python scripts/phase4_classifier.py eval/results/bad_traces_2026-08-26.json \
      --out eval/results/classification_report.json

The classifier uses the observation tree already attached to each trace
(retrieve_chunks, generate_answer, ...) so it never needs to contact
Langfuse. It only needs the exported JSON.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from dataclasses import dataclass, field
from typing import Any

try:
    import yaml  # optional: nice formatting for report
except Exception:  # pragma: no cover
    yaml = None


# ------------------------------------------------------------------
# Trace model (decoded from exported JSON)
# ------------------------------------------------------------------

@dataclass
class TraceEvent:
    name: str
    kind: str  # "SPAN" | "GENERATION" | "TRACE"
    model: str | None = None
    output: str | None = None
    input: str | None = None
    status: str | None = None
    latency_ms: int | None = None
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ClassifiedTrace:
    trace_id: str
    query: str
    strategy: str
    confidence: float | None
    document_id: int | None
    category: str
    reason: str
    suggestions: list[str]
    events: list[TraceEvent] = field(default_factory=list)
    score: float = 0.0  # 0..1, higher = more concerning


# ------------------------------------------------------------------
# Classification logic
# ------------------------------------------------------------------

CATEGORIES = {
    "retrieval_weak": "Retrieval stage brought back irrelevant/empty context",
    "hallucination":   "LLM answered from general knowledge without grounding",
    "wrong_tool":      "LLM/router/circuit failure prevented a valid answer",
    "direct_ok":       "Normal direct path (for comparison / golden traces)",
}


def classify(events: list[TraceEvent], strategy: str, confidence: float | None) -> tuple[str, str, list[str], float]:
    """
    Return (category, reason, suggestions, concern_score).

    concern_score: 0..1 where 0 = healthy, 1 = strongly suggest action.
    """
    suggestions: list[str] = []
    score = 0.0

    # Collect retrieval & generation span facts
    retrieval = [e for e in events if e.name and "retrieve" in e.name.lower()]
    gen_events = [e for e in events if e.kind == "GENERATION" and e.name and "generate" in e.name.lower()]
    judge = [e for e in events if e.name and "judge" in e.name.lower()]
    web = [e for e in events if e.name and "web" in e.name.lower()]

    # --- LLM/router failure paths ---
    llm_errors = [e for e in events if e.error] + [
        e for e in gen_events if e.status and e.status != "COMPLETED"
    ]
    circuit_events = [e for e in events if e.name and ("circuit" in e.name.lower() or "fallback" in e.name.lower())]

    if llm_errors or circuit_events:
        reason = "LLM or router failure"
        cat = "wrong_tool"
        if llm_errors:
            reason += f": {llm_errors[0].error}"
        score = 0.8
        suggestions = [
            "Circuit breaker open or LLM returned invalid structure — enable local Ollama fallback (qwen3:8b)",
            "If transient Cloudflare Workers AI error, request retry loop already in place; verify on staging",
        ]
        return cat, reason, suggestions, score

    # --- Retrieval weak paths ---
    low_confidence = confidence is not None and confidence < 0.35
    empty_retrieval = retrieval and all(
        (e.output is None or e.output.strip() == "") for e in retrieval
    )
    # Chunk count in metadata: metadata["chunkCount"] = 0 means nothing retrieved.
    zero_chunk = retrieval and all(
        e.metadata.get("chunkCount", 1) == 0 for e in retrieval
    )

    # Also tag when strategy explicitly says no_evidence / general_knowledge
    abstain_strategies = {"no_evidence", "general_knowledge"}

    if low_confidence or empty_retrieval or strategy in abstain_strategies:
        reason_parts = []
        if strategy in abstain_strategies:
            reason_parts.append(f"strategy={strategy}")
        if low_confidence:
            reason_parts.append(f"confidence={confidence}")
        if empty_retrieval:
            reason_parts.append("retrieval returned empty context")
        reason = "; ".join(reason_parts) or "retrieval did not provide grounded context"
        cat = "retrieval_weak"
        score = 0.5 if low_confidence else 0.7
        suggestions = [
            "Retrieval returned weak/nil context — review chunking strategy and metadata filter",
            "Consider embedding model upgrade (bge-base-en is English only; Vietnamese docs need vi embedding)",
            "If strategy no_evidence, check whether document content actually covers the query topic",
        ]
        if low_confidence:
            suggestions.append(
                "Confidence below gate (0.35) — review lexical score + bigram bonus in LegalQueryNormalizer"
            )
        return cat, reason, suggestions, score

    # --- Hallucination / general_knowledge used ---
    if strategy == "general_knowledge" or any(
        (e.output and e.input and "could not generate" in (e.output or "").lower()) for e in gen_events
    ):
        reason = "LLM answered from general knowledge / anti-hallucination gate triggered"
        cat = "hallucination"
        score = 0.6
        suggestions = [
            "Diagnostic: confidence gate failed; repair retrieval (chunking, filter) before adopting general_knowledge",
            "If content exists in doc but retrieval missed it, tune top-k / lexical post-filter",
        ]
        return cat, reason, suggestions, score

    # --- Direct / corrective OK (golden trace) ---
    return "direct_ok", "No failure detected — trace completed normally", [], 0.0


# ------------------------------------------------------------------
# Helpers to decode Langfuse observation dicts into TraceEvent
# ------------------------------------------------------------------

def decode_trace(trace: dict[str, Any]) -> ClassifiedTrace:
    tid = trace.get("trace_id") or trace.get("id") or "unknown"
    query = trace.get("query") or (trace.get("input") or {}).get("query") or ""
    strategy = (trace.get("metadata") or {}).get("strategy") or "unknown"
    confidence = (trace.get("metadata") or {}).get("confidence")
    try:
        confidence = float(confidence) if confidence is not None else None
    except (ValueError, TypeError):
        confidence = None
    doc_id = (trace.get("metadata") or {}).get("documentId")
    try:
        doc_id = int(doc_id) if doc_id is not None else None
    except (ValueError, TypeError):
        doc_id = None

    # Decode observations into TraceEvent list
    evs: list[TraceEvent] = []
    for obs in (trace.get("observations") or []):
        name = obs.get("name") or ""
        evt = TraceEvent(
            name=name,
            kind=obs.get("type") or "SPAN",
            model=obs.get("model"),
            output=obs.get("output"),
            input=obs.get("input"),
            status=obs.get("status"),
            latency_ms=None,
            error=None,
        )
        # Try to extract latency from observation metadata or name suffix
        meta = obs.get("metadata") or {}
        if "latencyMs" in meta:
            try:
                evt.latency_ms = int(meta["latencyMs"])
            except (ValueError, TypeError):
                pass
        evt.metadata = {k: v for k, v in meta.items() if k != "error"}
        if "error" in meta:
            evt.error = meta["error"]
        evs.append(evt)

    return ClassifiedTrace(
        trace_id=tid,
        query=query,
        strategy=strategy,
        confidence=confidence,
        document_id=doc_id,
        category="",
        reason="",
        suggestions=[],
        events=evs,
    )


# ------------------------------------------------------------------
# Report generation
# ------------------------------------------------------------------

def build_report(classified: list[ClassifiedTrace]) -> dict[str, Any]:
    total = len(classified)
    by_cat: Counter[str] = Counter()
    reasons: Counter[str] = Counter()
    strategies: Counter[str] = Counter()
    queries: list[str] = []
    cat_stats: dict[str, dict[str, Any]] = {}

    for t in classified:
        by_cat[t.category] += 1
        if t.reason:
            reasons[t.reason] += 1
        strategies[t.strategy] += 1
        if t.query:
            queries.append(t.query)

    # Per-category stats (confidence distribution, example queries)
    for cat in CATEGORIES:
        cat_traces = [t for t in classified if t.category == cat]
        cat_stats[cat] = {
            "count": len(cat_traces),
            "pct": round(len(cat_traces) / total * 100, 2) if total else 0,
            "examples": [t.query for t in cat_traces[:5]],
            "suggestions": sorted({s for t in cat_traces for s in t.suggestions}),
            "strategies": dict(Counter(t.strategy for t in cat_traces)),
        }

    return {
        "report_at": __import__("datetime").datetime.now().isoformat(),
        "total_traces": total,
        "by_category": {cat: by_cat.get(cat, 0) for cat in CATEGORIES},
        "by_category_pct": {cat: round(by_cat.get(cat, 0) / total * 100, 2) if total else 0 for cat in CATEGORIES},
        "reasons": dict(reasons.most_common()),
        "strategy_distribution": dict(strategies),
        "per_category": cat_stats,
        "classifications": [
            {
                "trace_id": t.trace_id,
                "query": t.query,
                "strategy": t.strategy,
                "confidence": t.confidence,
                "document_id": t.document_id,
                "category": t.category,
                "reason": t.reason,
                "suggestions": t.suggestions,
            }
            for t in classified
        ],
    }


def print_report(report: dict[str, Any]) -> None:
    """Pretty-print the report to stdout (YAML if available, else JSON)."""
    if yaml:
        print(yaml.dump(report, default_flow_style=False, sort_keys=False))
    else:
        print(json.dumps(report, indent=2, ensure_ascii=False))


# ------------------------------------------------------------------
# CLI
# ------------------------------------------------------------------

def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("input", help="JSON trace file exported by langfuse_export_bad_traces.py")
    ap.add_argument("--out", help="Write classification report JSON to this path")
    args = ap.parse_args()

    with open(args.input, "r", encoding="utf-8") as f:
        raw = json.load(f)

    # Accept either langfuse_export_bad_traces.py output ({"traces": [...]})
    # or a raw list of trace objects.
    traces: list[dict[str, Any]]
    if isinstance(raw, dict) and "traces" in raw:
        traces = raw["traces"]
    elif isinstance(raw, list):
        traces = raw
    else:
        print("Unrecognized input format; expected a list or {'traces': [...]}", file=sys.stderr)
        sys.exit(2)

    if not traces:
        print("No traces found in input file", file=sys.stderr)
        sys.exit(0)

    classified: list[ClassifiedTrace] = []
    for trace in traces:
        t = decode_trace(trace)
        cat, reason, sugg, score = classify(t.events, t.strategy, t.confidence)
        t.category = cat
        t.reason = reason
        t.suggestions = sugg
        t.score = score
        classified.append(t)

    report = build_report(classified)
    print_report(report)

    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        print(f"\nReport written to {args.out}")


if __name__ == "__main__":
    main()
