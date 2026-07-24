"""
MCP (Model Context Protocol) Server — custom implementation.
=============================================================
Provides a standardized way for LLMs to discover and call tools.

Inspired by Anthropic's MCP specification:
- Tools: typed function definitions with JSON Schema
- Server: exposes tools via an endpoint
- Client: discovers and invokes tools
- Transport: supports stdio and SSE (Server-Sent Events)

Note: This is a custom implementation inspired by MCP concepts.
"""

import asyncio
import inspect
import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


# ============================================================================
# Types
# ============================================================================


class ToolInputSchemaType(str, Enum):
    """JSON Schema types for tool inputs."""

    STRING = "string"
    NUMBER = "number"
    INTEGER = "integer"
    BOOLEAN = "boolean"
    ARRAY = "array"
    OBJECT = "object"

    @classmethod
    def from_python_type(cls, t: type) -> "ToolInputSchemaType":
        mapping = {
            str: cls.STRING,
            int: cls.INTEGER,
            float: cls.NUMBER,
            bool: cls.BOOLEAN,
            list: cls.ARRAY,
            dict: cls.OBJECT,
        }
        return mapping.get(t, cls.STRING)


class TransportType(str, Enum):
    STDIO = "stdio"
    SSE = "sse"


class ToolCallStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    ERROR = "error"


# ============================================================================
# Data Models
# ============================================================================


@dataclass
class MCPServerInfo:
    """Metadata about an MCP server."""

    name: str
    version: str = "1.0.0"
    description: str = ""
    transport: TransportType = TransportType.SSE
    vendor: str = "Smart Document Chatbot"
    tools_count: int = 0


@dataclass
class MCPToolSpec:
    """Specification for a tool exposed via MCP."""

    name: str
    description: str
    input_schema: Dict[str, Any]  # JSON Schema
    output_schema: Optional[Dict[str, Any]] = None
    required: List[str] = field(default_factory=list)
    category: str = "general"
    timeout_seconds: float = 30.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": {
                "type": "object",
                "properties": self.input_schema,
                "required": self.required,
            },
            "output_schema": self.output_schema,
        }


@dataclass
class MCPToolResult:
    """Result from a tool call."""

    tool_name: str
    status: ToolCallStatus
    result: Any = None
    error: Optional[str] = None
    latency_seconds: float = 0.0
    call_id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])


# ============================================================================
# MCP Server
# ============================================================================


