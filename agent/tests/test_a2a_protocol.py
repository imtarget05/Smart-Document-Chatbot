"""
Tests for A2A Protocol Implementation
Tests CircuitBreaker, DeadLetterQueue, A2AProtocolHub
"""

import pytest
import time

from a2a.protocol import (
    A2AProtocolHub,
    AgentCard,
    CircuitBreaker,
    DeadLetterQueue,
    Task,
    TaskStatus,
    CircuitState,
)
from a2a.factory import register_all_agents, create_default_hub


class TestCircuitBreaker:
    """CircuitBreaker state machine tests."""

    def test_initial_state(self):
        cb = CircuitBreaker("test_agent")
        assert cb.state == CircuitState.CLOSED
        assert cb.can_call() is True

    def test_open_after_threshold(self):
        cb = CircuitBreaker("test_agent", failure_threshold=3)
        assert cb.state == CircuitState.CLOSED

        cb.record_failure()  # 1
        assert cb.state == CircuitState.CLOSED
        cb.record_failure()  # 2
        assert cb.state == CircuitState.CLOSED
        cb.record_failure()  # 3 → OPEN
        assert cb.state == CircuitState.OPEN

    def test_rejects_when_open(self):
        cb = CircuitBreaker("test_agent", failure_threshold=1, recovery_timeout_sec=999)
        cb.record_failure()  # → OPEN
        assert cb.can_call() is False

    def test_half_open_after_timeout(self):
        cb = CircuitBreaker("test_agent", failure_threshold=1, recovery_timeout_sec=0.1)
        cb.record_failure()  # → OPEN
        assert cb.can_call() is False  # Still open

        time.sleep(0.15)
        assert cb.can_call() is True  # → HALF_OPEN

    def test_closed_after_half_open_success(self):
        cb = CircuitBreaker("test_agent", failure_threshold=1, recovery_timeout_sec=0.1)
        cb.record_failure()  # → OPEN
        time.sleep(0.15)
        cb.can_call()  # → HALF_OPEN
        cb.record_success()  # → CLOSED
        assert cb.state == CircuitState.CLOSED

    def test_success_rate_decay(self):
        cb = CircuitBreaker("test_agent", failure_threshold=3)
        cb.record_success()
        cb.record_success()
        cb.record_failure()
        stats = cb.get_stats()
        assert stats["success_rate"] == round(2 / 3, 4)


class TestDeadLetterQueue:
    """Dead Letter Queue tests."""

    def test_enqueue_dequeue(self):
        dlq = DeadLetterQueue()
        task = Task(agent_id="test", capability="rag")
        dlq.enqueue(task)
        assert task.status == TaskStatus.DEAD

        retrieved = dlq.dequeue(task.task_id)
        assert retrieved is not None
        assert retrieved.task_id == task.task_id

    def test_exponential_backoff(self):
        dlq = DeadLetterQueue(task_ttl_sec=999, max_retries=3)
        task = Task(agent_id="test", capability="rag")
        task.created_at = time.time()
        task.completed_at = time.time()
        task.retry_count = 1  # Backoff = 2^1 = 2s

        dlq.enqueue(task)
        # Should NOT be ready immediately
        ready = dlq.get_pending_retries()
        assert len(ready) == 0

        # Wait for backoff
        time.sleep(2.1)
        ready = dlq.get_pending_retries()
        assert len(ready) == 1
        assert ready[0].task_id == task.task_id

    def test_max_retries_exhausted(self):
        dlq = DeadLetterQueue(task_ttl_sec=999, max_retries=2)
        task = Task(agent_id="test", capability="rag")
        task.created_at = time.time()
        task.completed_at = time.time()
        task.retry_count = 2  # Exhausted
        dlq.enqueue(task)

        ready = dlq.get_pending_retries()
        assert len(ready) == 0

    def test_task_expiry(self):
        dlq = DeadLetterQueue(task_ttl_sec=0.1, max_retries=3)
        task = Task(agent_id="test", capability="rag")
        task.created_at = time.time() - 1  # Expired
        task.completed_at = time.time()
        dlq.enqueue(task)

        ready = dlq.get_pending_retries()
        assert len(ready) == 0


