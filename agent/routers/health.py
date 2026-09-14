"""
Health check and Prometheus metrics endpoints.
"""

import logging
from fastapi import APIRouter
from fastapi.responses import JSONResponse

from settings import settings

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])


@router.get("/health")
async def health():
    return {"status": "ok", "service": "agent", "version": "2.0.0"}


if settings.prometheus_enabled:

    @router.get("/metrics")
    async def metrics():
        try:
            from metrics import metrics_endpoint

            body, status_code, headers = metrics_endpoint()
            return JSONResponse(
                content=body,
                status_code=status_code,
                headers=headers,
            )
        except Exception as exc:
            logger.exception("Metrics endpoint failed: %s", exc)
            return JSONResponse(
                content={"error": "Metrics not available"},
                status_code=503,
            )
