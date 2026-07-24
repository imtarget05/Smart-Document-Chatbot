"""Test script for Long-Term Memory, Multi-lingual, Context Summarization.

Run: python -m pytest tests/test_long_term_memory.py -v
Or standalone: python tests/test_long_term_memory.py
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "agent"))

from memory.long_term import LongTermMemory, LongTermFact
from memory.context_summarizer import ContextSummarizer
from memory.language_handler import detect_language, detect_and_instruct


def test_detect_vietnamese():
    assert detect_language("Xin chào, tôi là sinh viên") == "vi"
    assert detect_language("Tôi đang học machine learning") == "vi"


def test_detect_english():
    assert detect_language("Hello, how are you?") == "en"
    assert detect_language("Explain how RAG works") == "en"


def test_detect_mixed():
    lang = detect_language("Tôi muốn học về transformer architecture")
    assert lang in ("vi", "mixed")


def test_detect_vi_no_diacritics():
    lang = detect_language("Xin chao, toi la sinh vien")
    assert lang == "vi"


def test_language_instruction():
    _, instr = detect_and_instruct("Xin chào")
    assert "Vietnamese" in instr
    _, instr = detect_and_instruct("Hello")
    assert "English" in instr


async def test_ltm_store_and_retrieve():
    ltm = LongTermMemory()
    await ltm.ensure_table()
    fact = LongTermFact(
        fact_text="User likes Python",
        importance=0.8,
        category="preference",
        user_id="test-user",
        session_id="s1",
    )
    await ltm._store_fact(fact)
    facts = await ltm.retrieve("test-user")
    assert len(facts) >= 1
    assert facts[0].fact_text == "User likes Python"


async def test_ltm_extract_heuristic():
    ltm = LongTermMemory()
    conversation = [{"role": "user", "content": "My name is Tan and I like Python"}]
    facts = await ltm.extract_and_store("s1", "test-user", conversation)
    assert len(facts) >= 1


async def test_ltm_cross_session():
    ltm = LongTermMemory()
    await ltm._store_fact(
        LongTermFact(
            fact_text="User is learning AI agents",
            importance=0.9,
            category="goal",
            user_id="user-cross",
            session_id="s1",
        )
    )
    facts = await ltm.retrieve("user-cross")
    assert len(facts) >= 1
    assert "AI agents" in facts[0].fact_text


async def test_summarizer_no_llm():
    summarizer = ContextSummarizer(llm_router=None)
    history = [
        {"role": "user", "content": f"Turn {i} content here for testing" * 5}
        for i in range(20)
    ]
    assert summarizer.needs_summary(history)
    compressed = await summarizer.compress("test-session", history)
    assert len(compressed) < len(history)
    assert compressed[0]["role"] == "system"
    assert "Summary" in compressed[0]["content"]


def test_summarizer_token_estimate():
    summarizer = ContextSummarizer()
    short = [{"role": "user", "content": "hi"}]
    assert not summarizer.needs_summary(short)
    long = [{"role": "user", "content": "x" * 8500}]
    assert summarizer.needs_summary(long)


if __name__ == "__main__":
    test_detect_vietnamese()
    test_detect_english()
    test_detect_mixed()
    test_detect_vi_no_diacritics()
    test_language_instruction()
    print("✅ Language detection: all passed")
    asyncio.run(test_ltm_store_and_retrieve())
    asyncio.run(test_ltm_extract_heuristic())
    asyncio.run(test_ltm_cross_session())
    print("✅ Long-term memory: all passed")
    asyncio.run(test_summarizer_no_llm())
    test_summarizer_token_estimate()
    print("✅ Context summarizer: all passed")
    print("=" * 50)
    print("ALL TESTS PASSED ✅")
    print("=" * 50)