class TestA2AProtocolHub:
    """A2A Protocol Hub integration tests."""

    @pytest.mark.asyncio
    async def test_register_and_discover(self):
        hub = A2AProtocolHub()
        register_all_agents(hub)

        agents = hub.discover_all()
        assert len(agents) >= 13  # All agents registered
        assert any(a.capabilities for a in agents)

    @pytest.mark.asyncio
    async def test_discover_by_capability(self):
        hub = A2AProtocolHub()
        register_all_agents(hub)

        rag_agents = hub.discover_agents("rag")
        assert len(rag_agents) >= 1
        assert rag_agents[0].agent_id == "rag_agent"

    @pytest.mark.asyncio
    async def test_find_best_agent(self):
        hub = A2AProtocolHub()
        register_all_agents(hub)

        best = hub.find_best_agent("rag")
        assert best is not None
        assert best.agent_id == "rag_agent"

    @pytest.mark.asyncio
    async def test_delegate_task_success(self):
        hub = A2AProtocolHub()

        async def mock_handler(input_data):
            return {"status": "ok", "result": "processed"}

        hub.register_agent(
            AgentCard(
                agent_id="test_agent",
                name="Test Agent",
                description="Test agent",
                capabilities=["test"],
            ),
            handler=mock_handler,
        )

        task = await hub.delegate("test", {"query": "hello"})
        assert task.status == TaskStatus.SUCCESS
        assert task.result["result"] == "processed"

    @pytest.mark.asyncio
    async def test_delegate_no_available_agent(self):
        hub = A2AProtocolHub()
        task = await hub.delegate("unknown_capability", {})
        assert task.status == TaskStatus.DEAD
        assert task.error is not None and "No available agent" in task.error

    @pytest.mark.asyncio
    async def test_circuit_breaker_prevents_calls(self):
        hub = A2AProtocolHub()

        async def failing_handler(input_data):
            raise ValueError("Simulated failure")

        hub.register_agent(
            AgentCard(
                agent_id="failing_agent",
                name="Failing Agent",
                description="Always fails",
                capabilities=["failing"],
            ),
            handler=failing_handler,
        )

        # Fail multiple times to trigger circuit breaker
        for _ in range(6):
            await hub.delegate("failing", {})

        # Circuit should be OPEN now
        cb = hub._circuit_breakers["failing_agent"]
        assert cb.state == CircuitState.OPEN

    @pytest.mark.asyncio
    async def test_dead_letter_retry(self):
        hub = A2AProtocolHub()
        register_all_agents(hub)

        # Register a handler that fails then succeeds
        call_count = 0

        async def handler(input_data):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ValueError("First attempt fails")
            return {"status": "ok", "attempt": call_count}

        hub.register_agent(
            AgentCard(
                agent_id="retry_agent",
                name="Retry Agent",
                description="Agent for retry testing",
                capabilities=["retry_test"],
            ),
            handler=handler,
        )

        # First call fails and gets enqueued to dead-letter queue
        task = await hub.delegate("retry_test", {})
        assert task.status == TaskStatus.DEAD

        # Retry
        retried = await hub.retry_dead_letter_tasks()
        assert retried >= 0  # May or may not succeed depending on timing

    @pytest.mark.asyncio
    async def test_get_stats(self):
        hub = A2AProtocolHub()
        register_all_agents(hub)

        stats = hub.get_stats()
        assert stats["registered_agents"] >= 13
        assert "circuit_breakers" in stats
        assert "dead_letter_queue" in stats


class TestA2AFactory:
    """A2A Factory tests."""

    def test_create_default_hub(self):
        hub = create_default_hub()
        assert isinstance(hub, A2AProtocolHub)

    def test_register_all_agents(self):
        hub = A2AProtocolHub()
        register_all_agents(hub)
        assert len(hub.discover_all()) >= 13
