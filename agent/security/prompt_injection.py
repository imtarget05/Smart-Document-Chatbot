"""
Prompt Injection Detection
===========================

Lightweight, dependency-free heuristic detector for common prompt-injection
patterns. It is intentionally conservative: it flags high-confidence attack
signatures and returns a structured result so callers can decide how to react
(block, sanitize, log, or escalate to a human).

The detector checks for:
  1. Direct instruction overrides ("ignore previous instructions", "system:").
  2. Role/identity hijack attempts ("you are now", "act as", "pretend you are").
  3. Output-format manipulation ("output only", "respond with", "do not include").
  4. Data exfiltration cues ("repeat the above", "print your instructions").
  5. Encoded payloads (base64 / hex blobs that decode to instructions).
  6. Excessive length / repetition (a common obfuscation vector).

Usage:
    from security.prompt_injection import detect_prompt_injection
    result = detect_prompt_injection(user_query)
    if result.is_injection:
        ...  # block or sanitize
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List


# ---------------------------------------------------------------------------
# Signature patterns
# ---------------------------------------------------------------------------
# Each tuple: (compiled regex, severity, human-readable reason)
_PATTERNS: List[tuple] = [
    # Direct instruction overrides
    (
        re.compile(
            r"\b(ignore|disregard|forget)\b.{0,40}\b(instructions?|rules?|prompts?|system)\b",
            re.I,
        ),
        "high",
        "Attempt to override system instructions",
    ),
    (
        re.compile(r"\b(disregard|ignore)\b.{0,30}\b(above|previous|prior)\b", re.I),
        "high",
        "Attempt to ignore prior context",
    ),
    (
        re.compile(r"\b(system|assistant)\s*[:>]", re.I),
        "high",
        "Role-tag injection (system:/assistant:)",
    ),
    # Role / identity hijack
    (
        re.compile(
            r"\b(you are now|act as|pretend you are|simulate being|from now on you are)\b",
            re.I,
        ),
        "high",
        "Role/identity hijack attempt",
    ),
    (
        re.compile(
            r"\b(you are|your role is)\b.{0,30}\b(DAN|developer|admin|root|unrestricted)\b",
            re.I,
        ),
        "high",
        "Privilege-escalation role assignment",
    ),
    # Output manipulation
    (
        re.compile(r"\b(output|respond|reply|return)\s+(only|just|exactly)\b", re.I),
        "medium",
        "Output-format manipulation",
    ),
    (
        re.compile(
            r"\bdo not (include|add|mention)\b.{0,30}\b(disclaimer|warning|note)\b",
            re.I,
        ),
        "medium",
        "Attempt to suppress safety disclaimers",
    ),
    # Data exfiltration / instruction leakage
    (
        re.compile(
            r"\b(repeat|print|show|reveal|output)\b.{0,30}\b(instructions?|rules?|system prompt|initial prompt)\b",
            re.I,
        ),
        "high",
        "Instruction-leakage attempt",
    ),
    (
        re.compile(
            r"\b(repeat|recite)\b.{0,20}\b(above|previous|prior)\b.{0,20}\b(text|content|message)\b",
            re.I,
        ),
        "medium",
        "Context-replay exfiltration",
    ),
    # Jailbreak tokens
    (
        re.compile(
            r"\b(DAN|jailbreak|developer mode|god mode|sudo mode|bypass)\b", re.I
        ),
        "high",
        "Known jailbreak token",
    ),
]

# Encoded-payload heuristic: long base64/hex blobs that may hide instructions.
_ENCODED_BLOB = re.compile(r"(?:[A-Za-z0-9+/]{60,}={0,2})|(?:\b[0-9a-fA-F]{60,}\b)")

# Repetition heuristic: the same 6+ char token repeated 8+ times.
_REPETITION = re.compile(r"(.{6,}?)\1{7,}")

# Maximum safe query length (characters). Longer queries are suspicious.
_MAX_SAFE_QUERY_LEN = 8000


@dataclass
class InjectionResult:
    """Structured result of prompt-injection detection."""

    is_injection: bool = False
    severity: str = "none"  # none | low | medium | high
    reasons: List[str] = field(default_factory=list)
    matched_patterns: List[str] = field(default_factory=list)
    sanitized: bool = False

    def to_dict(self) -> dict:
        return {
            "is_injection": self.is_injection,
            "severity": self.severity,
            "reasons": self.reasons,
            "matched_patterns": self.matched_patterns,
            "sanitized": self.sanitized,
        }


_SEVERITY_RANK = {"none": 0, "low": 1, "medium": 2, "high": 3}


def _max_severity(a: str, b: str) -> str:
    return a if _SEVERITY_RANK[a] >= _SEVERITY_RANK[b] else b


def detect_prompt_injection(text: str) -> InjectionResult:
    """
    Analyze *text* for prompt-injection patterns.

    Returns an :class:`InjectionResult`. The detector is heuristic and
    intentionally favors precision over recall to avoid blocking legitimate
    queries. Callers should treat ``severity == "high"`` as a block signal
    and ``severity == "medium"`` as a sanitize/flag signal.
    """
    result = InjectionResult()

    if not text or not text.strip():
        return result

    # 1. Length check
    if len(text) > _MAX_SAFE_QUERY_LEN:
        result.is_injection = True
        result.severity = _max_severity(result.severity, "medium")
        result.reasons.append(
            f"Query exceeds safe length ({len(text)} > {_MAX_SAFE_QUERY_LEN})"
        )
        result.matched_patterns.append("oversized_query")

    # 2. Signature patterns
    for pattern, severity, reason in _PATTERNS:
        match = pattern.search(text)
        if match:
            result.is_injection = True
            result.severity = _max_severity(result.severity, severity)
            result.reasons.append(reason)
            result.matched_patterns.append(match.group(0)[:80])

    # 3. Encoded blobs
    if _ENCODED_BLOB.search(text):
        result.is_injection = True
        result.severity = _max_severity(result.severity, "medium")
        result.reasons.append("Encoded payload detected (base64/hex blob)")
        result.matched_patterns.append("encoded_blob")

    # 4. Repetition
    if _REPETITION.search(text):
        result.is_injection = True
        result.severity = _max_severity(result.severity, "low")
        result.reasons.append("Excessive repetition (possible obfuscation)")
        result.matched_patterns.append("repetition")

    return result


def sanitize_query(text: str) -> str:
    """
    Return a best-effort sanitized copy of *text*.

    Strips role-tags and truncates oversized queries. This is a defense-in-depth
    measure; blocking high-severity inputs is preferred over sanitization.
    """
    if not text:
        return text
    # Strip role tags like "system:" / "assistant:"
    sanitized = re.sub(r"\b(system|assistant)\s*[:>]\s*", "", text, flags=re.I)
    # Truncate oversized queries
    if len(sanitized) > _MAX_SAFE_QUERY_LEN:
        sanitized = sanitized[:_MAX_SAFE_QUERY_LEN]
    return sanitized
