"""EvalRunner — orchestrates suites, caches results, generates reports."""

import logging
from typing import Any, Callable, Dict, List

from .core import EvalSuite
from .cases import ALL_CASES
from .cases.robustness import RobustnessEvalCase

logger = logging.getLogger(__name__)


def default_system_under_test(agent_service_url: str, internal_token: str) -> Callable:
    """Returns an async function that sends queries to the agent service."""

    async def _sut(input_data: Dict[str, Any]) -> Dict[str, Any]:
        import httpx
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{agent_service_url}/v1/agent/invoke",
                json=input_data,
                headers={"X-Internal-Token": internal_token},
            )
            if resp.status_code == 400:
                detail = resp.json().get("detail", "")
                return {"error": detail, "code": "blocked"}
            resp.raise_for_status()
            return resp.json()

    return _sut


def build_default_suites(document_ids: List[str]) -> List[EvalSuite]:
    suites = []
    suite = EvalSuite(
        name="rag-quality",
        description="Comprehensive RAG quality evaluation",
        pass_threshold=0.6,
    )
    for cls in ALL_CASES:
        if cls.__name__ == "RobustnessEvalCase":
            for c in RobustnessEvalCase.create_all(document_ids):
                suite.add_case(c)
        elif cls.__name__ == "SecurityEvalCase":
            for idx, test_type in enumerate(["injection", "injection", "injection", "pii"]):
                suite.add_case(cls(
                    case_id=f"sec-{idx}",
                    name=f"Security: {test_type}",
                    test_type=test_type,
                    document_ids=document_ids,
                ))
        elif cls.__name__ == "LatencyEvalCase":
            suite.add_case(cls(
                case_id="latency-0",
                name="Latency: quick query",
                query="What is the main topic of my documents?",
                document_ids=document_ids,
                max_total_ms=30000,
            ))
        elif cls.__name__ == "CostEvalCase":
            suite.add_case(cls(
                case_id="cost-0",
                name="Cost: simple query",
                query="Summarize my documents.",
                document_ids=document_ids,
                max_cost_usd=0.05,
            ))
        elif cls.__name__ == "HallucinationEvalCase":
            suite.add_case(cls(
                case_id="hal-0",
                name="Hallucination: grounded query",
                query="What do my documents say?",
                document_ids=document_ids,
                expected_source_keywords=[],
            ))
        elif cls.__name__ == "RetrievalQualityEvalCase":
            suite.add_case(cls(
                case_id="ret-0",
                name="Retrieval: default query",
                query="What is this about?",
                document_ids=document_ids,
                expected_source_keywords=[],
            ))
        elif cls.__name__ == "AnswerQualityEvalCase":
            suite.add_case(cls(
                case_id="ans-0",
                name="Answer: general query",
                query="Tell me about my documents.",
                document_ids=document_ids,
                expected_answer_keywords=[],
            ))
    suites.append(suite)
    return suites
