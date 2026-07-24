"""FastAPI router for the benchmark framework."""

import json
import logging
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from .benchmark_runner import BenchmarkRunner
from .cost_tracker import cost_tracker
from .latency_profiler import latency_profiler
from .models import MODEL_CATALOG, get_hardware_cost_estimate
from .report import report_to_json

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/benchmark", tags=["benchmark"])

_sut = None
_runner = BenchmarkRunner()
_reports_dir = Path("benchmark/reports")


def init_benchmark_framework(agent_service_url: str, internal_token: str):
    from eval_framework.runner import default_system_under_test

    global _sut, _reports_dir
    _sut = default_system_under_test(agent_service_url, internal_token)
    _reports_dir.mkdir(parents=True, exist_ok=True)


@router.post("/run")
async def run_benchmark():
    if _sut is None:
        raise HTTPException(status_code=503, detail="Benchmark not initialized")
    report = await _runner.run(_sut)
    report_to_json(report, _reports_dir / f"{report.run_id}.json")
    return report.to_dict()


@router.get("/cost/summary")
async def cost_summary(last_n: Optional[int] = Query(default=None)):
    return cost_tracker.get_summary(last_n=last_n).to_dict()


@router.get("/latency/summary")
async def latency_summary(last_n: Optional[int] = Query(default=None)):
    return latency_profiler.get_summary(last_n=last_n).to_dict()


@router.get("/models")
async def list_models():
    return {
        model_id: {
            "provider": p.provider,
            "input_per_1k": p.input_per_1k,
            "output_per_1k": p.output_per_1k,
            "is_local": p.is_local,
        }
        for model_id, p in MODEL_CATALOG.items()
    }


@router.get("/models/{model_id}/hardware")
async def model_hardware(model_id: str, monthly_queries: int = Query(default=100000)):
    est = get_hardware_cost_estimate(model_id, monthly_queries)
    if "error" in est:
        raise HTTPException(status_code=404, detail=est["error"])
    return est


@router.get("/reports")
async def list_reports():
    if not _reports_dir.exists():
        return {"reports": []}
    files = sorted(_reports_dir.glob("*.json"), reverse=True)
    reports = []
    for f in files[:20]:
        data = json.loads(f.read_text())
        reports.append({
            "run_id": data.get("run_id"),
            "avg_latency_ms": data.get("avg_latency_ms"),
            "p95_latency_ms": data.get("p95_latency_ms"),
            "total_cost_usd": data.get("total_cost_usd"),
            "pass_rate": data.get("pass_rate"),
            "timestamp": data.get("timestamp"),
        })
    return {"reports": reports}
