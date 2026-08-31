"""Heuristic-based prompt compressor (LLMLingua-style).

Reduces token usage by scoring and filtering prompt segments without
making an extra LLM call. Only compresses when the estimated token
count exceeds the configured threshold.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .models import ChatMessage


QUESTION_WORDS = frozenset(
    {
        "what", "how", "why", "when", "where", "who", "which", "whom",
        "whose", "whether", "explain", "describe", "define", "list",
        "compare", "difference", "summarize", "summary", "extract",
        "find", "tell", "give", "show", "calculate", "determine",
    }
)

# Rough token estimate: ~4 chars per token for English text.
CHARS_PER_TOKEN = 4


@dataclass
class CompressionResult:
    messages: list[ChatMessage]
    original_tokens: int
    compressed_tokens: int
    ratio: float

    @property
    def skipped(self) -> bool:
        return self.original_tokens == self.compressed_tokens


def _estimate_tokens(text: str) -> int:
    return max(1, len(text) // CHARS_PER_TOKEN)


def _split_segments(text: str) -> list[str]:
    """Split text into sentence-level segments."""
    segments = re.split(r"(?<=[.!?])\s+|\n+", text)
    return [s.strip() for s in segments if s.strip()]


def _score_segment(segment: str, position: int, total: int) -> float:
    """Score a segment based on heuristic signals."""
    words = segment.lower().split()
    if not words:
        return 0.0

    score = 0.0

    # Question-word presence.
    if any(w in QUESTION_WORDS for w in words):
        score += 2.0

    # Named entities (capitalized words not at sentence start).
    capitalized = sum(
        1 for i, w in enumerate(segment.split())
        if i > 0 and w[:1].isupper() and w.isalpha()
    )
    score += min(capitalized, 5) * 0.5

    # Position weight: first and last segments matter more.
    if position == 0:
        score += 1.5
    elif position == total - 1:
        score += 1.0
    elif position < total * 0.25:
        score += 0.5

    # Length normalization: prefer medium-length segments.
    seg_len = len(words)
    if 5 <= seg_len <= 50:
        score *= 1.0
    elif seg_len < 5:
        score *= 0.7
    else:
        score *= 0.85

    return score


def _compress_text(text: str, ratio: float) -> str:
    """Compress a single text string, keeping top-k segments."""
    segments = _split_segments(text)
    if len(segments) <= 1:
        return text

    total = len(segments)
    scored = [
        (seg, _score_segment(seg, i, total)) for i, seg in enumerate(segments)
    ]
    scored.sort(key=lambda x: x[1], reverse=True)

    keep_count = max(1, int(total * (1.0 - ratio)))
    kept = scored[:keep_count]

    # Restore original order.
    kept_segments = [seg for seg, _ in sorted(
        kept, key=lambda x: segments.index(x[0])
    )]
    return " ".join(kept_segments)


def compress_messages(
    messages: list[ChatMessage],
    ratio: float = 0.5,
    min_tokens: int = 1000,
) -> CompressionResult:
    """Compress chat messages while preserving system/recent context.

    - System messages are never compressed.
    - The last user message (current query) is never compressed.
    - Only compresses if total estimated tokens exceed ``min_tokens``.
    """
    if not messages or ratio <= 0.0:
        total = sum(
            _estimate_tokens(m.content) for m in messages
            if isinstance(m.content, str)
        )
        return CompressionResult(
            messages=messages,
            original_tokens=total,
            compressed_tokens=total,
            ratio=0.0,
        )

    original_tokens = sum(
        _estimate_tokens(m.content) for m in messages
        if isinstance(m.content, str)
    )
    if original_tokens < min_tokens:
        return CompressionResult(
            messages=messages,
            original_tokens=original_tokens,
            compressed_tokens=original_tokens,
            ratio=0.0,
        )

    # Determine compressible range: skip system messages and last message.
    system_indices = {
        i for i, m in enumerate(messages) if m.role == "system"
    }
    last_idx = len(messages) - 1

    compressed: list[ChatMessage] = []
    for i, msg in enumerate(messages):
        if (
            i in system_indices
            or i == last_idx
            or not isinstance(msg.content, str)
        ):
            compressed.append(msg)
            continue

        new_content = _compress_text(msg.content, ratio)
        compressed.append(ChatMessage(role=msg.role, content=new_content))

    compressed_tokens = sum(
        _estimate_tokens(m.content) for m in compressed
        if isinstance(m.content, str)
    )
    actual_ratio = (
        (original_tokens - compressed_tokens) / original_tokens
        if original_tokens > 0
        else 0.0
    )

    return CompressionResult(
        messages=compressed,
        original_tokens=original_tokens,
        compressed_tokens=compressed_tokens,
        ratio=round(actual_ratio, 3),
    )