class MCPServer:
    """
    MCP Server — holds tool definitions and handles discovery + execution.

    Supports:
    - Tool registration with JSON Schema
    - Tool discovery (list_tools, get_tool)
    - Tool execution with timeout and error handling
    - SSE transport for streaming
    - History tracking
    """

    def __init__(self, name: str = "agent-mcp-server", version: str = "1.0.0"):
        self.info = MCPServerInfo(
            name=name,
            version=version,
            description="MCP server for Smart Document Chatbot agent tools",
        )
        self._tools: Dict[str, MCPToolSpec] = {}
        self._handlers: Dict[str, Callable] = {}
        self._call_history: List[MCPToolResult] = []
        self._max_history = 100

    # ------------------------------------------------------------------
    # Tool Registration
    # ------------------------------------------------------------------

    def register_tool(
        self,
        name: str,
        description: str,
        handler: Callable,
        input_schema: Optional[Dict[str, Any]] = None,
        output_schema: Optional[Dict[str, Any]] = None,
        required_params: Optional[List[str]] = None,
        category: str = "general",
        timeout_seconds: float = 30.0,
    ) -> None:
        """
        Register a tool with the MCP server.

        Args:
            name: Tool name (used to invoke)
            description: Human-readable description
            handler: Async or sync function to call
            input_schema: JSON Schema dict for input parameters
            output_schema: JSON Schema dict for output
            required_params: List of required parameter names
            category: Tool category for grouping
            timeout_seconds: Max execution time
        """
        spec = MCPToolSpec(
            name=name,
            description=description,
            input_schema=input_schema or {},
            output_schema=output_schema,
            required=required_params or [],
            category=category,
            timeout_seconds=timeout_seconds,
        )
        self._tools[name] = spec
        self._handlers[name] = handler
        self.info.tools_count = len(self._tools)
        logger.info(f"[MCPServer] Registered tool '{name}' ({category})")

    def register_tools_from_registry(
        self,
        tool_specs: List[MCPToolSpec],
        handlers: Dict[str, Callable],
    ) -> None:
        """Register multiple tools at once (from ADKToolRegistry)."""
        for spec in tool_specs:
            handler = handlers.get(spec.name)
            if handler:
                self.register_tool(
                    name=spec.name,
                    description=spec.description,
                    handler=handler,
                    input_schema=spec.input_schema,
                    output_schema=spec.output_schema,
                    timeout_seconds=spec.timeout_seconds,
                )

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------

    def list_tools(self) -> List[Dict[str, Any]]:
        """List all available tools with their specs."""
        return [spec.to_dict() for spec in self._tools.values()]

    def get_tool(self, name: str) -> Optional[Dict[str, Any]]:
        """Get a specific tool's spec."""
        spec = self._tools.get(name)
        return spec.to_dict() if spec else None

    def get_server_info(self) -> Dict[str, Any]:
        """Get server metadata."""
        return {
            "name": self.info.name,
            "version": self.info.version,
            "description": self.info.description,
            "transport": self.info.transport.value,
            "vendor": self.info.vendor,
            "tools_count": self.info.tools_count,
        }

    # ------------------------------------------------------------------
    # Tool Execution
    # ------------------------------------------------------------------

    async def call_tool(
        self,
        name: str,
        arguments: Dict[str, Any],
        timeout: Optional[float] = None,
    ) -> MCPToolResult:
        """
        Execute a tool by name with arguments.

        Includes:
        - Timeout
        - Async/sync handler detection
        - Error handling
        - History tracking
        """
        start = time.time()
        call_id = str(uuid.uuid4())[:12]

        if name not in self._tools:
            return MCPToolResult(
                tool_name=name,
                status=ToolCallStatus.ERROR,
                error=f"Tool '{name}' not found",
                call_id=call_id,
            )

        spec = self._tools[name]
        handler = self._handlers.get(name)
        timeout = timeout or spec.timeout_seconds

        if not handler:
            return MCPToolResult(
                tool_name=name,
                status=ToolCallStatus.ERROR,
                error=f"Tool '{name}' has no handler registered",
                call_id=call_id,
            )

        try:
            if inspect.iscoroutinefunction(handler):
                result = await asyncio.wait_for(
                    handler(**arguments),
                    timeout=timeout,
                )
            else:
                result = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: handler(**arguments),
                )

            latency = time.time() - start
            tool_result = MCPToolResult(
                tool_name=name,
                status=ToolCallStatus.SUCCESS,
                result=result,
                latency_seconds=round(latency, 3),
                call_id=call_id,
            )

            logger.info(f"[MCPServer] Tool '{name}' completed in {latency:.2f}s")

        except asyncio.TimeoutError:
            tool_result = MCPToolResult(
                tool_name=name,
                status=ToolCallStatus.ERROR,
                error=f"Tool '{name}' timed out after {timeout}s",
                latency_seconds=time.time() - start,
                call_id=call_id,
            )
            logger.warning(f"[MCPServer] Tool '{name}' timed out")

        except Exception as e:
            tool_result = MCPToolResult(
                tool_name=name,
                status=ToolCallStatus.ERROR,
                error=str(e),
                latency_seconds=time.time() - start,
                call_id=call_id,
            )
            logger.error(f"[MCPServer] Tool '{name}' failed: {e}")

        # Store in history
        self._call_history.append(tool_result)
        if len(self._call_history) > self._max_history:
            self._call_history = self._call_history[-self._max_history :]

        return tool_result

    # ------------------------------------------------------------------
    # SSE / Streaming Support
    # ------------------------------------------------------------------

    def sse_endpoint(self) -> str:
        """Get the SSE endpoint URL."""
        return f"/mcp/{self.info.name}/sse"

    async def stream_tool_call(
        self,
        name: str,
        arguments: Dict[str, Any],
    ) -> str:
        """
        Stream a tool call with SSE-like events.
        Returns JSON lines with status updates.
        """
        lines: List[str] = []

        # Start event
        lines.append(
            json.dumps(
                {
                    "type": "tool_call_start",
                    "tool": name,
                    "arguments": arguments,
                }
            )
        )

        # Execute
        result = await self.call_tool(name, arguments)

        # Result event
        lines.append(
            json.dumps(
                {
                    "type": "tool_call_result",
                    "tool": name,
                    "status": result.status.value,
                    "result": result.result
                    if result.status == ToolCallStatus.SUCCESS
                    else None,
                    "error": result.error,
                    "latency_seconds": result.latency_seconds,
                }
            )
        )

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # History & Stats
    # ------------------------------------------------------------------

    def get_call_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent tool call history."""
        recent = self._call_history[-limit:]
        return [
            {
                "tool_name": r.tool_name,
                "status": r.status.value,
                "error": r.error,
                "latency_seconds": r.latency_seconds,
                "call_id": r.call_id,
            }
            for r in recent
        ]

    def get_stats(self) -> Dict[str, Any]:
        """Get MCP server statistics."""
        total = len(self._call_history)
        successes = sum(
            1 for r in self._call_history if r.status == ToolCallStatus.SUCCESS
        )
        errors = sum(1 for r in self._call_history if r.status == ToolCallStatus.ERROR)
        avg_latency = (
            sum(r.latency_seconds for r in self._call_history) / total
            if total > 0
            else 0.0
        )

        return {
            "server": self.info.name,
            "tools_count": self.info.tools_count,
            "total_calls": total,
            "successes": successes,
            "errors": errors,
            "success_rate": round(successes / max(total, 1), 4),
            "avg_latency_seconds": round(avg_latency, 3),
        }


# ============================================================================
# MCP Client (for calling remote MCP servers)
# ============================================================================


class MCPClient:
    """
    MCP Client — discovers and calls tools on MCP servers.
    """

    def __init__(self, base_url: str = ""):
        self.base_url = base_url
        self._tool_cache: Optional[List[Dict[str, Any]]] = None
        self._server_info: Optional[Dict[str, Any]] = None

    async def discover_tools(self) -> List[Dict[str, Any]]:
        """Discover tools from the MCP server."""
        # In a full implementation, this would call the server's /tools endpoint
        # For now, returns cached tools
        return self._tool_cache or []

    def set_tools(self, tools: List[Dict[str, Any]]) -> None:
        """Set tool definitions (for local use)."""
        self._tool_cache = tools
