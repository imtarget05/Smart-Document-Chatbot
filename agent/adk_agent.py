from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class AdkAgentSpec:
    name: str
    description: str
    instructions: str


class AdkAgent:
    """Minimal ADK-style wrapper for the 5-day coding demo.

    This keeps the interface simple and deterministic so it can be used
    as a foundation for a richer Agent Development Kit integration later.
    """

    def __init__(self, spec: AdkAgentSpec):
        self.spec = spec

    def run(self, user_input: str) -> Dict[str, Any]:
        return {
            "agent": self.spec.name,
            "status": "ok",
            "input": user_input,
            "summary": (
                f"{self.spec.description}. "
                f"Instructions: {self.spec.instructions}"
            ),
        }
