"""
Tests for Prometheus metrics integration.
"""

import pytest

from metrics import (
    request_total,
    request_latency,
    request_in_flight,
    agent_run_total,
    agent_run_latency,
    llm_call_total,
    llm_call_latency,
    llm_tokens_total,
    retrieval_total,
    retrieval_latency,
    retrieval_chunks,
    circuit_breaker_state,
    circuit_breaker_failures,
    memory_operations,
    memory_latency,
    metrics_endpoint,
    track_request,
    track_agent_run,
)


class TestMetricsEndpoint:
    """Metrics endpoint tests."""

    def test_metrics_endpoint_returns_content(self):
        body, status, headers = metrics_endpoint()
        assert status == 200
        assert headers["Content-Type"] == "text/plain; charset=utf-8"
        assert len(body) > 0
        # Should contain prometheus metrics
        assert "# HELP" in body or "# TYPE" in body


class TestMetricsRegistry:
    """Verify all metrics are properly registered."""

    def test_request_metrics_exist(self):
        assert request_total._name == "agent_requests"
        assert request_latency._name == "agent_request_latency_seconds"
        assert request_in_flight._name == "agent_requests_in_flight"

    def test_agent_metrics_exist(self):
        assert agent_run_total._name == "agent_runs"
        assert agent_run_latency._name == "agent_run_latency_seconds"

    def test_llm_metrics_exist(self):
        assert llm_call_total._name == "llm_calls"
        assert llm_call_latency._name == "llm_call_latency_seconds"
        assert llm_tokens_total._name == "llm_tokens"

    def test_retrieval_metrics_exist(self):
        assert retrieval_total._name == "retrieval_requests"
        assert retrieval_latency._name == "retrieval_latency_seconds"
        assert retrieval_chunks._name == "retrieval_chunks_total"

    def test_circuit_breaker_metrics_exist(self):
        assert circuit_breaker_state._name == "circuit_breaker_state"
        assert circuit_breaker_failures._name == "circuit_breaker_failures"

    def test_memory_metrics_exist(self):
        assert memory_operations._name == "memory_operations"
        assert memory_latency._name == "memory_latency_seconds"


class TestMetricsLabels:
    """Verify metrics can be used with labels."""

    def test_request_total_labels(self):
        request_total.labels(
            endpoint="/agent/invoke", agent_type="rag", status="success"
        ).inc()
        # Verify no exception

    def test_agent_run_labels(self):
        agent_run_total.labels(agent_name="rag_agent", status="success").inc()

    def test_llm_call_labels(self):
        llm_call_total.labels(model="qwen2.5:7b", status="success").inc()

    def test_retrieval_labels(self):
        retrieval_total.labels(search_type="hybrid", status="success").inc()

    def test_circuit_breaker_labels(self):
        circuit_breaker_state.labels(agent_id="rag_agent").set(0)
        circuit_breaker_failures.labels(agent_id="rag_agent").inc()

    def test_memory_labels(self):
        memory_operations.labels(
            operation="save", memory_type="short_term", status="success"
        ).inc()


class TestTrackDecorators:
    """Test the tracking decorators."""

    @pytest.mark.asyncio
    async def test_track_request_decorator(self):
        @track_request(endpoint="/test", agent_type="rag")
        async def my_handler():
            return {"status": "ok"}

        result = await my_handler()
        assert result["status"] == "ok"

    @pytest.mark.asyncio
    async def test_track_request_decorator_error(self):
        @track_request(endpoint="/test", agent_type="rag")
        async def failing_handler():
            raise ValueError("test error")

        with pytest.raises(ValueError):
            await failing_handler()

    @pytest.mark.asyncio
    async def test_track_agent_run_decorator(self):
        @track_agent_run(agent_name="test_agent")
        async def my_agent():
            return {"output": "done"}

        result = await my_agent()
        assert result["output"] == "done"
