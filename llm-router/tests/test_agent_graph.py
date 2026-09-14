"""Tests for agent/graph.py LangGraph agent workflow."""

import pytest
from agent.graph import run_agent


@pytest.mark.asyncio
async def test_run_agent_greeting():
    answer = await run_agent("Xin chào bạn!")
    assert "Xin chào!" in answer
    assert "dự báo nhu cầu" in answer


@pytest.mark.asyncio
async def test_run_agent_forecast_fallback():
    answer = await run_agent("Dự báo nhu cầu hàng hóa tuần tới")
    assert "forecast_demand" in answer
    assert "SUPPLY_CHAIN_API_URL chưa cấu hình" in answer or "Không thể lấy dữ liệu" in answer


@pytest.mark.asyncio
async def test_run_agent_route_fallback():
    answer = await run_agent("Tối ưu tuyến đường giao hàng")
    assert "optimize_delivery_route" in answer


@pytest.mark.asyncio
async def test_run_agent_supplier_risk_fallback():
    answer = await run_agent("Kiểm tra rủi ro nhà cung cấp")
    assert "check_supplier_risk" in answer
