"""
SSE (Server-Sent Events) Streaming Support
=============================================
Provides streaming response infrastructure for agent communication.
Enables real-time token-by-token streaming of LLM responses.

Key features:
- SSE event format for streaming LLM responses
- Support for streaming from Ollama / any streaming-compatible LLM
- Graceful cancellation
- Chunked response aggregation for post-processing
"""

import json
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, AsyncGenerator, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class SSEEventType(str, Enum):
    """SSE event types for streaming agent responses."""

    START = "start"
    TOKEN = "token"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    SEARCH = "search"
    RETRIEVAL = "retrieval"
    DONE = "done"
    ERROR = "error"
    METADATA = "metadata"


@dataclass
class SSEEvent:
    """A single SSE event to be streamed to the client."""

    event_type: SSEEventType
    data: Any = None
    metadata: Optional[Dict[str, Any]] = None
    timestamp: float = field(default_factory=time.time)

    def to_sse_string(self) -> str:
        """Convert to SSE format string."""
        payload = {
            "type": self.event_type.value,
            "data": self.data,
            "timestamp": self.timestamp,
        }
        if self.metadata:
            payload["metadata"] = self.metadata
        return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

    @staticmethod
    def start(session_id: str = "") -> "SSEEvent":
        return SSEEvent(
            event_type=SSEEventType.START,
            data={"status": "started", "session_id": session_id},
        )

    @staticmethod
    def token(text: str, index: int = 0) -> "SSEEvent":
        return SSEEvent(
            event_type=SSEEventType.TOKEN,
            data={"text": text, "index": index},
        )

    @staticmethod
    def done(final_answer: str, latency_seconds: float = 0.0) -> "SSEEvent":
        return SSEEvent(
            event_type=SSEEventType.DONE,
            data={
                "answer": final_answer,
                "latency_seconds": round(latency_seconds, 2),
            },
        )

    @staticmethod
    def error(message: str) -> "SSEEvent":
        return SSEEvent(
            event_type=SSEEventType.ERROR,
            data={"error": message},
        )

    @staticmethod
    def tool_call(tool_name: str, arguments: Dict[str, Any]) -> "SSEEvent":
        return SSEEvent(
            event_type=SSEEventType.TOOL_CALL,
            data={"tool": tool_name, "arguments": arguments},
        )

    @staticmethod
    def search(query: str, results_count: int = 0) -> "SSEEvent":
        return SSEEvent(
            event_type=SSEEventType.SEARCH,
            data={"query": query, "results_count": results_count},
        )

    @staticmethod
    def retrieval(chunks_count: int, max_score: float = 0.0) -> "SSEEvent":
        return SSEEvent(
            event_type=SSEEventType.RETRIEVAL,
            data={"chunks_count": chunks_count, "max_score": round(max_score, 4)},
        )


class StreamingResponseHandler:
    """
    Handles streaming of agent responses via SSE.

    Usage:
        handler = StreamingResponseHandler()
        async for event in handler.stream_llm_response(llm, prompt):
            # Send event to client
            event_str = event.to_sse_string()

    Supports:
    - Token-by-token streaming from LLM
    - Tool call notifications
    - Search/retrieval status updates
    - Final result delivery
    """

    def __init__(self):
        self._start_time: float = 0.0
        self._token_count: int = 0
        self._full_response: List[str] = []
        self._cancelled: bool = False

    def cancel(self) -> None:
        """Cancel the current streaming operation."""
        self._cancelled = True
        logger.info("[Streaming] Cancelled by client")

    async def stream_llm_response(
        self,
        llm_callable: Callable,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: str = "qwen2.5:7b",
    ) -> AsyncGenerator[SSEEvent, None]:
        """
        Stream an LLM response token by token.

        Yields:
            SSEEvent for each token and metadata

        Args:
            llm_callable: Async function that takes prompt, system_prompt, model
            prompt: User prompt
            system_prompt: System instructions
            model: Model name
        """
        self._start_time = time.time()
        self._token_count = 0
        self._full_response = []
        self._cancelled = False

        yield SSEEvent.start()

        try:
            # Attempt to call the LLM with streaming support
            # This is a generic interface — adapt to your LLM
            if hasattr(llm_callable, "astream"):
                # LangChain-style streaming
                async for chunk in llm_callable.astream(
                    prompt,
                    system_prompt=system_prompt,
                ):
                    if self._cancelled:
                        break
                    text = chunk if isinstance(chunk, str) else str(chunk)
                    if text:
                        self._token_count += 1
                        self._full_response.append(text)
                        yield SSEEvent.token(text, self._token_count)
            else:
                # Non-streaming fallback
                result = await llm_callable(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    model=model,
                )
                text = (
                    result.get("text", "") if isinstance(result, dict) else str(result)
                )
                if text:
                    yield SSEEvent.token(text, 1)
                    self._full_response.append(text)
                    self._token_count = 1

            latency = time.time() - self._start_time
            final_text = "".join(self._full_response)

            yield SSEEvent(
                event_type=SSEEventType.METADATA,
                data={
                    "tokens": self._token_count,
                    "latency_seconds": round(latency, 2),
                    "tokens_per_second": round(self._token_count / latency, 2)
                    if latency > 0
                    else 0,
                },
            )
            yield SSEEvent.done(final_answer=final_text, latency_seconds=latency)

        except Exception as e:
            logger.error(f"[Streaming] Error: {e}")
            yield SSEEvent.error(str(e))

    def get_full_response(self) -> str:
        """Get the complete aggregated response."""
        return "".join(self._full_response)


class AgentEventStream:
    """
    High-level event stream for agent execution with real-time updates.

    Provides status updates during agent execution:
    1. Agent selection (orchestrator decision)
    2. Tool calls and results
    3. Search/retrieval progress
    4. Token-by-token response generation
    """

    def __init__(self):
        self.handler = StreamingResponseHandler()

    async def stream_agent_execution(
        self,
        query: str,
        orchestrator_result: Dict[str, Any],
        agent_result: Dict[str, Any],
        llm_stream: AsyncGenerator[SSEEvent, None],
    ) -> AsyncGenerator[SSEEvent, None]:
        """
        Stream the full agent execution lifecycle.

        Flow:
        1. Start event
        2. Orchestrator decision (which agent, what plan)
        3. Agent-specific events (tool calls, search, retrieval)
        4. Token-by-token response
        5. Done event
        """
        yield SSEEvent.start()

        # Agent selection
        yield SSEEvent(
            event_type=SSEEventType.START,
            data={
                "agent_type": orchestrator_result.get("agent_type", "rag"),
                "plan": orchestrator_result.get("plan", ""),
                "query": query,
            },
        )

        # Stream LLM response
        async for event in llm_stream:
            if event.event_type != SSEEventType.START:  # Skip duplicate start
                yield event
