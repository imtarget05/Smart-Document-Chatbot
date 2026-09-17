"""RED: doc_search phai noi API that (document workflow), khong status:mock."""

import pytest
from agent.graph import execute_tool_node


@pytest.mark.asyncio
async def test_doc_search_calls_real_api_not_mock():
    state = {
        "messages": [],
        "tool_choice": "doc_search",
        "tool_params": {
            "text": "PURCHASE ORDER\nPO #PO-2024-001\nVendor: ABC Trading Corp\n"
                    "Order date: 15/03/2024\nTotal amount: 1,500 USD",
            "filename": "po.pdf",
        },
        "tool_result": {},
        "final_answer": "",
        "trace_id": None,
        "parent_span_id": None,
    }
    result = await execute_tool_node(state)
    tool_result = result["tool_result"]
    assert tool_result.get("status") != "mock", f"van tra mock: {tool_result}"
    assert tool_result.get("status") == "ok"
    assert tool_result.get("tool") == "doc_search"
    # du lieu that tu document workflow (extract that, khong phai placeholder)
    assert tool_result["data"]["doc_type"] == "PO"
    assert tool_result["data"]["fields"]["po_number"] == "PO-2024-001"
