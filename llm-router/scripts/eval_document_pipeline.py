#!/usr/bin/env python3
"""Eval pipeline (Phase 3): so extracted data vs ground truth.

Metrics: Schema Accuracy (field-level precision/recall trên schema chuẩn),
Value IoU (overlap field values), Match Accuracy (PO↔Invoice), Latency.

Usage:
    python scripts/eval_document_pipeline.py samples/ground_truth.json
Ground truth format: [{"text": ..., "filename": ..., "doc_type": ...,
                       "expected_fields": {...},
                       "counterpart_fields": {...} (optional)}]
"""

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agent.document_graph import run_document_workflow  # noqa: E402


def _norm(value):
    return str(value or "").strip().lower()


def evaluate_sample(sample: dict) -> dict:
    start = time.perf_counter()
    result = run_document_workflow(
        text=sample.get("text", ""),
        filename=sample.get("filename", ""),
        counterpart_fields=sample.get("counterpart_fields"),
    )
    latency = time.perf_counter() - start

    expected = sample.get("expected_fields", {})
    extracted = result.get("fields", {})
    schema = result.get("schema_mapping", {}).get("schema", [])

    # Value IoU: |expected ∩ extracted| / |expected ∪ extracted| theo field name
    union = set(expected) | set(extracted)
    inter = {k for k in expected if k in extracted and _norm(expected[k]) == _norm(extracted[k])}
    value_iou = len(inter) / len(union) if union else 1.0

    # Schema accuracy: fields bắt buộc của schema được extract đúng
    schema_hits = sum(1 for k in schema if k in extracted and k in expected
                      and _norm(expected[k]) == _norm(extracted[k]))
    schema_total = sum(1 for k in schema if k in expected)
    schema_accuracy = schema_hits / schema_total if schema_total else 0.0

    # Doc type
    type_correct = result.get("doc_type") == sample.get("doc_type")

    # Match accuracy (nếu sample có expected match status)
    match_correct = True
    if "expected_match_status" in sample:
        match_correct = result.get("match_status") == sample["expected_match_status"]

    return {
        "filename": sample.get("filename", ""),
        "type_correct": type_correct,
        "value_iou": value_iou,
        "schema_accuracy": schema_accuracy,
        "match_correct": match_correct,
        "latency_s": round(latency, 3),
        "precision_at_schema": round(schema_hits / len(schema), 2) if schema else 0.0,
    }


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    samples = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    reports = [evaluate_sample(s) for s in samples]

    n = len(reports) or 1
    summary = {
        "samples": len(reports),
        "doc_type_accuracy": round(sum(r["type_correct"] for r in reports) / n, 3),
        "mean_value_iou": round(sum(r["value_iou"] for r in reports) / n, 3),
        "mean_schema_accuracy": round(sum(r["schema_accuracy"] for r in reports) / n, 3),
        "match_accuracy": round(sum(r["match_correct"] for r in reports) / n, 3),
        "latency_p50_s": round(sorted(r["latency_s"] for r in reports)[len(reports) // 2], 3) if reports else 0,
    }
    print(json.dumps({"summary": summary, "details": reports}, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())