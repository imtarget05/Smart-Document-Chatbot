"""Contract tests for exported Langfuse traces."""

from __future__ import annotations

import sys


sys.path.insert(0, "scripts")

import langfuse_export_bad_traces as exporter
import phase4_classifier as classifier


def test_exported_trace_round_trips_top_level_fields_and_observation_error():
    """A wire trace preserves classifier inputs without relying on metadata fallback.

    This would fail if the exporter again removes observation payloads, or if the
    decoder ignores the canonical top-level strategy, confidence, and document id.
    """
    exported = exporter.export_trace(
        {"id": "trace-round-trip", "timestamp": "2026-09-18T00:00:00Z", "name": "fallback query"},
        {
            "metadata": {
                "strategy": "general_knowledge",
                "confidence": "0.42",
                "documentId": "19",
            },
            "input": {"query": "What does the policy allow?"},
            "observations": [
                {
                    "name": "generate_answer",
                    "type": "GENERATION",
                    "model": "qwen3",
                    "input": "policy context",
                    "output": "answer from general knowledge",
                    "status": "ERROR",
                    "error": "upstream timeout",
                    "metadata": {"latencyMs": 250},
                }
            ],
        },
        "strategy:general_knowledge",
    )

    decoded = classifier.decode_trace(exported)

    assert decoded.trace_id == "trace-round-trip"
    assert decoded.query == "What does the policy allow?"
    assert decoded.strategy == "general_knowledge"
    assert decoded.confidence == 0.42
    assert decoded.document_id == 19
    assert len(decoded.events) == 1
    event = decoded.events[0]
    assert event.kind == "GENERATION"
    assert event.input == "policy context"
    assert event.output == "answer from general knowledge"
    assert event.status == "ERROR"
    assert event.error == "upstream timeout"
    assert event.latency_ms == 250


def test_decoder_prefers_canonical_fields_and_accepts_legacy_metadata():
    """Canonical values win, while old metadata-only exports stay readable."""
    canonical = classifier.decode_trace(
        {
            "trace_id": "canonical",
            "strategy": "general_knowledge",
            "confidence": "0.42",
            "document_id": "19",
            "metadata": {"strategy": "no_evidence", "confidence": "0.01", "documentId": "3"},
        }
    )
    legacy = classifier.decode_trace(
        {
            "trace_id": "legacy",
            "metadata": {"strategy": "no_evidence", "confidence": "0.01", "documentId": "3"},
        }
    )

    assert (canonical.strategy, canonical.confidence, canonical.document_id) == (
        "general_knowledge",
        0.42,
        19,
    )
    assert (legacy.strategy, legacy.confidence, legacy.document_id) == ("no_evidence", 0.01, 3)
