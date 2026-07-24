"""
A2A Protocol — Agent-to-Agent communication layer.
==================================================
Core components:
  - AgentCard: metadata + capability description for each agent
  - A2AProtocolHub: discovery, capability indexing, task delegation
  - CircuitBreaker: auto-stops calling failing agents
  - DeadLetterQueue: stores failed tasks for retry with exponential backoff
"""

import asyncio
import inspect
import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


# ============================================================================
# Enums & Data Models
# ============================================================================


class CircuitState(str, Enum):
    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing — reject calls immediately
    HALF_OPEN = "half_open"  # Testing if service recovered


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    RETRYING = "retrying"
    DEAD = "dead"  # Moved to dead-letter queue


@dataclass
class AgentCard:
    """
    Agent metadata card — describes what an agent can do.
    Used for discovery and capability matching.
    """

    agent_id: str
    name: str
    description: str
    capabilities: List[str]  # e.g. ["rag", "research", "finance"]
    input_schema: Optional[Dict[str, Any]] = None
    output_schema: Optional[Dict[str, Any]] = None
    version: str = "1.0.0"
    endpoint: str = ""  # Internal routing key or URL
    max_concurrent_tasks: int = 5
    avg_latency_ms: float = 0.0
    success_rate: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "description": self.description,
            "capabilities": self.capabilities,
            "version": self.version,
            "endpoint": self.endpoint,
            "max_concurrent_tasks": self.max_concurrent_tasks,
            "avg_latency_ms": round(self.avg_latency_ms, 2),
            "success_rate": round(self.success_rate, 4),
        }


@dataclass
class Task:
    """A unit of work to be delegated to an agent."""

    task_id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    agent_id: str = ""
    capability: str = ""
    input_data: Dict[str, Any] = field(default_factory=dict)
    status: TaskStatus = TaskStatus.PENDING
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: float = 0.0
    started_at: float = 0.0
    completed_at: float = 0.0
    retry_count: int = 0
    max_retries: int = 3
    source_agent: str = ""  # Which agent delegated this task

    def latency_ms(self) -> float:
        if self.completed_at and self.started_at:
            return (self.completed_at - self.started_at) * 1000
        return 0.0


# ============================================================================
# Circuit Breaker
# ============================================================================


class CircuitBreaker:
    """
    Circuit Breaker pattern for agent-to-agent calls.

    States:
      CLOSED  → normal operation, calls pass through
      OPEN    → failure threshold exceeded, calls rejected immediately
      HALF_OPEN → after timeout, one test call allowed

    If test call succeeds → back to CLOSED
    If test call fails → back to OPEN with longer timeout
    """

    def __init__(
        self,
        agent_id: str,
        failure_threshold: int = 5,
        recovery_timeout_sec: float = 30.0,
        half_open_max_calls: int = 1,
    ):
        self.agent_id = agent_id
        self.failure_threshold = failure_threshold
        self.recovery_timeout_sec = recovery_timeout_sec
        self.half_open_max_calls = half_open_max_calls

        self.state: CircuitState = CircuitState.CLOSED
        self.failure_count: int = 0
        self.last_failure_time: float = 0.0
        self.half_open_calls: int = 0
        self.total_calls: int = 0
        self.total_failures: int = 0

    def record_success(self):
        """Record a successful call."""
        self.total_calls += 1
        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.CLOSED
            self.failure_count = 0
            self.half_open_calls = 0
            logger.info(
                f"[CircuitBreaker:{self.agent_id}] HALF_OPEN→CLOSED (recovered)"
            )
        elif self.state == CircuitState.CLOSED:
            self.failure_count = max(0, self.failure_count - 1)  # Slow decay

    def record_failure(self):
        """Record a failed call."""
        self.total_calls += 1
        self.total_failures += 1
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.OPEN
            self.half_open_calls = 0
            logger.warning(
                f"[CircuitBreaker:{self.agent_id}] HALF_OPEN→OPEN "
                f"(test call failed, {self.failure_count}/{self.failure_threshold})"
            )
        elif (
            self.state == CircuitState.CLOSED
            and self.failure_count >= self.failure_threshold
        ):
            self.state = CircuitState.OPEN
            logger.warning(
                f"[CircuitBreaker:{self.agent_id}] CLOSED→OPEN "
                f"(threshold {self.failure_threshold} exceeded)"
            )

    def can_call(self) -> bool:
        """Check if a call is allowed through the circuit breaker."""
        if self.state == CircuitState.CLOSED:
            return True

        if self.state == CircuitState.OPEN:
            # Check if recovery timeout has elapsed
            if time.time() - self.last_failure_time >= self.recovery_timeout_sec:
                self.state = CircuitState.HALF_OPEN
                self.half_open_calls = 0
                logger.info(
                    f"[CircuitBreaker:{self.agent_id}] OPEN→HALF_OPEN (timeout elapsed)"
                )
                return True
            return False

        if self.state == CircuitState.HALF_OPEN:
            if self.half_open_calls < self.half_open_max_calls:
                self.half_open_calls += 1
                return True
            return False

        return False

    def get_stats(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "failure_threshold": self.failure_threshold,
            "total_calls": self.total_calls,
            "total_failures": self.total_failures,
            "success_rate": round(
                (self.total_calls - self.total_failures) / max(self.total_calls, 1), 4
            ),
            "recovery_timeout_sec": self.recovery_timeout_sec,
        }


