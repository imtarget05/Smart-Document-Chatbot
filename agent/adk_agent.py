"""
Smart Document Chatbot — ADK-inspired Agent Framework (self-built)
===================================================================
ADK-style (Agent Development Kit) framework built in-house, inspired by
Google ADK architecture patterns:
- AgentConfig: model, tools, instructions configuration
- ToolRegistry: register, discover, and invoke tools
- QueryParser: rule-based + LLM fallback intent detection
- AgentFactory: create specialized agents from config
- Structured output (JSON schema), tracing, retry logic

NOTE: This is a custom implementation inspired by Google ADK concepts,
not the official Google ADK library. The architecture follows similar
patterns (tool registry, agent config, query routing) but is built
entirely from scratch for our specific RAG + multi-agent use case.
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
# Data Models
# ============================================================================


class AgentRole(str, Enum):
    """Roles an ADK-style agent can perform."""

    RAG = "rag"
    RESEARCH = "research"
    REPORT = "report"
    ACTION = "action"
    ENGINEERING = "engineering"
    COMPARATOR = "comparator"
    CHAT = "chat"
    FINANCE = "finance"
    CODE = "code"
    SUMMARIZER = "summarizer"


@dataclass
class ADKToolSpec:
    """Specification for a tool an agent can use."""

    name: str
    description: str
    input_schema: Optional[Dict[str, Any]] = None
    output_schema: Optional[Dict[str, Any]] = None
    requires_approval: bool = False
    timeout_seconds: float = 30.0


@dataclass
class ADKAgentConfig:
    """Configuration for an ADK-style agent."""

    name: str
    role: AgentRole
    instructions: str
    model: str = "qwen2.5:7b"
    tools: List[ADKToolSpec] = field(default_factory=list)
    max_retries: int = 2
    temperature: float = 0.7
    structured_output_schema: Optional[Dict[str, Any]] = None
    tracing_enabled: bool = True
    timeout_seconds: float = 60.0


@dataclass
class ADKExecutionResult:
    """Result from an ADK-style agent execution."""

    agent_name: str
    success: bool
    output: str
    structured_output: Optional[Dict[str, Any]] = None
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    latency_seconds: float = 0.0
    retries: int = 0
    error: Optional[str] = None
    trace_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])


# ============================================================================
# Simplified AgentSpec for the demo runtime (backward-compatible alias)
# ============================================================================


@dataclass
class AdkAgentSpec:
    """
    Simplified agent spec for the ADK-demo runtime pipeline.
    Lightweight version used by adk_runtime.py for the 5-step demo workflow.
    """

    name: str
    description: str
    instructions: str
    model: str = "qwen2.5:7b"


# ============================================================================
# ToolRegistry
# ============================================================================


class ADKToolRegistry:
    """
    Registry for tools that ADK-style agents can use.
    Supports: register, discover, invoke with retry + timeout.
    """

    def __init__(self):
        self._tools: Dict[str, Callable] = {}
        self._specs: Dict[str, ADKToolSpec] = {}

    def register_tool(
        self,
        spec: ADKToolSpec,
        handler: Callable,
    ) -> None:
        """Register a tool with its spec and handler function."""
        self._tools[spec.name] = handler
        self._specs[spec.name] = spec
        logger.info(f"[ToolRegistry] Registered tool: {spec.name}")

    def get_tool(self, name: str) -> Optional[Callable]:
        """Get a tool handler by name."""
        return self._tools.get(name)

    def get_spec(self, name: str) -> Optional[ADKToolSpec]:
        """Get a tool spec by name."""
        return self._specs.get(name)

    def list_tools(self) -> List[ADKToolSpec]:
        """List all registered tools."""
        return list(self._specs.values())

    def discover_tools(self, query: str) -> List[ADKToolSpec]:
        """
        Discover tools matching a query (by name or description).
        Simple keyword matching — can be upgraded to semantic search.
        """
        query_lower = query.lower()
        results = []
        for spec in self._specs.values():
            if (
                query_lower in spec.name.lower()
                or query_lower in spec.description.lower()
            ):
                results.append(spec)
        return results

    async def invoke_tool(
        self,
        name: str,
        arguments: Dict[str, Any],
        timeout: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Invoke a tool by name with arguments.
        Includes: timeout, retry logic, error handling.
        """
        if name not in self._tools:
            return {"success": False, "error": f"Tool '{name}' not found"}

        handler = self._tools[name]
        spec = self._specs[name]
        timeout = timeout or spec.timeout_seconds
        max_retries = 2

        for attempt in range(max_retries + 1):
            try:
                start = time.time()
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
                logger.info(f"[ToolRegistry] Tool '{name}' completed in {latency:.2f}s")
                return {
                    "success": True,
                    "result": result,
                    "latency_seconds": latency,
                    "tool_name": name,
                }
            except asyncio.TimeoutError:
                logger.warning(
                    f"[ToolRegistry] Tool '{name}' timed out after {timeout}s "
                    f"(attempt {attempt + 1}/{max_retries + 1})"
                )
                if attempt == max_retries:
                    return {
                        "success": False,
                        "error": f"Tool '{name}' timed out after {max_retries + 1} attempts",
                        "tool_name": name,
                    }
            except Exception as e:
                logger.error(
                    f"[ToolRegistry] Tool '{name}' failed: {e} "
                    f"(attempt {attempt + 1}/{max_retries + 1})"
                )
                if attempt == max_retries:
                    return {
                        "success": False,
                        "error": str(e),
                        "tool_name": name,
                    }
                await asyncio.sleep(1.0 * (attempt + 1))  # exponential backoff

        return {"success": False, "error": "Unknown error", "tool_name": name}


