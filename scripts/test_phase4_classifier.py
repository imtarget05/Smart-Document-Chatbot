#!/usr/bin/env python3
"""Unit tests for the Phase 4 trace classifier."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import textwrap

import pytest

# Use the classifier module directly (same dir as this file).
sys.path.insert(0, "scripts")
import phase4_classifier as clf


# ------------------------------------------------------------------
# Fixture traces
# ------------------------------------------------------------------

GOOD_DIRECT_TRACE = {
    "trace_id": "trace-001",
    "query": "Quyền của người kiểm thử là gì",
    "strategy": "direct",
    "confidence": 0.78,
    "document_id": 12,
    "observations": [
        {
            "name": "retrieve_chunks",
            "type": "SPAN",
            "model": None,
            "metadata": {"chunkCount": 2, "latencyMs": 12},
            "output": "Điều 2. Người kiểm thử có quyền chạy bộ kiểm thử.",
        },
        {
            "name": "generate_answer",
            "type": "GENERATION",
            "model": "llama-3.3-70b",
            "metadata": {"latencyMs": 1800},
            "output": "Người kiểm thử có quyền chạy bộ kiểm thử theo Điều 2.",
        },
    ],
}


BAD_RETRIEVAL_TRACE = {
    "trace_id": "trace-002",
    "query": "Tại sao dự án này dùng Spring Boot",
    "strategy": "no_evidence",
    "confidence": 0.12,
    "document_id": 12,
    "observations": [
        {
            "name": "retrieve_chunks",
            "type": "SPAN",
            "model": None,
            "metadata": {"chunkCount": 0, "latencyMs": 8},
            "output": "",
        },
    ],
}


BAD_HALLUCINATION_TRACE = {
    "trace_id": "trace-003",
    "query": "Framework nào dùng cho frontend",
    "strategy": "general_knowledge",
    "confidence": 0.41,
    "document_id": 12,
    "observations": [
        {
            "name": "retrieve_chunks",
            "type": "SPAN",
            "model": None,
            "metadata": {"chunkCount": 1, "latencyMs": 10},
            "output": "Backend dùng Spring Boot.",
        },
        {
            "name": "generate_answer",
            "type": "GENERATION",
            "model": "llama-3.3-70b",
            "metadata": {"latencyMs": 2100},
            "output": "Smart Document Chatbot dùng React cho frontend.",
        },
    ],
}


BAD_LLM_FAILURE_TRACE = {
    "trace_id": "trace-004",
    "query": "Điều 5 nói về gì",
    "strategy": "direct",
    "confidence": 0.91,
    "document_id": 12,
    "observations": [
        {
            "name": "retrieve_chunks",
            "type": "SPAN",
            "model": None,
            "metadata": {"chunkCount": 1, "latencyMs": 10},
            "output": "Điều 5: Trách nhiệm bồi thường.",
        },
        {
            "name": "generate_answer",
            "type": "GENERATION",
            "model": "llama-3.3-70b",
            "metadata": {"latencyMs": 3500, "error": "llm_timeout"},
            "status": "ERROR",
            "error": "llm_timeout",
        },
    ],
}


def _classify(**kwargs) -> clf.ClassifiedTrace:
    """Build a ClassifiedTrace with defaults, override selected fields."""
    base = clf.decode_trace(GOOD_DIRECT_TRACE)
    base.trace_id = kwargs.pop("trace_id", base.trace_id)
    base.query = kwargs.pop("query", base.query)
    base.strategy = kwargs.pop("strategy", base.strategy)
    base.confidence = kwargs.pop("confidence", base.confidence)
    base.document_id = kwargs.pop("document_id", base.document_id)
    base.events = kwargs.pop("events", base.events)
    cat, reason, sugg, score = clf.classify(base.events, base.strategy, base.confidence)
    base.category = cat
    base.reason = reason
    base.suggestions = sugg
    base.score = score
    return base


# ------------------------------------------------------------------
# Tests: classification logic
# ------------------------------------------------------------------

def test_good_direct_trace_is_classified_ok():
    """A normal direct-path trace should be classified as direct_ok."""
    t = _classify(trace_id="ok", **GOOD_DIRECT_TRACE)
    assert t.category == "direct_ok"
    assert t.score == 0.0
    assert t.reason.startswith("No failure detected")


def test_no_evidence_strategy_is_retrieval_weak():
    """no_evidence strategy → retrieval_weak."""
    t = _classify(trace_id="rw1", **BAD_RETRIEVAL_TRACE)
    assert t.category == "retrieval_weak"
    assert t.score >= 0.5
    assert any("no_evidence" in s.lower() or "strategy" in s.lower() for s in t.suggestions)


def test_low_confidence_is_retrieval_weak():
    """confidence < 0.35 → retrieval_weak."""
    events = GOOD_DIRECT_TRACE["observations"]
    cat, reason, _, score = clf.classify(
        events, "direct", 0.22
    )
    assert cat == "retrieval_weak"
    assert score >= 0.5


def test_general_knowledge_is_hallucination():
    """general_knowledge strategy when content exists → hallucination label."""
    t = _classify(trace_id="hl1", **BAD_HALLUCINATION_TRACE)
    assert t.category == "hallucination"
    assert t.score >= 0.5


def test_llm_error_is_wrong_tool():
    """LLM failure (error metadata or status ERROR) → wrong_tool."""
    t = _classify(trace_id="wt1", **BAD_LLM_FAILURE_TRACE)
    assert t.category == "wrong_tool"
    assert t.score >= 0.7
    assert "fallback" in t.reason.lower() or "circuit" in t.reason.lower() or "llm" in t.reason.lower()


def test_empty_retrieval_output_is_retrieval_weak():
    """Retrieval span with empty output → retrieval_weak."""
    events = [
        {
            "name": "retrieve_chunks",
            "type": "SPAN",
            "metadata": {"chunkCount": 0},
            "output": "",
        },
        {
            "name": "generate_answer",
            "type": "GENERATION",
            "metadata": {"latencyMs": 900},
            "output": "Sorry I cannot answer.",
        },
    ]
    decoded = [clf.TraceEvent(**{k: v for k, v in ev.items() if k in clf.TraceEvent.__dataclass_fields__}) for ev in events]
    cat, _, _, score = clf.classify(decoded, "direct", 0.15)
    assert cat == "retrieval_weak"
    assert score >= 0.5


def test_categorization_preserves_trace_identity():
    """ClassifiedTrace must keep trace_id, query, strategy intact."""
    t = _classify(trace_id="xyz-123", query="test query", strategy="corrective", confidence=0.6)
    assert t.trace_id == "xyz-123"
    assert t.query == "test query"
    assert t.strategy == "corrective"
    assert t.confidence == 0.6


# ------------------------------------------------------------------
# Tests: report generation
# ------------------------------------------------------------------

def test_build_report_counts_categories():
    """build_report must count traces per category."""
    traces = [
        clf.ClassifiedTrace(trace_id="a", query="q1", strategy="direct", confidence=0.8,
                            document_id=None, category="direct_ok", reason="", suggestions=[], score=0),
        clf.ClassifiedTrace(trace_id="b", query="q2", strategy="no_evidence", confidence=0.1,
                            document_id=12, category="retrieval_weak", reason="low conf", suggestions=["x"], score=0.7),
    ]
    report = clf.build_report(traces)
    assert report["total_traces"] == 2
    assert report["by_category"]["direct_ok"] == 1
    assert report["by_category"]["retrieval_weak"] == 1
    assert report["by_category_pct"]["direct_ok"] == 50.0


def test_build_report_collects_suggestions():
    """Per-category suggestions must be unique and sorted."""
    traces = [
        clf.ClassifiedTrace(trace_id="a", query="q", strategy="no_evidence", confidence=0.1,
                            document_id=1, category="retrieval_weak", reason="", suggestions=["b", "a"], score=0.6),
        clf.ClassifiedTrace(trace_id="b", query="q", strategy="no_evidence", confidence=0.1,
                            document_id=1, category="retrieval_weak", reason="", suggestions=["a", "c"], score=0.6),
    ]
    report = clf.build_report(traces)
    suggestions = report["per_category"]["retrieval_weak"]["suggestions"]
    assert suggestions == ["a", "b", "c"]


def test_build_report_emits_per_trace_classifications():
    """The classifications list in the report must contain all traces."""
    traces = [
        clf.ClassifiedTrace(trace_id="t1", query="q1", strategy="direct", confidence=0.8,
                            document_id=None, category="direct_ok", reason="", suggestions=[], score=0),
    ]
    report = clf.build_report(traces)
    assert len(report["classifications"]) == 1
    assert report["classifications"][0]["trace_id"] == "t1"
    assert report["classifications"][0]["category"] == "direct_ok"


# ------------------------------------------------------------------
# Tests: CLI round-trip (end-to-end on a temp file)
# ------------------------------------------------------------------

def test_cli_export_then_classify(tmp_path):
    """Write a small bad-traces JSON, run the classifier CLI, verify output."""
    input_file = tmp_path / "bad_traces.json"
    output_file = tmp_path / "report.json"

    input_file.write_text(json.dumps({"traces": [BAD_RETRIEVAL_TRACE, BAD_HALLUCINATION_TRACE]}))

    result = subprocess.run(
        [sys.executable, "scripts/phase4_classifier.py", str(input_file), "--out", str(output_file)],
        cwd=".",
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert output_file.exists()
    report = json.loads(output_file.read_text())
    assert report["total_traces"] == 2
    assert report["by_category"]["retrieval_weak"] == 1
    assert report["by_category"]["hallucination"] == 1
    assert report["by_category"]["direct_ok"] == 0
    assert len(report["classifications"]) == 2


def test_cli_accepts_list_input(tmp_path):
    """Classifier CLI also accepts a plain list (not wrapped in {'traces': [...]})."""
    input_file = tmp_path / "bad_list.json"
    output_file = tmp_path / "report2.json"
    input_file.write_text(json.dumps([BAD_RETRIEVAL_TRACE]))
    result = subprocess.run(
        [sys.executable, "scripts/phase4_classifier.py", str(input_file), "--out", str(output_file)],
        cwd=".",
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    report = json.loads(output_file.read_text())
    assert report["total_traces"] == 1


def test_cli_empty_input_is_noop(tmp_path):
    """An empty traces list should produce a report with total_traces == 0 and exit 0."""
    input_file = tmp_path / "empty.json"
    output_file = tmp_path / "report_empty.json"
    input_file.write_text(json.dumps({"traces": []}))
    result = subprocess.run(
        [sys.executable, "scripts/phase4_classifier.py", str(input_file), "--out", str(output_file)],
        cwd=".",
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert json.loads(output_file.read_text())["total_traces"] == 0


# ------------------------------------------------------------------
# Tests: edge cases
# ------------------------------------------------------------------

def test_none_confidence_does_not_blow_up():
    """confidence=None should be handled gracefully."""
    events = GOOD_DIRECT_TRACE["observations"]
    cat, _, _, score = clf.classify(events, "direct", None)
    assert cat == "direct_ok"
    assert score == 0.0


def test_unknown_strategy_defaults_to_ok_if_confidence_high():
    """strategy='unknown' with high confidence should be direct_ok (no failure)."""
    events = GOOD_DIRECT_TRACE["observations"]
    cat, reason, _, score = clf.classify(events, "unknown", 0.85)
    assert cat == "direct_ok"
    assert score == 0.0


def test_decode_trace_preserves_observation_fields():
    """Decoding must keep name, type, model, output, input, status, metadata."""
    trace = {
        "trace_id": "decode-test",
        "query": "q",
        "strategy": "direct",
        "confidence": 0.9,
        "document_id": 7,
        "observations": [
            {
                "name": "retrieve_chunks",
                "type": "SPAN",
                "model": "bge-base-en-v1.5",
                "metadata": {"chunkCount": 2, "latencyMs": 10},
                "output": "chunk text",
                "input": "query text",
                "status": "COMPLETED",
            }
        ],
    }
    t = clf.decode_trace(trace)
    assert len(t.events) == 1
    ev = t.events[0]
    assert ev.name == "retrieve_chunks"
    assert ev.kind == "SPAN"
    assert ev.model == "bge-base-en-v1.5"
    assert ev.output == "chunk text"
    assert ev.input == "query text"
    assert ev.status == "COMPLETED"
    assert ev.metadata == {"chunkCount": 2, "latencyMs": 10}
    assert t.trace_id == "decode-test"
    assert t.confidence == 0.9
    assert t.document_id == 7


# ------------------------------------------------------------------
# Tests: report format structure (for downstream consumers)
# ------------------------------------------------------------------

def test_report_has_required_top_level_keys():
    """Report must contain keys downstream eval/e2e scripts expect."""
    traces = []
    report = clf.build_report(traces)
    required = {
        "report_at", "total_traces", "by_category", "by_category_pct",
        "reasons", "strategy_distribution", "per_category", "classifications",
    }
    assert required.issubset(report.keys())


def test_per_category_has_examples_and_suggestions():
    """Each category in per_category must have examples (list) and suggestions (list)."""
    report = clf.build_report([])
    for cat, info in report["per_category"].items():
        assert isinstance(info["examples"], list)
        assert isinstance(info["suggestions"], list)
        assert isinstance(info["count"], int)
        assert isinstance(info["pct"], float)


def test_strategy_distribution_is_dict():
    """strategy_distribution must be a plain dict mapping strategy -> count."""
    report = clf.build_report([])
    assert isinstance(report["strategy_distribution"], dict)


# ------------------------------------------------------------------
# Integration-ish: runs the real classifier module without subprocess
# ------------------------------------------------------------------

def test_e2e_classify_pipeline(tmp_path):
    """End-to-end: write file, read with decode_trace + classify + build_report + write report."""
    input_file = tmp_path / "in.json"
    output_file = tmp_path / "out.json"
    input_file.write_text(json.dumps({
        "traces": [GOOD_DIRECT_TRACE, BAD_RETRIEVAL_TRACE, BAD_HALLUCINATION_TRACE, BAD_LLM_FAILURE_TRACE]
    }))

    with open(input_file) as f:
        raw = json.load(f)
    traces = raw["traces"]

    classified = [clf.decode_trace(t) for t in traces]
    for t in classified:
        cat, reason, sugg, score = clf.classify(t.events, t.strategy, t.confidence)
        t.category = cat
        t.reason = reason
        t.suggestions = sugg
        t.score = score

    report = clf.build_report(classified)
    with open(output_file, "w") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    loaded = json.loads(output_file.read_text())
    assert loaded["total_traces"] == 4
    assert loaded["by_category"]["direct_ok"] >= 1
    assert loaded["by_category"]["retrieval_weak"] >= 1
    assert loaded["by_category"]["hallucination"] >= 1
    assert loaded["by_category"]["wrong_tool"] >= 1
