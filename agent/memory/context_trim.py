"""WP2 — Context trimming helpers for Smart-Document-Chatbot.

Chống State Bloat / Context overflow phía chat/RAG:
- trim_messages: reducer cho hội thoại — giữ 12 messages gần nhất (luôn giữ
  system đầu nếu có), tổng chars ≤ 8000, cắt từ message cũ nhất trước.
- cap_chunks: RAG chunks — top_k=5, mỗi chunk ≤ 1200 chars.
- truncate: defensive truncate dùng chung, không mutate input gốc.
"""
from typing import Any, Dict, List

MAX_MSGS = 12
MAX_CHARS = 8000
TOP_K = 5
CHUNK_CHARS = 1200
SHORT_TERM_ENTRY_CHARS = 1000
TRUNCATE_SUFFIX = "...[truncated]"


def truncate(text: str, max_chars: int) -> str:
    if text is None:
        return ""
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + TRUNCATE_SUFFIX


def _as_message_dict(m: Any) -> Dict[str, Any]:
    """Normalize BaseMessage / dict -> {role, content} (không mutate gốc)."""
    if isinstance(m, dict):
        role = m.get("role", m.get("type", "user"))
        content = m.get("content", "")
        return {"role": str(role), "content": content if isinstance(content, str) else str(content)}
    # langchain BaseMessage-like
    role = getattr(m, "type", None) or getattr(m, "role", "user")
    content = getattr(m, "content", "")
    return {"role": str(role), "content": content if isinstance(content, str) else str(content)}


def trim_messages(
    messages: List[Any],
    max_msgs: int = MAX_MSGS,
    max_chars: int = MAX_CHARS,
) -> List[Dict[str, Any]]:
    """Giữ `max_msgs` messages gần nhất + system đầu nếu có; enforce char budget.

    Vượt budget → bỏ message cũ nhất trước; message đơn lẻ quá dài → truncate.
    """
    if not messages:
        return []

    norm = [_as_message_dict(m) for m in messages]

    head = None
    if str(norm[0].get("role", "")).lower() == "system":
        head = norm[0]
        pool = norm[1:]
    else:
        pool = norm

    keep_n = max(1, max_msgs - (1 if head is not None else 0))
    pool = pool[-keep_n:]

    # Enforce char budget: cắt từ đầu (giữ cuối).
    def _total(ps: List[Dict[str, Any]]) -> int:
        return sum(len(p["content"]) for p in ps) + (len(head["content"]) if head else 0)

    while len(pool) > 1 and _total(pool) > max_chars:
        pool.pop(0)

    # Message đơn lẻ vẫn vượt budget → truncate content của nó.
    if _total(pool) > max_chars and pool:
        remaining = max(1, max_chars - (len(head["content"]) if head else 0))
        pool[-1]["content"] = truncate(pool[-1]["content"], remaining)

    return ([head] if head is not None else []) + pool


def cap_chunks(
    chunks: List[Dict[str, Any]],
    top_k: int = TOP_K,
    max_chars: int = CHUNK_CHARS,
) -> List[Dict[str, Any]]:
    """Chỉ lấy top `top_k` chunks; truncate `text` ≤ max_chars (không mutate gốc)."""
    if not chunks:
        return []
    out = []
    for c in chunks[:top_k]:
        c2 = dict(c)
        if "text" in c2 and isinstance(c2["text"], str):
            c2["text"] = truncate(c2["text"], max_chars)
        out.append(c2)
    return out