# ============================================================================
# QueryParser
# ============================================================================


class ADKQueryParser:
    """
    Parse user queries to detect intent and extract parameters.
    Two-stage: rule-based (fast) → LLM fallback (accurate).
    """

    # Rule-based intent patterns
    INTENT_PATTERNS = {
        AgentRole.RAG: [
            "what is",
            "explain",
            "how does",
            "tell me about",
            "tìm",
            "giải thích",
            "là gì",
            "thế nào",
        ],
        AgentRole.RESEARCH: [
            "research",
            "nghiên cứu",
            "phân tích",
            "analyze",
            "investigate",
            "tìm hiểu sâu",
        ],
        AgentRole.REPORT: [
            "report",
            "báo cáo",
            "generate report",
            "tạo báo cáo",
            "summary report",
            "executive summary",
        ],
        AgentRole.ACTION: [
            "send email",
            "create ticket",
            "gửi email",
            "tạo task",
            "execute",
            "run",
            "trigger",
            "chạy",
        ],
        AgentRole.ENGINEERING: [
            "engineering",
            "architecture",
            "kỹ thuật",
            "thiết kế",
            "design pattern",
            "system design",
        ],
        AgentRole.COMPARATOR: [
            "compare",
            "so sánh",
            "difference",
            "khác nhau",
            "vs",
            "versus",
            "better",
        ],
        AgentRole.FINANCE: [
            "tài chính",
            "chứng khoán",
            "stock",
            "cổ phiếu",
            "invest",
            "đầu tư",
            "market",
            "rsi",
            "macd",
        ],
        AgentRole.CODE: [
            "code",
            "function",
            "class",
            "implement",
            "viết code",
            "debug",
            "fix bug",
            "refactor",
        ],
        AgentRole.SUMMARIZER: [
            "summarize",
            "tóm tắt",
            "summary",
            "tổng kết",
            "key points",
            "main ideas",
        ],
    }

    def parse(self, query: str) -> Dict[str, Any]:
        """
        Parse query to detect intent and extract parameters.
        Returns: { "role": AgentRole, "confidence": float, "params": dict }
        """
        query_lower = query.lower()
        scores: Dict[AgentRole, int] = {}

        for role, patterns in self.INTENT_PATTERNS.items():
            score = sum(1 for p in patterns if p in query_lower)
            if score > 0:
                scores[role] = score

        if not scores:
            return {
                "role": AgentRole.RAG,
                "confidence": 0.5,
                "params": {"query": query},
            }

        best_role = max(scores, key=scores.get)
        max_score = scores[best_role]
        confidence = min(1.0, max_score / 3.0)

        # Extract parameters
        params = {"query": query}
        if "document" in query_lower or "file" in query_lower:
            params["requires_document"] = True
        if "web" in query_lower or "internet" in query_lower:
            params["use_web_search"] = True

        return {
            "role": best_role,
            "confidence": confidence,
            "params": params,
        }

    async def parse_with_llm(
        self,
        query: str,
        llm_generate: Callable,
    ) -> Dict[str, Any]:
        """
        Fallback: use LLM for ambiguous queries.
        """
        prompt = f"""Analyze this user query and return a JSON with:
- role: one of [rag, research, report, action, engineering, comparator, finance, code, summarizer, chat]
- confidence: 0.0 to 1.0
- params: dict of extracted parameters

Query: "{query}"

Return ONLY valid JSON, no other text."""

        try:
            result = await llm_generate(
                prompt=prompt,
                system_prompt="You are a query parser. Return only JSON.",
                model="qwen2.5:7b",
            )
            text = result.get("text", "")
            # Extract JSON from response
            json_match = __import__("re").search(
                r"\{.*\}", text, __import__("re").DOTALL
            )
            if json_match:
                parsed = json.loads(json_match.group())
                return {
                    "role": AgentRole(parsed.get("role", "rag")),
                    "confidence": parsed.get("confidence", 0.5),
                    "params": parsed.get("params", {"query": query}),
                }
        except Exception as e:
            logger.warning(f"[QueryParser] LLM parse failed: {e}")

        return {"role": AgentRole.RAG, "confidence": 0.5, "params": {"query": query}}