# ============================================================================
# Dead Letter Queue
# ============================================================================


class DeadLetterQueue:
    """
    Stores failed tasks for later retry with exponential backoff.

    Features:
    - Max retries per task
    - Exponential backoff (1s, 2s, 4s, 8s, ...)
    - Automatic retry scheduling
    - Task expiry (discard tasks older than TTL)
    """

    def __init__(self, task_ttl_sec: float = 3600.0, max_retries: int = 3):
        self._queue: Dict[str, Task] = {}
        self._task_ttl_sec = task_ttl_sec
        self._max_retries = max_retries

    def enqueue(self, task: Task) -> None:
        """Add a failed task to the dead-letter queue."""
        task.status = TaskStatus.DEAD
        task.retry_count = 0
        self._queue[task.task_id] = task
        logger.info(
            f"[DeadLetterQueue] Enqueued task {task.task_id} "
            f"(agent={task.agent_id}, capability={task.capability})"
        )

    def dequeue(self, task_id: str) -> Optional[Task]:
        """Remove and return a task from the queue."""
        return self._queue.pop(task_id, None)

    def get_pending_retries(self) -> List[Task]:
        """
        Get tasks that are ready for retry based on exponential backoff.
        Backoff: 2^retry_count seconds since last attempt.
        """
        now = time.time()
        ready: List[Task] = []
        expired: List[str] = []

        for task_id, task in self._queue.items():
            # Check expiry
            if now - task.created_at > self._task_ttl_sec:
                expired.append(task_id)
                continue

            # Check if ready for retry
            if task.retry_count >= self._max_retries:
                continue  # Exhausted retries, keep in queue for inspection

            backoff_sec = 2**task.retry_count  # 1, 2, 4, 8, ...
            if now - task.completed_at >= backoff_sec:
                ready.append(task)

        # Clean expired tasks
        for tid in expired:
            logger.warning(
                f"[DeadLetterQueue] Task {tid} expired (TTL={self._task_ttl_sec}s)"
            )
            del self._queue[tid]

        return ready

    def mark_retried(self, task: Task) -> None:
        """Mark a task as having been retried."""
        task.retry_count += 1
        task.status = TaskStatus.RETRYING
        if task.retry_count >= self._max_retries:
            logger.warning(
                f"[DeadLetterQueue] Task {task.task_id} exhausted retries "
                f"({self._max_retries}/{self._max_retries})"
            )

    def get_all_tasks(self) -> List[Task]:
        return list(self._queue.values())

    def stats(self) -> Dict[str, Any]:
        return {
            "total_tasks": len(self._queue),
            "max_retries": self._max_retries,
            "task_ttl_sec": self._task_ttl_sec,
        }


