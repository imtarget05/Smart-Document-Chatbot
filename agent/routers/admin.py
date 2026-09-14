"""
Admin, Retraining, Self-Improvement, and A/B Testing endpoints.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, Request

from ab_testing import ab_manager
from settings import settings
import state

logger = logging.getLogger(__name__)

router = APIRouter(tags=["admin"])


@router.post("/agent/improve", dependencies=[Depends(state.verify_and_rate_limit)])
async def run_improvement(request: Request):
    """Trigger the auto-improvement pipeline for an agent."""
    try:
        from improvement.pipeline import run_improvement_pipeline

        payload = await request.json()
        agent_id = payload.get("agent_id", "rag_agent")
        performance_data = payload.get("performance_data", {})
        deploy_automatically = payload.get("deploy_automatically", False)

        improvement = await run_improvement_pipeline(
            agent_id=agent_id,
            performance_data=performance_data,
            deploy_automatically=deploy_automatically,
        )
        return {
            "status": "ok",
            "improvement": {
                "id": improvement.improvement_id,
                "title": improvement.title,
                "description": improvement.description,
                "status": improvement.status.value,
                "score": improvement.score,
            },
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Improvement pipeline failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/agent/retrain", dependencies=[Depends(state.verify_and_rate_limit)])
async def run_retrain(request: Request):
    """Trigger the retrain/re-evaluation pipeline."""
    try:
        from retrain import check_and_retrain

        payload = await request.json()
        base_url = payload.get("base_url", "http://localhost:8080/api")
        token = payload.get("token", "")
        document_id = payload.get("document_id", 1)
        force = payload.get("force", False)

        if not token:
            raise HTTPException(status_code=400, detail="token is required")

        decision = check_and_retrain(base_url, token, document_id, force)
        return {"status": "ok", "decision": decision.to_dict()}
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Retrain pipeline failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/ab/report", dependencies=[Depends(state.verify_and_rate_limit)])
async def ab_report():
    return ab_manager.get_report()


@router.get("/ab/variants", dependencies=[Depends(state.verify_and_rate_limit)])
async def ab_variants():
    exp = ab_manager.experiments.get("rag-config-v1")
    if not exp:
        return {"error": "No active experiment"}
    return {
        "experiment_id": exp.id,
        "status": exp.status,
        "variants": [
            {
                "id": v.id,
                "name": v.name,
                "description": v.description,
                "weight": v.weight,
                "is_control": v.is_control,
                "config": v.config,
            }
            for v in exp.variants
        ],
    }


@router.post("/agent/on-ingest-complete", dependencies=[Depends(state.verify_internal_token)])
async def on_ingest_complete(request: Request):
    """Called by backend after ETL completes for a document.
    Triggers retrain pipeline if conditions are met."""
    try:
        from retrain import check_and_retrain

        payload = await request.json()
        document_id = payload.get("document_id", 0)
        base_url = payload.get("base_url", "http://backend:8080/api")
        token = payload.get("token", settings.internal_service_token)

        decision = check_and_retrain(base_url, token, document_id, force=False)
        if decision.should_retrain:
            logger.info(
                "Auto-retrain triggered after document %s ingestion: %s",
                document_id,
                decision.reason,
            )
        return {
            "status": "ok",
            "should_retrain": decision.should_retrain,
            "decision": decision.to_dict(),
        }
    except Exception as exc:
        logger.exception("on_ingest_complete failed: %s", exc)
        return {"status": "error", "error": str(exc)}
