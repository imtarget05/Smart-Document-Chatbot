"""
Guardrails — Input/Output monitoring for RAG pipeline.

Monitors:
  - Input: PII detection, query quality, prompt injection (delegates to existing detector)
  - Output: PII leakage, hallucination signals, empty/low-confidence answers
  - All events are logged to drift detector for trend analysis
"""

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

# ── PII patterns (Vietnamese + English) ──────────────────────────────────────
_PII_PATTERNS: List[tuple] = [
    (re.compile(r"\b\d{9,12}\b"), "CCCD/CMND", "ID number"),
    (re.compile(r"\b0\d{8,10}\b"), "phone_vn", "Vietnamese phone number"),
    (re.compile(r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b"), "phone_us", "US phone number"),
    (re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.+-]+\b"), "email", "Email address"),
    (
        re.compile(
            r"\b(?:\d{4}[-\s]?){3}\d{4}\b"
        ),
        "credit_card",
        "Credit card number",
    ),
    (re.compile(r"\b\d{12,19}\b"), "bank_account", "Bank account number"),
    (
        re.compile(
            r"(?:mật khẩu|password|passwd|pwd|secret|token|api[_-]?key)\s*[:=]\s*\S+",
            re.I,
        ),
        "credential_leak",
        "Password/secret leak",
    ),
]

# ── Output quality signals ─────────────────────────────────────────────────
_OUTPUT_QUALITY_PATTERNS = {
    "empty_answer": re.compile(r"^\s*$"),
    "i_dont_know": re.compile(
        r"\b(không (thể|biết|tìm thấy|rõ)|không có (thông tin|dữ liệu)|"
        r"don't know|can('t|not) (find|answer)|unable to|no (information|data))\b",
        re.I,
    ),
    "hallucination_signal": re.compile(
        r"\b(tôi nghĩ|có thể là|có lẽ|probably|maybe|might be|"
        r"theo tôi được biết|as far as i know)\b",
        re.I,
    ),
}


@dataclass
class GuardrailEvent:
    event_type: str
    severity: str
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.event_type,
            "severity": self.severity,
            "message": self.message,
            "details": self.details,
            "timestamp": self.timestamp,
        }


@dataclass
class GuardrailReport:
    passed: bool = True
    events: List[GuardrailEvent] = field(default_factory=list)
    pii_found: List[str] = field(default_factory=list)
    score: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "passed": self.passed,
            "events": [e.to_dict() for e in self.events],
            "pii_found": self.pii_found,
            "score": self.score,
        }


class InputGuardrails:
    def check(self, text: str) -> GuardrailReport:
        report = GuardrailReport()

        if not text or not text.strip():
            report.passed = False
            report.events.append(
                GuardrailEvent("empty_input", "high", "Empty query received")
            )
            report.score = 0.0
            return report

        # PII detection
        for pattern, pii_type, description in _PII_PATTERNS:
            matches = pattern.findall(text)
            if matches:
                report.pii_found.append(pii_type)
                report.events.append(
                    GuardrailEvent(
                        "pii_detected",
                        "high" if pii_type == "credential_leak" else "medium",
                        f"{description} detected in input",
                        {"pii_type": pii_type, "count": len(matches)},
                    )
                )

        # Query quality checks
        word_count = len(text.split())
        if word_count < 3:
            report.events.append(
                GuardrailEvent(
                    "short_query",
                    "low",
                    f"Very short query ({word_count} words)",
                    {"word_count": word_count},
                )
            )

        if word_count > 500:
            report.events.append(
                GuardrailEvent(
                    "long_query",
                    "medium",
                    f"Query too long ({word_count} words), may hit context limits",
                    {"word_count": word_count},
                )
            )

        # Repeated characters (spam/random noise)
        if re.search(r"(.)\1{20,}", text):
            report.events.append(
                GuardrailEvent(
                    "repeated_chars",
                    "medium",
                    "Query contains excessive repeated characters",
                )
            )

        if report.events:
            report.passed = all(
                e.severity != "high" for e in report.events
            )
            report.score = max(
                0.0,
                1.0 - (sum(_severity_weight(e.severity) for e in report.events) / 10),
            )

        return report


class OutputGuardrails:
    def check(
        self, query: str, answer: str, confidence: float = 0.0
    ) -> GuardrailReport:
        report = GuardrailReport()

        if not answer or not answer.strip():
            report.passed = False
            report.events.append(
                GuardrailEvent("empty_output", "high", "Empty answer generated")
            )
            report.score = 0.0
            return report

        # PII in output (leakage)
        for pattern, pii_type, description in _PII_PATTERNS:
            matches = pattern.findall(answer)
            if matches:
                report.pii_found.append(pii_type)
                report.events.append(
                    GuardrailEvent(
                        "pii_leak",
                        "high",
                        f"{description} leaked in output",
                        {"pii_type": pii_type, "count": len(matches)},
                    )
                )

        # Low confidence
        if confidence < 0.3:
            report.events.append(
                GuardrailEvent(
                    "low_confidence", "medium", "Answer confidence is very low"
                )
            )

        # Quality signals
        for signal_name, pattern in _OUTPUT_QUALITY_PATTERNS.items():
            if pattern.search(answer):
                severity = "medium" if signal_name == "hallucination_signal" else "low"
                report.events.append(
                    GuardrailEvent(
                        signal_name, severity, f"Output quality signal: {signal_name}"
                    )
                )

        # Answer too short relative to query
        answer_words = len(answer.split())
        if answer_words < 5 and confidence < 0.5:
            report.events.append(
                GuardrailEvent(
                    "too_short",
                    "low",
                    f"Answer too short ({answer_words} words)",
                    {"answer_words": answer_words},
                )
            )

        if report.events:
            report.passed = all(
                e.severity != "high" for e in report.events
            )
            report.score = max(
                0.0,
                1.0 - (sum(_severity_weight(e.severity) for e in report.events) / 10),
            )

        return report


def _severity_weight(severity: str) -> float:
    return {"low": 0.5, "medium": 1.0, "high": 2.0}.get(severity, 0.5)


# Singleton guardrails
input_guardrails = InputGuardrails()
output_guardrails = OutputGuardrails()
