"""Canonical JSON wire schema shared by RAG trace exporters and consumers."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class TraceObservation:
    """An observation as represented in an exported RAG trace."""

    name: str
    type: str
    model: str | None = None
    input: Any = None
    output: Any = None
    status: str | None = None
    error: Any = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_wire(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RAGTrace:
    """The canonical trace envelope consumed by the offline classifier."""

    trace_id: str
    timestamp: str | None
    failure_reason: str
    strategy: str | None
    confidence: Any
    document_id: Any
    query: str
    observations: list[TraceObservation]

    def to_wire(self) -> dict[str, Any]:
        return {
            **asdict(self),
            "observations": [observation.to_wire() for observation in self.observations],
        }
