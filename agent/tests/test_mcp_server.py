"""
Tests for MCP (Model Context Protocol) Server.
"""

import pytest
from mcp.server import MCPServer, MCPToolSpec, ToolCallStatus


class TestMCPServer:
    """MCP Server tests."""

    def test_initial_state(self):
        server = MCPServer(name="test-server", version="1.0.0")
        assert server.info.name == "test-server"
        assert server.info.version == "1.0.0"
        assert server.info.tools_count == 0

    def test_register_tool(self):
        server = MCPServer(name="test")
        server.register_tool(
            name="web_search",
            description="Search the web",
            handler=lambda query: {"results": []},
            input_schema={"query": {"type": "string"}},
            category="search",
        )
        assert server.info.tools_count == 1
        tools = server.list_tools()
        assert len(tools) == 1
        assert tools[0]["name"] == "web_search"

    def test_list_tools(self):
        server = MCPServer(name="test")
        server.register_tool(
            name="tool1",
            description="Tool 1",
            handler=lambda: None,
        )
        server.register_tool(
            name="tool2",
            description="Tool 2",
            handler=lambda: None,
        )
        tools = server.list_tools()
        assert len(tools) == 2

    def test_get_tool_found(self):
        server = MCPServer(name="test")
        server.register_tool(
            name="my_tool",
            description="My tool",
            handler=lambda: None,
        )
        spec = server.get_tool("my_tool")
        assert spec is not None
        assert spec["name"] == "my_tool"

    def test_get_tool_not_found(self):
        server = MCPServer(name="test")
        assert server.get_tool("nonexistent") is None

    def test_get_server_info(self):
        server = MCPServer(name="my-server", version="2.0.0")
        info = server.get_server_info()
        assert info["name"] == "my-server"
        assert info["version"] == "2.0.0"

    @pytest.mark.asyncio
    async def test_call_tool_sync_handler(self):
        server = MCPServer(name="test")

        def sync_handler(query):
            return {"result": f"Search results for: {query}"}

        server.register_tool(
            name="web_search",
            description="Search",
            handler=sync_handler,
            input_schema={"query": {"type": "string"}},
        )

        result = await server.call_tool("web_search", {"query": "test"})
        assert result.status == ToolCallStatus.SUCCESS
        assert result.result["result"] == "Search results for: test"

    @pytest.mark.asyncio
    async def test_call_tool_async_handler(self):
        server = MCPServer(name="test")

        async def async_handler(query):
            return {"result": f"Async: {query}"}

        server.register_tool(
            name="async_tool",
            description="Async tool",
            handler=async_handler,
        )

        result = await server.call_tool("async_tool", {"query": "hello"})
        assert result.status == ToolCallStatus.SUCCESS
        assert result.result["result"] == "Async: hello"

    @pytest.mark.asyncio
    async def test_call_tool_not_found(self):
        server = MCPServer(name="test")
        result = await server.call_tool("nonexistent", {})
        assert result.status == ToolCallStatus.ERROR
        assert "not found" in result.error

    @pytest.mark.asyncio
    async def test_call_tool_error_handling(self):
        server = MCPServer(name="test")

        def failing_handler():
            raise ValueError("Something broke")

        server.register_tool(
            name="failing_tool",
            description="Fails",
            handler=failing_handler,
        )

        result = await server.call_tool("failing_tool", {})
        assert result.status == ToolCallStatus.ERROR
        assert "Something broke" in result.error

    @pytest.mark.asyncio
    async def test_call_history_tracking(self):
        server = MCPServer(name="test")
        server.register_tool(
            name="tool1",
            description="Tool 1",
            handler=lambda: "ok",
        )
        server.register_tool(
            name="tool2",
            description="Tool 2",
            handler=lambda: "ok",
        )

        await server.call_tool("tool1", {})
        await server.call_tool("tool2", {})

        history = server.get_call_history(limit=10)
        assert len(history) == 2
        assert history[0]["tool_name"] == "tool1"
        assert history[1]["tool_name"] == "tool2"

    @pytest.mark.asyncio
    async def test_get_stats(self):
        server = MCPServer(name="test")
        server.register_tool(
            name="tool1",
            description="Tool 1",
            handler=lambda: "ok",
        )

        await server.call_tool("tool1", {})

        stats = server.get_stats()
        assert stats["server"] == "test"
        assert stats["tools_count"] == 1
        assert stats["total_calls"] == 1
        assert stats["successes"] == 1

    @pytest.mark.asyncio
    async def test_stream_tool_call(self):
        server = MCPServer(name="test")
        server.register_tool(
            name="web_search",
            description="Search",
            handler=lambda query: {"results": ["r1", "r2"]},
        )

        stream_output = await server.stream_tool_call("web_search", {"query": "test"})
        assert "tool_call_start" in stream_output
        assert "tool_call_result" in stream_output
        assert "r1" in stream_output


class TestMCPToolSpec:
    """MCPToolSpec tests."""

    def test_to_dict(self):
        spec = MCPToolSpec(
            name="web_search",
            description="Search the web",
            input_schema={"query": {"type": "string"}},
            required=["query"],
            category="search",
        )
        d = spec.to_dict()
        assert d["name"] == "web_search"
        assert d["input_schema"]["required"] == ["query"]
        assert d["input_schema"]["properties"]["query"]["type"] == "string"
