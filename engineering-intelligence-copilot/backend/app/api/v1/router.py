from typing import Any

from fastapi import APIRouter

api_router = APIRouter()


@api_router.get("/", tags=["system"])
async def api_root() -> dict[str, Any]:
    return {
        "message": "Engineering Intelligence Copilot API v1",
        "capabilities": [
            "knowledge_qa",
            "document_analysis",
            "test_report_summary",
            "8d_problem_solving",
            "evaluation",
        ],
    }