# ============================================================================
# A2A Protocol Hub
# ============================================================================


class A2AProtocolHub:
    """
    Central hub for agent-to-agent communication.

    Responsibilities:
    1. Agent Registry — register, discover agents by capability
    2. Capability Indexing — map capabilities → agent IDs
    3. Task Delegation — route tasks to appropriate agents
    4. Circuit Breaking — protect against failing agents
    5. Dead Letter Queue — retry failed tasks
    """

    def __init__(self):
        self._agents: Dict[str, AgentCard] = {}
        self._capability_index: Dict[str, Set[str]] = {}  # capability → {agent_ids}
        self._circuit_breakers: Dict[str, CircuitBreaker] = {}
        self._dead_letter_queue = DeadLetterQueue()
        self._agent_handlers: Dict[str, Callable] = {}  # agent_id → callable
        self._active_tasks: Dict[str, Task] = {}

    # ------------------------------------------------------------------
    # Agent Registration
    # ------------------------------------------------------------------

    def register_agent(
        self,
        card: AgentCard,
        handler: Optional[Callable] = None,
    ) -> None:
        """Register an agent with its card and optional handler function."""
        self._agents[card.agent_id] = card
        self._circuit_breakers[card.agent_id] = CircuitBreaker(agent_id=card.agent_id)

        # Index capabilities
        for cap in card.capabilities:
            if cap not in self._capability_index:
                self._capability_index[cap] = set()
            self._capability_index[cap].add(card.agent_id)

        if handler:
            self._agent_handlers[card.agent_id] = handler

        logger.info(
            f"[A2AProtocolHub] Registered agent '{card.name}' "
            f"(id={card.agent_id}, capabilities={card.capabilities})"
        )

    def unregister_agent(self, agent_id: str) -> None:
        """Remove an agent from the registry."""
        card = self._agents.pop(agent_id, None)
        if card:
            for cap in card.capabilities:
                if cap in self._capability_index:
                    self._capability_index[cap].discard(agent_id)
            self._circuit_breakers.pop(agent_id, None)
            self._agent_handlers.pop(agent_id, None)
            logger.info(f"[A2AProtocolHub] Unregistered agent '{agent_id}'")

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------

    def discover_agents(self, capability: str) -> List[AgentCard]:
        """Find all agents that can handle a given capability."""
        agent_ids = self._capability_index.get(capability, set())
        return [self._agents[aid] for aid in agent_ids if aid in self._agents]

    def discover_all(self) -> List[AgentCard]:
        """List all registered agents."""
        return list(self._agents.values())

    def get_agent(self, agent_id: str) -> Optional[AgentCard]:
        return self._agents.get(agent_id)

    def find_best_agent(self, capability: str) -> Optional[AgentCard]:
        """
        Find the best agent for a capability based on success rate and latency.
        Returns None if no agent available or all circuits are open.
        """
        candidates = self.discover_agents(capability)
        if not candidates:
            return None

        # Filter out agents with open circuits
        available = [
            c
            for c in candidates
            if self._circuit_breakers.get(
                c.agent_id, CircuitBreaker(c.agent_id)
            ).can_call()
        ]
        if not available:
            logger.warning(
                f"[A2AProtocolHub] All agents for '{capability}' are circuit-open"
            )
            return None

        # Sort by success_rate desc, then avg_latency_ms asc
        available.sort(key=lambda c: (-c.success_rate, c.avg_latency_ms))
        return available[0]

    # ------------------------------------------------------------------
    # Task Delegation
    # ------------------------------------------------------------------

    async def delegate(
        self,
        capability: str,
        input_data: Dict[str, Any],
        source_agent: str = "user",
        max_retries: int = 3,
    ) -> Task:
        """
        Delegate a task to the best agent for a given capability.

        Flow:
        1. Find best agent via capability index
        2. Check circuit breaker
        3. Execute task with timeout
        4. Record success/failure
        5. If failed → enqueue to dead-letter queue for retry
        """
        task = Task(
            capability=capability,
            input_data=input_data,
            source_agent=source_agent,
            max_retries=max_retries,
            created_at=time.time(),
        )

        agent = self.find_best_agent(capability)
        if not agent:
            task.status = TaskStatus.FAILED
            task.error = f"No available agent for capability '{capability}'"
            self._dead_letter_queue.enqueue(task)
            return task

        task.agent_id = agent.agent_id
        cb = self._circuit_breakers.get(agent.agent_id)

        if cb and not cb.can_call():
            task.status = TaskStatus.FAILED
            task.error = f"Circuit breaker OPEN for agent '{agent.name}'"
            self._dead_letter_queue.enqueue(task)
            return task

        # Execute
        task.status = TaskStatus.RUNNING
        task.started_at = time.time()
        self._active_tasks[task.task_id] = task

        try:
            handler = self._agent_handlers.get(agent.agent_id)
            if handler:
                if inspect.iscoroutinefunction(handler):
                    result = await handler(input_data)
                else:
                    result = await asyncio.get_event_loop().run_in_executor(
                        None, lambda: handler(input_data)
                    )
            else:
                # No handler registered — simulate for demo
                await asyncio.sleep(0.1)
                result = {
                    "status": "ok",
                    "agent": agent.name,
                    "summary": f"Processed via {agent.name}",
                }

            task.status = TaskStatus.SUCCESS
            task.result = result
            task.completed_at = time.time()

            # Update agent stats
            agent.avg_latency_ms = (agent.avg_latency_ms * 0.9) + (
                task.latency_ms() * 0.1
            )
            agent.success_rate = (agent.success_rate * 0.95) + (1.0 * 0.05)

            if cb:
                cb.record_success()

            logger.info(
                f"[A2AProtocolHub] Task {task.task_id} delegated to '{agent.name}' "
                f"({task.latency_ms():.0f}ms)"
            )

        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error = str(e)
            task.completed_at = time.time()

            if cb:
                cb.record_failure()

            agent.success_rate = (agent.success_rate * 0.95) + (0.0 * 0.05)

            logger.warning(
                f"[A2AProtocolHub] Task {task.task_id} failed on '{agent.name}': {e}"
            )

            # Enqueue to dead-letter queue for retry
            self._dead_letter_queue.enqueue(task)

        finally:
            self._active_tasks.pop(task.task_id, None)

        return task

    async def retry_dead_letter_tasks(self) -> int:
        """
        Retry all tasks in the dead-letter queue that are ready.
        Returns number of tasks retried.
        """
        ready = self._dead_letter_queue.get_pending_retries()
        retried = 0

        for task in ready:
            self._dead_letter_queue.mark_retried(task)
            logger.info(
                f"[A2AProtocolHub] Retrying task {task.task_id} "
                f"(attempt {task.retry_count}/{task.max_retries})"
            )

            # Re-delegate
            new_task = await self.delegate(
                capability=task.capability,
                input_data=task.input_data,
                source_agent=task.source_agent,
                max_retries=task.max_retries,
            )

            if new_task.status == TaskStatus.SUCCESS:
                self._dead_letter_queue.dequeue(task.task_id)
                retried += 1

        return retried

    # ------------------------------------------------------------------
    # Stats & Monitoring
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        return {
            "registered_agents": len(self._agents),
            "capabilities": {k: list(v) for k, v in self._capability_index.items()},
            "circuit_breakers": {
                aid: cb.get_stats() for aid, cb in self._circuit_breakers.items()
            },
            "dead_letter_queue": self._dead_letter_queue.stats(),
            "active_tasks": len(self._active_tasks),
        }

    def get_agent_stats(self, agent_id: str) -> Optional[Dict[str, Any]]:
        card = self._agents.get(agent_id)
        cb = self._circuit_breakers.get(agent_id)
        if not card:
            return None
        return {
            "card": card.to_dict(),
            "circuit_breaker": cb.get_stats() if cb else None,
        }
