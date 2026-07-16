import logging
from typing import Any, Dict, List

from adk_agent import AdkAgent, AdkAgentSpec

logger = logging.getLogger(__name__)


def run_demo_workflow(user_request: str, document_name: str) -> Dict[str, Any]:
    steps: List[Dict[str, Any]] = []
    specs = [
        AdkAgentSpec(
            name="ingest",
            description="Prepare the document for analysis",
            instructions="Validate that the file exists and is readable.",
        ),
        AdkAgentSpec(
            name="analyze",
            description="Extract key ideas from the document",
            instructions="Return the top insights in concise bullets.",
        ),
        AdkAgentSpec(
            name="summarize",
            description="Generate a short executive summary",
            instructions="Keep the summary precise and relevant to the request.",
        ),
        AdkAgentSpec(
            name="actions",
            description="Create follow-up action items",
            instructions="List concrete next steps.",
        ),
        AdkAgentSpec(
            name="report",
            description="Package the output into a demo-ready response",
            instructions="Return a polished handoff summary.",
        ),
    ]

    for spec in specs:
        agent = AdkAgent(spec)
        result = agent.run(user_request)
        logger.info("ADK step=%s status=%s", spec.name, result["status"])
        steps.append(
            {
                "name": spec.name,
                "status": result["status"],
                "summary": result["summary"],
            }
        )

    return {
        "status": "ok",
        "document_name": document_name,
        "user_request": user_request,
        "steps": steps,
        "summary": "Demo workflow completed successfully.",
        "trace": {
            "status": "ok",
            "step_count": len(steps),
            "steps": [step["name"] for step in steps],
        },
    }
