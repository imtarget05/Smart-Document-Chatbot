"""
Shared runtime state and dependencies for the Agent Service.
Maintains singletons initialized during the FastAPI lifespan.
"""

import contextvars
import logging
from typing import Any, Optional

from fastapi import HTTPException, Request, status

from security.prompt_injection import detect_prompt_injection, sanitize_query
from settings import settings

logger = logging.getLogger(__name__)

# Singletons managed by the application lifespan
_workflow: Any = None
_long_term_memory: Any = None
_graph_memory: Any = None
_rate_limiter: Any = None
_a2a_hub: Any = None
_mcp_server: Any = None
_agent_factory: Any = None

# Contextvars for distributed tracing correlation
_request_id_ctx: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="")
_trace_id_ctx: contextvars.ContextVar[str] = contextvars.ContextVar("trace_id", default="")


def get_correlation_ids() -> dict[str, str]:
    return {"request_id": _request_id_ctx.get(""), "trace_id": _trace_id_ctx.get("")}


def check_rate_limit(key: str) -> bool:
    if _rate_limiter is None:
        return True
    return _rate_limiter.is_allowed(key)


def verify_internal_token(request: Request) -> None:
    if getattr(settings, "app_env", "local").lower() in ("test", "testing"):
        return
    token = request.headers.get("X-Internal-Token", "")
    if settings.internal_service_token and token != settings.internal_service_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized"
        )


def check_prompt_injection(query: str) -> str:
    """
    Detect and mitigate prompt-injection attempts.
    - HIGH severity: blocked (raises ValueError; caller converts to HTTP 400).
    - MEDIUM severity: sanitized + warning logged.
    - LOW / none: returned as-is.
    """
    result = detect_prompt_injection(query)
    if result.is_injection:
        logger.warning(
            "Prompt-injection detected: severity=%s reasons=%s patterns=%s",
            result.severity,
            result.reasons,
            result.matched_patterns,
        )
        if result.severity == "high":
            raise ValueError(
                f"Query rejected by prompt-injection guard: {result.reasons}"
            )
        sanitized = sanitize_query(query)
        logger.info("Query sanitized by prompt-injection guard.")
        return sanitized
    return query


def verify_and_rate_limit(request: Request) -> None:
    verify_internal_token(request)
    client_ip = request.headers.get("X-Forwarded-For", "").split(",")[0].strip() or (
        request.client.host if request.client else "unknown"
    )
    if not check_rate_limit(client_ip):
        logger.warning(
            "Agent rate limit exceeded for IP: %s path: %s", client_ip, request.url.path
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Maximum {settings.agent_rate_limit_rpm} requests per minute.",
            headers={"Retry-After": "60"},
        )
