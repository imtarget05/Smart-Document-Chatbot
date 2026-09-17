"""LangGraph agent graph (Phase 0 → 2): intent -> execute tool -> answer.

Stateful multi-step agent cho document tools (module dự báo đã gỡ).
- execute_tool_node trả deterministic/abstain cho các tool cũ
  (không hallucinate, không gọi HTTP ngoài).
- Mỗi node tạo Langfuse span (joined vào trace backend qua X-Langfuse-Trace-Id)
  khi observability được enable.
"""

import operator
from typing import Annotated, Any, Dict, Optional, Sequence, TypedDict

from langgraph.graph import END, StateGraph

try:  # chạy như top-level package (uvicorn app.main:app từ llm-router/)
    from app import observability
except (ImportError, ValueError):  # agent được import như sub-package của root package
    try:
        from ..app import observability
    except (ImportError, ValueError):
        from llm_router.app import observability


class AgentState(TypedDict):
    messages: Annotated[Sequence, operator.add]
    tool_choice: str
    tool_params: Dict[str, Any]
    tool_result: Dict[str, Any]
    final_answer: str
    trace_id: Optional[str]
    parent_span_id: Optional[str]


# Các tool chuỗi cung ứng cũ đã gỡ backend: trả abstain xác định.
UNSUPPORTED_LEGACY_TOOLS = frozenset({
    "forecast_demand",
    "optimize_delivery_route",
    "check_supplier_risk",
})


def _last_message(state: AgentState) -> str:
    msgs = state.get("messages") or []
    if not msgs:
        return ""
    last = msgs[-1]
    return getattr(last, "content", None) or (last.get("content") if isinstance(last, dict) else "")


async def intent_node(state: AgentState) -> Dict[str, Any]:
    obs_id, obs = observability.span(
        state.get("trace_id"), "agent_intent",
        parent_observation_id=state.get("parent_span_id"),
        input={"message": _last_message(state)[:200]},
    )
    msg = _last_message(state).lower()
    if "dự báo" in msg or "forecast" in msg:
        choice = "forecast_demand"
    elif "tuyến" in msg or "route" in msg or "giao hàng" in msg:
        choice = "optimize_delivery_route"
    elif "rủi ro" in msg or "supplier" in msg or "nhà cung cấp" in msg:
        choice = "check_supplier_risk"
    elif "tài liệu" in msg or "document" in msg or "search" in msg:
        choice = "doc_search"
    else:
        choice = "none"
    observability.end_span(obs, output={"tool_choice": choice})
    return {"tool_choice": choice}


async def execute_tool_node(state: AgentState) -> Dict[str, Any]:
    tool = state.get("tool_choice", "none")
    if tool == "none":
        result = {"status": "skipped", "tool": "none"}
    elif tool in UNSUPPORTED_LEGACY_TOOLS:
        # Module dự báo đã gỡ: deterministic abstain, không gọi API ngoài.
        result = {
            "status": "unsupported",
            "source": "deterministic_abstain",
            "tool": tool,
            "detail": "không hỗ trợ dự báo chuỗi cung ứng",
        }
    elif tool == "doc_search":
        # doc_search noi API that: reuse document workflow hien co.
        try:
            try:  # chay nhu top-level package (tu llm-router/)
                from agent.document_graph import run_document_workflow
            except (ImportError, ValueError):
                try:
                    from .document_graph import run_document_workflow
                except (ImportError, ValueError):
                    from llm_router.agent.document_graph import run_document_workflow
            params = state.get("tool_params") or {}
            data = run_document_workflow(
                text=params.get("text", ""),
                filename=params.get("filename", ""),
                counterpart_fields=params.get("counterpart_fields"),
            )
            result = {
                "status": "ok",
                "source": "document_workflow",
                "tool": tool,
                "data": data,
            }
        except Exception as exc:
            result = {
                "status": "error",
                "source": "document_workflow",
                "tool": tool,
                "detail": str(exc),
            }
    else:
        # Tool chua noi API — deterministic placeholder
        result = {"status": "mock", "source": "deterministic_fallback", "tool": tool}
    return {"tool_result": result}


async def generate_answer_node(state: AgentState) -> Dict[str, Any]:
    obs_id, obs = observability.span(
        state.get("trace_id"), "agent_answer",
        parent_observation_id=state.get("parent_span_id"),
        input={"tool": state.get("tool_choice")},
    )
    result = state.get("tool_result") or {}
    tool = state.get("tool_choice", "none")
    if tool == "none":
        answer = (
            "Xin chào! Tôi có thể giúp bạn tìm kiếm tài liệu."
        )
    elif result.get("status") == "unsupported":
        answer = (
            f"Không hỗ trợ dự báo chuỗi cung ứng với công cụ '{tool}' — "
            f"không đưa ra dự đoán thiếu nguồn. Chi tiết: {result.get('detail')}"
        )
    elif result.get("status") == "ok":
        answer = (
            f"Kết quả từ công cụ '{tool}': "
            f"{result.get('data')}"
        )
    else:
        detail = result.get("detail") or result.get("status")
        answer = (
            f"Không thể lấy dữ liệu thực từ công cụ '{tool}' — không đưa ra "
            f"dự đoán thiếu nguồn. Chi tiết: {detail}"
        )
    observability.end_span(obs, output={"answer": answer[:200]})
    return {"final_answer": answer}


def build_agent_app():
    graph = StateGraph(AgentState)
    graph.add_node("intent", intent_node)
    graph.add_node("execute", execute_tool_node)
    graph.add_node("answer", generate_answer_node)
    graph.set_entry_point("intent")
    graph.add_edge("intent", "execute")
    graph.add_edge("execute", "answer")
    graph.add_edge("answer", END)
    return graph.compile()


agent_app = build_agent_app()


async def run_agent(message: str, trace_id: Optional[str] = None,
                    tool_params: Optional[dict] = None) -> str:
    """Chạy agent graph; mỗi node span vào Langfuse trace nếu có trace_id."""
    root_id, root = observability.span(
        trace_id, "agent_run", input={"message": message[:200]}
    )
    initial_state: AgentState = {
        "messages": [{"role": "user", "content": message}],
        "tool_choice": "",
        "tool_params": tool_params or {},
        "tool_result": {},
        "final_answer": "",
        "trace_id": trace_id,
        "parent_span_id": root_id,
    }
    try:
        result = await agent_app.ainvoke(initial_state)
        observability.end_span(root, output={"answer": result["final_answer"][:200]})
        return result["final_answer"]
    except Exception as exc:
        observability.end_span(root, error=str(exc))
        raise