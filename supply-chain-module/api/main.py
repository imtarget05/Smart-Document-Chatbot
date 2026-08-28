"""Supply Chain Module API — FastAPI service cho agentic tools.

Endpoints khớp với SUPPLY_CHAIN_ENDPOINTS trong llm-router/agent/graph.py:
/forecast, /optimize-route, /supplier-risk (+ /anomaly-detect,
/inventory-optimal-order, /health).

Auth: optional X-Internal-Token (SUPPLY_CHAIN_INTERNAL_TOKEN, rỗng = tắt).
"""

import os
from typing import Any, Optional

from fastapi import Depends, FastAPI, HTTPException, Request, status

from . import services

INTERNAL_TOKEN = os.getenv("SUPPLY_CHAIN_INTERNAL_TOKEN", "")


def create_app() -> FastAPI:
    app = FastAPI(
        title="Smart Document Chatbot - Supply Chain Module",
        version="1.0.0",
        description="Deterministic supply chain tools for the agentic layer.",
    )

    def verify_token(request: Request) -> None:
        if INTERNAL_TOKEN and request.headers.get("X-Internal-Token", "") != INTERNAL_TOKEN:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized"
            )

    def _err_or(result: dict[str, Any]) -> dict[str, Any]:
        if "error" in result:
            raise HTTPException(status_code=422, detail=result)
        return result

    @app.post("/forecast", dependencies=[Depends(verify_token)])
    async def forecast(body: dict[str, Any]):
        """POST {history: number[], periods?: int} -> forecast chuỗi demand."""
        history = body.get("history") or []
        if not isinstance(history, list):
            raise HTTPException(status_code=422, detail="history phải là mảng số")
        periods = int(body.get("periods", 30))
        return _err_or(services.forecast_demand(history, periods))

    @app.post("/optimize-route", dependencies=[Depends(verify_token)])
    async def optimize_route(body: dict[str, Any]):
        """POST {distance_matrix: number[][], num_vehicles?: int, depot?: int}."""
        matrix = body.get("distance_matrix") or []
        if not isinstance(matrix, list) or not matrix:
            raise HTTPException(status_code=422, detail="distance_matrix trống")
        return _err_or(services.optimize_route(
            matrix, int(body.get("num_vehicles", 1)), int(body.get("depot", 0))
        ))

    @app.post("/supplier-risk", dependencies=[Depends(verify_token)])
    async def supplier_risk(body: dict[str, Any]):
        """POST {lead_time_std, defect_rate, on_time_rate} -> risk score + grade."""
        try:
            return _err_or(services.supplier_risk(
                float(body.get("lead_time_std", 0)),
                float(body.get("defect_rate", 0)),
                float(body.get("on_time_rate", 0)),
            ))
        except (TypeError, ValueError):
            raise HTTPException(status_code=422, detail="invalid numbers")

    @app.post("/anomaly-detect", dependencies=[Depends(verify_token)])
    async def anomaly_detect(body: dict[str, Any]):
        """POST {values: number[], threshold?: float} -> anomalies."""
        values = body.get("values") or []
        if not isinstance(values, list):
            raise HTTPException(status_code=422, detail="values phải là mảng số")
        return _err_or(services.detect_anomalies(
            values, float(body.get("threshold", 3.0))
        ))

    @app.post("/inventory-optimal-order", dependencies=[Depends(verify_token)])
    async def inventory_optimal_order(body: dict[str, Any]):
        """POST {annual_demand, order_cost, holding_cost, ...} -> EOQ/safety/ROP."""
        try:
            return _err_or(services.inventory_optimal_order(
                float(body.get("annual_demand", 0)),
                float(body.get("order_cost", 0)),
                float(body.get("holding_cost", 0)),
                float(body.get("std_demand", 0)),
                float(body.get("lead_time_days", 1)),
                float(body.get("service_level", 0.95)),
            ))
        except (TypeError, ValueError):
            raise HTTPException(status_code=422, detail="invalid numbers")

    @app.get("/health")
    async def health() -> dict[str, Any]:
        return {"status": "ok", "service": "supply-chain-module"}

    return app


app = create_app()