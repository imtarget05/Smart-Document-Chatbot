"""
Tests for SSE Streaming and WebSocket integration.
"""

import json
import pytest

from streaming.sse import SSEEvent, SSEEventType, StreamingResponseHandler


class TestSSEEvent:
    """SSE event creation and serialization tests."""

    def test_start_event(self):
        event = SSEEvent.start("test-session")
        assert event.event_type == SSEEventType.START
        assert event.data["session_id"] == "test-session"

    def test_token_event(self):
        event = SSEEvent.token("Hello", index=1)
        assert event.event_type == SSEEventType.TOKEN
        assert event.data["text"] == "Hello"
        assert event.data["index"] == 1

    def test_done_event(self):
        event = SSEEvent.done("Final answer", latency_seconds=1.5)
        assert event.event_type == SSEEventType.DONE
        assert event.data["answer"] == "Final answer"
        assert event.data["latency_seconds"] == 1.5

    def test_error_event(self):
        event = SSEEvent.error("Something went wrong")
        assert event.event_type == SSEEventType.ERROR
        assert event.data["error"] == "Something went wrong"

    def test_tool_call_event(self):
        event = SSEEvent.tool_call("web_search", {"query": "test"})
        assert event.event_type == SSEEventType.TOOL_CALL
        assert event.data["tool"] == "web_search"
        assert event.data["arguments"]["query"] == "test"

    def test_search_event(self):
        event = SSEEvent.search("test query", results_count=5)
        assert event.event_type == SSEEventType.SEARCH
        assert event.data["query"] == "test query"
        assert event.data["results_count"] == 5

    def test_retrieval_event(self):
        event = SSEEvent.retrieval(chunks_count=10, max_score=0.85)
        assert event.event_type == SSEEventType.RETRIEVAL
        assert event.data["chunks_count"] == 10
        assert event.data["max_score"] == 0.85

    def test_to_sse_string(self):
        event = SSEEvent.token("Hello")
        sse = event.to_sse_string()
        assert sse.startswith("data: ")
        assert sse.endswith("\n\n")
        parsed = json.loads(sse[6:].strip())
        assert parsed["type"] == "token"
        assert parsed["data"]["text"] == "Hello"


class TestStreamingResponseHandler:
    """StreamingResponseHandler tests."""

    @pytest.mark.asyncio
    async def test_cancel(self):
        handler = StreamingResponseHandler()
        assert handler._cancelled is False
        handler.cancel()
        assert handler._cancelled is True

    @pytest.mark.asyncio
    async def test_stream_non_streaming_llm(self):
        handler = StreamingResponseHandler()

        async def mock_llm(prompt, system_prompt=None, model=None):
            return {"text": "Hello world"}

        events = []
        async for event in handler.stream_llm_response(mock_llm, "test prompt"):
            events.append(event)

        assert len(events) >= 2  # start + token + metadata + done
        assert events[0].event_type == SSEEventType.START
        assert any(e.event_type == SSEEventType.TOKEN for e in events)
        assert any(e.event_type == SSEEventType.DONE for e in events)

    @pytest.mark.asyncio
    async def test_cancellation_flag(self):
        handler = StreamingResponseHandler()
        assert handler._cancelled is False
        handler.cancel()
        assert handler._cancelled is True
        assert handler.get_full_response() == ""


class TestAgentEventStream:
    """AgentEventStream tests."""

    @pytest.mark.asyncio
    async def test_stream_agent_execution(self):
        from streaming.sse import AgentEventStream

        stream = AgentEventStream()

        async def mock_llm_stream():
            yield SSEEvent.start()
            yield SSEEvent.token("Hello", 1)
            yield SSEEvent.done("Hello", 0.5)

        orchestrator_result = {"agent_type": "rag", "plan": "Search documents"}
        agent_result = {"answer": "Hello", "sources": []}

        events = []
        async for event in stream.stream_agent_execution(
            "test query", orchestrator_result, agent_result, mock_llm_stream()
        ):
            events.append(event)

        assert len(events) > 0
        # Should have at least the start event
        start_events = [e for e in events if e.event_type == SSEEventType.START]
        assert len(start_events) >= 1
