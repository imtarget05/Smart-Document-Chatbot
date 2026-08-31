"""Tests for app/prompt_compressor.py — heuristic prompt compression."""

import pytest

from app.models import ChatMessage
from app.prompt_compressor import (
    CompressionResult,
    _compress_text,
    _estimate_tokens,
    _score_segment,
    _split_segments,
    compress_messages,
)


class TestEstimateTokens:
    def test_empty_string_returns_one(self):
        assert _estimate_tokens("") == 1

    def test_short_text(self):
        assert _estimate_tokens("hello world") == 2

    def test_longer_text(self):
        text = "a" * 400
        assert _estimate_tokens(text) == 100


class TestSplitSegments:
    def test_sentence_split(self):
        segments = _split_segments("Hello world. How are you? Fine!")
        assert len(segments) == 3
        assert segments[0] == "Hello world."
        assert segments[1] == "How are you?"
        assert segments[2] == "Fine!"

    def test_newline_split(self):
        segments = _split_segments("Line one\nLine two\n\nLine three")
        assert len(segments) == 3

    def test_empty_string(self):
        assert _split_segments("") == []

    def test_whitespace_only(self):
        assert _split_segments("   \n  \n  ") == []


class TestScoreSegment:
    def test_question_word_boosts_score(self):
        scored = _score_segment("What is the capital of France?", 1, 3)
        assert scored > 0

    def test_first_position_bonus(self):
        seg = "This is a normal sentence with some words in it."
        first_score = _score_segment(seg, 0, 5)
        middle_score = _score_segment(seg, 2, 5)
        assert first_score > middle_score

    def test_last_position_bonus(self):
        seg = "This is a normal sentence with some words in it."
        last_score = _score_segment(seg, 4, 5)
        middle_score = _score_segment(seg, 2, 5)
        assert last_score > middle_score

    def test_empty_segment(self):
        assert _score_segment("", 0, 1) == 0.0


class TestCompressText:
    def test_single_segment_unchanged(self):
        text = "This is a single sentence."
        assert _compress_text(text, 0.5) == text

    def test_compression_removes_segments(self):
        text = "First sentence. Second sentence. Third sentence. Fourth sentence."
        result = _compress_text(text, 0.5)
        assert len(result) < len(text)

    def test_preserves_order(self):
        text = "Alpha one. Beta two. Gamma three. Delta four."
        result = _compress_text(text, 0.5)
        segments = _split_segments(result)
        if len(segments) >= 2:
            original_segments = _split_segments(text)
            indices = [original_segments.index(s) for s in segments]
            assert indices == sorted(indices)


class TestCompressMessages:
    def test_empty_messages(self):
        result = compress_messages([], ratio=0.5, min_tokens=100)
        assert result.skipped is True
        assert result.original_tokens == 0

    def test_below_min_tokens_skips_compression(self):
        messages = [
            ChatMessage(role="user", content="Short message."),
        ]
        result = compress_messages(messages, ratio=0.5, min_tokens=1000)
        assert result.skipped is True
        assert result.ratio == 0.0

    def test_system_messages_never_compressed(self):
        long_content = " ".join(
            ["System instruction sentence number " + str(i) + "." for i in range(50)]
        )
        messages = [
            ChatMessage(role="system", content=long_content),
            ChatMessage(role="user", content="What is this?"),
        ]
        result = compress_messages(messages, ratio=0.5, min_tokens=100)
        assert result.messages[0].content == long_content

    def test_last_message_never_compressed(self):
        long_content = " ".join(
            ["User context sentence number " + str(i) + "." for i in range(50)]
        )
        messages = [
            ChatMessage(role="assistant", content="Previous response."),
            ChatMessage(role="user", content=long_content),
        ]
        result = compress_messages(messages, ratio=0.5, min_tokens=100)
        assert result.messages[-1].content == long_content

    def test_compression_reduces_tokens(self):
        long_content = " ".join(
            ["Context sentence number " + str(i) + " with some words." for i in range(100)]
        )
        messages = [
            ChatMessage(role="system", content="You are a helpful assistant."),
            ChatMessage(role="user", content=long_content),
            ChatMessage(role="assistant", content="Here is my response to your query."),
            ChatMessage(role="user", content="Follow up question here?"),
        ]
        result = compress_messages(messages, ratio=0.5, min_tokens=100)
        assert result.compressed_tokens < result.original_tokens
        assert result.ratio > 0.0

    def test_ratio_zero_skips_compression(self):
        messages = [
            ChatMessage(role="user", content="Some content."),
        ]
        result = compress_messages(messages, ratio=0.0, min_tokens=10)
        assert result.skipped is True

    def test_compression_result_skipped_false(self):
        messages = [ChatMessage(role="user", content="Test")]
        result = CompressionResult(
            messages=messages,
            original_tokens=100,
            compressed_tokens=50,
            ratio=0.5,
        )
        assert result.skipped is False

    def test_compression_result_skipped_true(self):
        messages = [ChatMessage(role="user", content="Test")]
        result = CompressionResult(
            messages=messages,
            original_tokens=100,
            compressed_tokens=100,
            ratio=0.0,
        )
        assert result.skipped is True

    def test_non_string_content_preserved(self):
        messages = [
            ChatMessage(role="user", content=[{"type": "text", "text": "multimodal"}]),
        ]
        result = compress_messages(messages, ratio=0.5, min_tokens=10)
        assert result.messages[0].content == [{"type": "text", "text": "multimodal"}]
