"""FastAPI router for the eval framework."""

import json
import logging
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query

from .core import EvalReport
from .runner import build_default_suites, default_system_under_test
from .report import report_to_html, report_to_markdown

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/eval", tags=["evaluation"])

_sut = None
_reports_dir = Path("eval_framework/reports")


def init_eval_framework(agent_service_url: str, internal_token: str):
    global _sut
    _sut = default_system_under_test(agent_service_url, internal_token)
    _reports_dir.mkdir(parents=True, exist_ok=True)


@router.post("/run")
async def run_evaluation(
    document_ids: List[str] = Query(default=[]),
    suite_name: Optional[str] = None,
):
    if _sut is None:
        raise HTTPException(status_code=503, detail="Eval framework not initialized")

    suites = build_default_suites(document_ids)
    if suite_name:
        suites = [s for s in suites if s.name == suite_name]
        if not suites:
            raise HTTPException(status_code=404, detail=f"Suite '{suite_name}' not found")

    reports = []
    for suite in suites:
        report = await suite.run(_sut)
        reports.append(report)

    if len(reports) == 1:
        return reports[0].to_dict()
    return {
        "aggregate": {
            "total_suites": len(reports),
            "total_cases": sum(r.total_cases for r in reports),
            "total_passed": sum(r.passed_cases for r in reports),
            "average_score": round(
                sum(r.overall_score for r in reports) / len(reports), 4
            ),
        },
        "reports": [r.to_dict() for r in reports],
    }


@router.get("/reports")
async def list_reports():
    if not _reports_dir.exists():
        return {"reports": []}
    files = sorted(_reports_dir.glob("*.json"), reverse=True)
    reports = []
    for f in files[:20]:
        with open(f) as fh:
            data = json.load(fh)
        reports.append({
            "run_id": data.get("run_id"),
            "suite_name": data.get("suite_name"),
            "overall_score": data.get("overall_score"),
            "pass_rate": data.get("pass_rate"),
            "duration_ms": data.get("duration_ms"),
            "timestamp": data.get("timestamp"),
            "path": str(f),
        })
    return {"reports": reports}


@router.get("/reports/{run_id}")
async def get_report(run_id: str, format: str = Query(default="json")):
    for f in _reports_dir.glob(f"{run_id}.json"):
        report_data = json.loads(f.read_text())
        if format == "markdown":
            report = EvalReport(
                run_id=report_data["run_id"],
                suite_name=report_data["suite_name"],
                total_cases=report_data["total_cases"],
                passed_cases=report_data["passed_cases"],
                overall_score=report_data["overall_score"],
                results=[],
                duration_ms=report_data["duration_ms"],
            )
            return {"markdown": report_to_markdown(report)}
        elif format == "html":
            report = EvalReport(
                run_id=report_data["run_id"],
                suite_name=report_data["suite_name"],
                total_cases=report_data["total_cases"],
                passed_cases=report_data["passed_cases"],
                overall_score=report_data["overall_score"],
                results=[],
                duration_ms=report_data["duration_ms"],
            )
            return {"html": report_to_html(report)}
        return report_data
    raise HTTPException(status_code=404, detail=f"Report '{run_id}' not found")
