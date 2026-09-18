"""WP2 (Smart) — State trimming tests (RED until agent.memory.context_trim lands).

  - trim_messages: keep 12 messages, ≤8000 chars, luôn giữ system đầu.
  - cap_chunks: top_k=5 × 1200 chars mỗi chunk.
  - compress: return đúng shape (list of {role, content} dicts).
  - Defensive truncate: short_term memory + qdrant chunk fetch.
"""
from memory.context_trim import (  # noqa: F401
    cap_chunks,
    trim_messages,
    truncate,
)
from memory.short_term import ShortTermMemory


def _msgs(n: int, pad: int = 500) -> list[dict]:
    msgs = [{"role": "system", "content": "S" * 200}]
    for i in range(n):
        msgs.append({"role": "user" if i % 2 == 0 else "assistant", "content": "c" * pad})
    return msgs


def test_trim_messages_keeps_12_and_char_budget():
    out = trim_messages(_msgs(40))
    assert len(out) <= 12
    assert out[0]["role"] == "system", "system message đầu phải được giữ"
    total = sum(len(m["content"]) for m in out)
    assert total <= 8000
    # giữ các message gần nhất
    assert out[-1]["content"] == "c" * 500
    # state gốc intact
    assert len(_msgs(40)) == 41


def test_trim_messages_giant_single_message():
    out = trim_messages([{"role": "user", "content": "x" * 20000}])
    total = sum(len(m["content"]) for m in out)
    assert total <= 8000 + len("...[truncated]")


def test_cap_chunks_top5_1200():
    chunks = [
        {"text": "t" * 2000, "document_name": f"d{i}", "score": 0.9}
        for i in range(8)
    ]
    out = cap_chunks(chunks)
    assert len(out) == 5
    for c in out:
        assert len(c["text"]) <= 1200 + len("...[truncated]")
        assert c["document_name"] == chunks[out.index(c)]["document_name"]
    # chunk gốc intact
    assert len(chunks[0]["text"]) == 2000


def test_compress_return_shape():
    import asyncio

    from memory.context_summarizer import ContextSummarizer

    s = ContextSummarizer(llm_router=None)
    history = _msgs(20, pad=400)
    result = asyncio.run(s.compress("sess", history))
    assert isinstance(result, list)
    assert all(isinstance(m, dict) and "role" in m and "content" in m for m in result)

    # short history -> trả nguyên trạng thái, không thêm system rỗng
    short = [{"role": "user", "content": "hi"}]
    assert asyncio.run(s.compress("sess2", short)) == short


def test_qdrant_short_term_defensive_truncate():
    mem = ShortTermMemory()
    mem.add("s1", "user", "y" * 10000)
    recent = mem.get_recent("s1", turns=1)
    assert len(recent[0]["content"]) <= 1000 + len("...[truncated]")

    from tools.qdrant_tool import defensive_truncate_chunk

    chunk = {"text": "q" * 10000, "document_name": "d", "score": 0.5}
    capped = defensive_truncate_chunk(chunk)
    assert len(capped["text"]) <= 1200 + len("...[truncated]")
    assert len(chunk["text"]) == 10000, "chunk gốc không bị mutate"
