"""
Short-term memory – stores conversation history per session in-process.
Limited to the last N turns to keep context within LLM token limits.
"""

from collections import defaultdict, deque
from typing import Any, Dict, List


class ShortTermMemory:
    MAX_TURNS = 20

    def __init__(self):
        self._store: Dict[str, deque] = defaultdict(
            lambda: deque(maxlen=self.MAX_TURNS)
        )

    def add(self, session_id: str, role: str, content: str) -> None:
        self._store[session_id].append({"role": role, "content": content})

    def get_recent(self, session_id: str, turns: int = 5) -> List[Dict[str, Any]]:
        history = list(self._store[session_id])
        return history[-turns * 2 :]  # turns = N user+assistant pairs

    def clear(self, session_id: str) -> None:
        self._store[session_id].clear()