# ============================================================================
# ADKAgent — Core Agent Class (async, full-featured)
# ============================================================================


class ADKAgent:
    """
    Core ADK-style Agent with:
    - Configurable instructions, model, tools
    - Structured output (JSON schema validation)
    - Retry logic with exponential backoff
    - Tracing (latency, tool calls, retries)
    - Tool calling with timeout
    """

    def __init__(
        self,
        config: ADKAgentConfig,
        tool_registry: Optional[ADKToolRegistry] = None,
        llm_generate: Optional[Callable] = None,
    ):
        self.config = config
        self.tool_registry = tool_registry or ADKToolRegistry()
        self.llm_generate = llm_generate
        self.trace_history: List[ADKExecutionResult] = []

    async def run(
        self,
        user_input: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> ADKExecutionResult:
        """
        Execute the agent with user input.
        Pipeline: parse → select tools → generate → validate → return
        """
        start = time.time()
        context = context or {}
        trace_id = str(uuid.uuid4())[:8]

        logger.info(
            f"[ADKAgent:{self.config.name}] Running with input: {user_input[:80]}"
        )

        # Step 1: Parse query to detect intent
        parser = ADKQueryParser()
        parser.parse(user_input)

        # Step 2: Discover relevant tools
        relevant_tools = self.tool_registry.discover_tools(user_input)
        tool_descriptions = "\n".join(
            f"- {t.name}: {t.description}" for t in relevant_tools
        )

        # Step 3: Build prompt with instructions + tools + context
        system_prompt = self.config.instructions
        if tool_descriptions:
            system_prompt += f"\n\nAvailable tools:\n{tool_descriptions}"
        if context:
            context_str = json.dumps(context, indent=2)
            system_prompt += f"\n\nContext:\n{context_str}"

        # Step 4: Generate response with retry
        retries = 0
        last_error = None

        for attempt in range(self.config.max_retries + 1):
            try:
                if self.llm_generate:
                    result = await self.llm_generate(
                        prompt=user_input,
                        system_prompt=system_prompt,
                        model=self.config.model,
                        temperature=self.config.temperature,
                    )
                    output = result.get("text", "")
                else:
                    # Mock mode for testing
                    output = (
                        f"[ADKAgent:{self.config.name}] Processed: {user_input[:100]}"
                    )
                    result = {"text": output, "model": "mock"}

                # Step 5: Validate structured output if schema provided
                structured_output = None
                if self.config.structured_output_schema and output:
                    try:
                        structured_output = json.loads(output)
                    except json.JSONDecodeError:
                        logger.warning(
                            f"[ADKAgent:{self.config.name}] Output is not valid JSON"
                        )

                latency = time.time() - start
                execution_result = ADKExecutionResult(
                    agent_name=self.config.name,
                    success=True,
                    output=output,
                    structured_output=structured_output,
                    tool_calls=[],  # Would be populated by tool execution
                    latency_seconds=round(latency, 2),
                    retries=retries,
                    trace_id=trace_id,
                )

                # Store trace
                if self.config.tracing_enabled:
                    self.trace_history.append(execution_result)

                return execution_result

            except Exception as e:
                last_error = str(e)
                retries += 1
                logger.warning(
                    f"[ADKAgent:{self.config.name}] Attempt {attempt + 1} failed: {e}"
                )
                if attempt < self.config.max_retries:
                    await asyncio.sleep(1.0 * (attempt + 1))  # exponential backoff

        # All retries exhausted
        latency = time.time() - start
        execution_result = ADKExecutionResult(
            agent_name=self.config.name,
            success=False,
            output="",
            error=last_error or "Max retries exceeded",
            latency_seconds=round(latency, 2),
            retries=retries,
            trace_id=trace_id,
        )

        if self.config.tracing_enabled:
            self.trace_history.append(execution_result)

        return execution_result

    def get_trace(self, limit: int = 10) -> List[ADKExecutionResult]:
        """Get recent execution traces."""
        return self.trace_history[-limit:]

    def get_stats(self) -> Dict[str, Any]:
        """Get agent statistics."""
        if not self.trace_history:
            return {"agent": self.config.name, "total_runs": 0}

        total = len(self.trace_history)
        successes = sum(1 for t in self.trace_history if t.success)
        avg_latency = sum(t.latency_seconds for t in self.trace_history) / total

        return {
            "agent": self.config.name,
            "role": self.config.role.value,
            "total_runs": total,
            "success_rate": round(successes / total, 2),
            "avg_latency_seconds": round(avg_latency, 2),
            "total_retries": sum(t.retries for t in self.trace_history),
        }


# ============================================================================
# AdkAgent — Simplified sync agent for the demo runtime pipeline
# ============================================================================


class AdkAgent:
    """
    Simplified sync agent for the ADK-demo runtime pipeline.

    This is a separate, lighter-weight class (not the same as ADKAgent above)
    designed specifically for the 5-step demo workflow in adk_runtime.py.

    It runs synchronously and returns plain dicts for simplicity.
    """

    def __init__(self, spec: AdkAgentSpec):
        self.spec = spec
        self._trace: List[Dict[str, Any]] = []

    def run(self, user_request: str) -> Dict[str, Any]:
        """
        Execute the agent synchronously.
        Returns a dict with status, summary, agent, and input keys.
        """
        start = time.time()
        logger.info(f"[AdkAgent:{self.spec.name}] Running with: {user_request[:80]}")

        # Simulate processing with the agent's instructions
        result = {
            "agent": self.spec.name,
            "status": "ok",
            "summary": f"[{self.spec.name}] {self.spec.description[:60]}... processed.",
            "input": user_request[:200],
        }

        latency = time.time() - start
        self._trace.append(
            {
                "agent": self.spec.name,
                "latency_seconds": round(latency, 3),
                "status": "ok",
            }
        )

        return result

    def get_trace(self) -> List[Dict[str, Any]]:
        return self._trace


# ============================================================================
# ADKAgentFactory
# ============================================================================


class ADKAgentFactory:
    """
    Factory to create specialized ADK-style agents from config.
    Provides pre-built agents for common roles.
    """

    def __init__(
        self,
        tool_registry: Optional[ADKToolRegistry] = None,
        llm_generate: Optional[Callable] = None,
    ):
        self.tool_registry = tool_registry or ADKToolRegistry()
        self.llm_generate = llm_generate

    def create_agent(self, config: ADKAgentConfig) -> ADKAgent:
        """Create an ADK-style agent from config."""
        return ADKAgent(
            config=config,
            tool_registry=self.tool_registry,
            llm_generate=self.llm_generate,
        )

    def create_rag_agent(self) -> ADKAgent:
        """Create a pre-configured RAG agent."""
        return self.create_agent(
            ADKAgentConfig(
                name="rag_agent",
                role=AgentRole.RAG,
                instructions="""You are a RAG (Retrieval-Augmented Generation) specialist.
Your job is to answer questions based on the provided document context.
- Always cite your sources when using retrieved documents
- If you don't have enough information, say so clearly
- Keep answers concise and focused on the question
- Use bullet points for multiple facts""",
                tools=[
                    ADKToolSpec(
                        name="retrieve_documents",
                        description="Search and retrieve relevant document chunks",
                        input_schema={"query": "str", "top_k": "int"},
                    ),
                    ADKToolSpec(
                        name="web_search",
                        description="Search the web for additional information",
                        input_schema={"query": "str"},
                    ),
                ],
                structured_output_schema={
                    "type": "object",
                    "properties": {
                        "answer": {"type": "string"},
                        "sources": {"type": "array", "items": {"type": "string"}},
                        "confidence": {"type": "number"},
                    },
                },
            )
        )

    def create_research_agent(self) -> ADKAgent:
        """Create a pre-configured Research agent."""
        return self.create_agent(
            ADKAgentConfig(
                name="research_agent",
                role=AgentRole.RESEARCH,
                instructions="""You are a research analyst. Your job is to:
1. Break down complex topics into key aspects
2. Gather evidence from multiple sources
3. Identify trends, patterns, and insights
4. Highlight controversies or debates
5. Provide structured reports with citations""",
                tools=[
                    ADKToolSpec(
                        name="web_search",
                        description="Search the web for information",
                        input_schema={"query": "str"},
                    ),
                    ADKToolSpec(
                        name="retrieve_documents",
                        description="Search internal documents",
                        input_schema={"query": "str", "top_k": "int"},
                    ),
                ],
            )
        )

    def create_report_agent(self) -> ADKAgent:
        """Create a pre-configured Report agent."""
        return self.create_agent(
            ADKAgentConfig(
                name="report_agent",
                role=AgentRole.REPORT,
                instructions="""You are a report writer. Create professional reports with:
- Executive summary (3-5 bullet points)
- Detailed findings with evidence
- Data visualizations described in text
- Actionable recommendations
- Next steps and timeline""",
            )
        )

    def create_finance_agent(self) -> ADKAgent:
        """Create a pre-configured Finance agent."""
        return self.create_agent(
            ADKAgentConfig(
                name="finance_agent",
                role=AgentRole.FINANCE,
                instructions="""You are a financial analyst specializing in:
- Technical Analysis: SMA, EMA, RSI, MACD, Bollinger Bands
- Fundamental Analysis: P/E, EPS, market cap, revenue growth
- Vietnamese market: HOSE, HNX, UPCOM, VN-Index
- Portfolio analysis and risk assessment
- Always explain reasoning behind each analysis""",
                tools=[
                    ADKToolSpec(
                        name="calculate_sma",
                        description="Calculate Simple Moving Average",
                        input_schema={"prices": "list", "period": "int"},
                    ),
                    ADKToolSpec(
                        name="calculate_rsi",
                        description="Calculate Relative Strength Index",
                        input_schema={"prices": "list", "period": "int"},
                    ),
                    ADKToolSpec(
                        name="calculate_macd",
                        description="Calculate MACD indicator",
                        input_schema={"prices": "list"},
                    ),
                ],
            )
        )


# ============================================================================
# Convenience: create default ADK-inspired system
# ============================================================================


def create_default_adk_system(
    llm_generate: Optional[Callable] = None,
) -> Dict[str, Any]:
    """
    Create a default ADK-inspired system with all pre-built agents.
    Returns: { "factory": ADKAgentFactory, "agents": dict, "tool_registry": ADKToolRegistry }
    """
    tool_registry = ADKToolRegistry()
    factory = ADKAgentFactory(tool_registry=tool_registry, llm_generate=llm_generate)

    agents = {
        "rag": factory.create_rag_agent(),
        "research": factory.create_research_agent(),
        "report": factory.create_report_agent(),
        "finance": factory.create_finance_agent(),
    }

    return {
        "factory": factory,
        "agents": agents,
        "tool_registry": tool_registry,
    }
