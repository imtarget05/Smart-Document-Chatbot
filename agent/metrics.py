"""
Prometheus metrics for the agent service.
Exposes /metrics endpoint for Prometheus scraping.
"""

import time
from functools import wraps
from typing import Callable

from prometheus_client import Counter, Gauge, Histogram, generate_latest
from prometheus_client import REGISTRY

# ── Request metrics ──────────────────────────────────────────────────────
request_total = Counter(
    "agent_requests_total",
    "Total agent requests",
    ["endpoint", "agent_type", "status"],
)

request_latency = Histogram(
    "agent_request_latency_seconds",
    "Request latency in seconds",
    ["endpoint", "agent_type"],
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0),
)

request_in_flight = Gauge(
    "agent_requests_in_flight",
    "Current number of in-flight requests",
    ["endpoint"],
)

# ── Agent metrics ────────────────────────────────────────────────────────
agent_run_total = Counter(
    "agent_runs_total",
    "Total agent executions",
    ["agent_name", "status"],
)

agent_run_latency = Histogram(
    "agent_run_latency_seconds",
    "Agent execution latency in seconds",
    ["agent_name"],
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0, 120.0),
)

# ── LLM metrics ──────────────────────────────────────────────────────────
llm_call_total = Counter(
    "llm_calls_total",
    "Total LLM calls",
    ["model", "status"],
)

llm_call_latency = Histogram(
    "llm_call_latency_seconds",
    "LLM call latency in seconds",
    ["model"],
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0),
)

llm_tokens_total = Counter(
    "llm_tokens_total",
    "Total tokens processed by LLM",
    ["model", "direction"],
)

# ── Retrieval metrics ────────────────────────────────────────────────────
retrieval_total = Counter(
    "retrieval_requests_total",
    "Total retrieval requests",
    ["search_type", "status"],
)

retrieval_latency = Histogram(
    "retrieval_latency_seconds",
    "Retrieval latency in seconds",
    ["search_type"],
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0),
)

retrieval_chunks = Histogram(
    "retrieval_chunks_total",
    "Number of chunks retrieved per request",
    ["search_type"],
    buckets=(0, 1, 3, 5, 10, 20, 50),
)

# ── Circuit Breaker metrics ──────────────────────────────────────────────
circuit_breaker_state = Gauge(
    "circuit_breaker_state",
    "Circuit breaker state (0=closed, 1=half_open, 2=open)",
    ["agent_id"],
)

circuit_breaker_failures = Counter(
    "circuit_breaker_failures_total",
    "Total circuit breaker failures",
    ["agent_id"],
)

# ── Memory metrics ───────────────────────────────────────────────────────
memory_operations = Counter(
    "memory_operations_total",
    "Total memory operations",
    ["operation", "memory_type", "status"],
)

memory_latency = Histogram(
    "memory_latency_seconds",
    "Memory operation latency",
    ["operation", "memory_type"],
    buckets=(0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0),
)


def metrics_endpoint():
    """Return prometheus metrics as text."""
    return (
        generate_latest(REGISTRY).decode("utf-8"),
        200,
        {"Content-Type": "text/plain; charset=utf-8"},
    )


def track_request(endpoint: str, agent_type: str = "unknown"):
    """Decorator to track request metrics."""

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            request_in_flight.labels(endpoint=endpoint).inc()
            start = time.time()
            try:
                result = await func(*args, **kwargs)
                request_total.labels(
                    endpoint=endpoint, agent_type=agent_type, status="success"
                ).inc()
                return result
            except Exception:
                request_total.labels(
                    endpoint=endpoint, agent_type=agent_type, status="error"
                ).inc()
                raise
            finally:
                request_in_flight.labels(endpoint=endpoint).dec()
                request_latency.labels(
                    endpoint=endpoint, agent_type=agent_type
                ).observe(time.time() - start)

        return wrapper

    return decorator


def track_agent_run(agent_name: str):
    """Decorator to track agent execution metrics."""

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start = time.time()
            try:
                result = await func(*args, **kwargs)
                agent_run_total.labels(agent_name=agent_name, status="success").inc()
                return result
            except Exception:
                agent_run_total.labels(agent_name=agent_name, status="error").inc()
                raise
            finally:
                agent_run_latency.labels(agent_name=agent_name).observe(
                    time.time() - start
                )

        return wrapper

    return decorator
