"""
Auto-Improvement Pipeline for AI Agents
========================================
Pipeline: generate → evaluate → improve → notify

This pipeline continuously improves agent prompts, tool definitions, and
response quality by:
1. Generating candidate improvements based on performance data
2. Evaluating them against quality metrics
3. Deploying improvements that pass evaluation
4. Notifying the team via Slack/email
"""

import inspect
import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class ImprovementStatus(str, Enum):
    PROPOSED = "proposed"
    EVALUATING = "evaluating"
    PASSED = "passed"
    FAILED = "failed"
    DEPLOYED = "deployed"
    ROLLED_BACK = "rolled_back"


@dataclass
class Improvement:
    """
    A candidate improvement to the agent system.

    Can be:
    - Prompt improvement (new system prompt)
    - Tool improvement (new/modified tool)
    - Configuration improvement (new parameters)
    - Agent improvement (new agent logic)
    """

    improvement_id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    agent_id: str = ""
    improvement_type: str = "prompt"  # prompt | tool | config | agent
    title: str = ""
    description: str = ""
    old_value: str = ""
    new_value: str = ""
    status: ImprovementStatus = ImprovementStatus.PROPOSED
    score: float = 0.0
    created_at: float = field(default_factory=time.time)
    evaluated_at: float = 0.0
    deployed_at: float = 0.0
    evaluator_notes: str = ""


class ImprovementPipeline:
    """
    Generate → Evaluate → Improve → Notify pipeline.

    Usage:
        pipeline = ImprovementPipeline()
        improvement = await pipeline.generate_improvement(agent_id, performance_data)
        result = await pipeline.evaluate(improvement)
        if result:
            await pipeline.deploy(improvement)
        await pipeline.notify(improvement)
    """

    def __init__(
        self, llm_generate: Optional[Callable] = None, slack_webhook: str = ""
    ):
        self._llm = llm_generate
        self._slack_webhook = slack_webhook
        self._history: List[Improvement] = []
        self._evaluators: Dict[str, Callable] = {}
        self._max_history = 200

    # ------------------------------------------------------------------
    # Register evaluators
    # ------------------------------------------------------------------

    def register_evaluator(self, name: str, evaluator: Callable) -> None:
        """Register an evaluation function for improvements."""
        self._evaluators[name] = evaluator
        logger.info(f"[ImprovementPipeline] Registered evaluator: {name}")

    # ------------------------------------------------------------------
    # Step 1: Generate (propose improvements)
    # ------------------------------------------------------------------

    async def generate_improvement(
        self,
        agent_id: str,
        performance_data: Dict[str, Any],
        improvement_type: str = "prompt",
    ) -> Improvement:
        """
        Generate a candidate improvement based on performance data.

        Analyzes performance metrics and proposes specific changes.
        """
        # Generate improvement using LLM if available
        if self._llm:
            improvement = await self._llm_generate_improvement(
                agent_id, performance_data, improvement_type
            )
        else:
            # Simple rule-based improvement
            improvement = self._rule_based_improvement(
                agent_id, performance_data, improvement_type
            )

        improvement.improvement_id = str(uuid.uuid4())[:12]
        improvement.created_at = time.time()
        self._history.append(improvement)

        logger.info(
            f"[ImprovementPipeline] Generated improvement '{improvement.title}' "
            f"for agent '{agent_id}'"
        )

        return improvement

    async def _llm_generate_improvement(
        self,
        agent_id: str,
        performance_data: Dict[str, Any],
        improvement_type: str,
    ) -> Improvement:
        """Use LLM to generate improvement suggestions."""
        prompt = f"""Analyze this agent's performance data and propose ONE specific improvement.

Agent: {agent_id}
Improvement type: {improvement_type}
Performance data: {json.dumps(performance_data, indent=2)}

Return a JSON with:
- title: short title of the improvement
- description: what needs to change and why
- old_value: current state
- new_value: proposed new state

Return ONLY valid JSON, no other text."""

        try:
            from langchain_core.messages import HumanMessage

            response = await self._llm.ainvoke([HumanMessage(content=prompt)])
            raw = response.content.strip()
            import re

            match = re.search(r"\{.*\}", raw, re.DOTALL)
            if match:
                data = json.loads(match.group())
                return Improvement(
                    agent_id=agent_id,
                    improvement_type=improvement_type,
                    title=data.get("title", "LLM-suggested improvement"),
                    description=data.get("description", ""),
                    old_value=data.get("old_value", ""),
                    new_value=data.get("new_value", ""),
                )
        except Exception as e:
            logger.warning(f"[ImprovementPipeline] LLM generation failed: {e}")

        return Improvement(
            agent_id=agent_id,
            improvement_type=improvement_type,
            title="Default improvement (LLM unavailable)",
            description="No specific improvement generated",
        )

    def _rule_based_improvement(
        self,
        agent_id: str,
        performance_data: Dict[str, Any],
        improvement_type: str,
    ) -> Improvement:
        """Generate rule-based improvements when LLM is unavailable."""
        suggestions = []

        # Check latency
        avg_latency = performance_data.get("avg_latency_seconds", 0)
        if avg_latency > 5.0:
            suggestions.append(
                "High latency detected. Consider reducing top_k, using smaller model, "
                "or implementing response caching."
            )

        # Check success rate
        success_rate = performance_data.get("success_rate", 1.0)
        if success_rate < 0.8:
            suggestions.append(
                f"Low success rate ({success_rate:.0%}). Consider adding retry logic, "
                "improving error handling, or adding fallback responses."
            )

        # Check token usage
        avg_tokens = performance_data.get("avg_tokens", 0)
        if avg_tokens > 2000:
            suggestions.append(
                "High token usage. Consider optimizing prompts to be more concise."
            )

        description = (
            " ".join(suggestions)
            if suggestions
            else "Performance within expected ranges."
        )
        return Improvement(
            agent_id=agent_id,
            improvement_type=improvement_type,
            title=f"Performance-based improvement for {agent_id}",
            description=description,
            old_value=f"latency={avg_latency}s, success_rate={success_rate:.0%}",
            new_value="optimized configuration",
        )

    # ------------------------------------------------------------------
    # Step 2: Evaluate
    # ------------------------------------------------------------------

    async def evaluate(self, improvement: Improvement) -> bool:
        """
        Evaluate an improvement against quality metrics.

        Returns:
            True if improvement passes evaluation
        """
        improvement.status = ImprovementStatus.EVALUATING
        scores = []

        # Run registered evaluators
        for name, evaluator in self._evaluators.items():
            try:
                if inspect.iscoroutinefunction(evaluator):
                    score = await evaluator(improvement)
                else:
                    score = evaluator(improvement)
                scores.append(score)
                logger.debug(
                    f"[ImprovementPipeline] Evaluator '{name}' scored: {score}"
                )
            except Exception as e:
                logger.warning(f"[ImprovementPipeline] Evaluator '{name}' failed: {e}")

        # Calculate overall score
        improvement.score = sum(scores) / max(len(scores), 1)
        improvement.evaluated_at = time.time()

        # Make decision
        if improvement.score >= 0.6 and len(scores) > 0:
            improvement.status = ImprovementStatus.PASSED
            logger.info(
                f"[ImprovementPipeline] Improvement '{improvement.title}' PASSED "
                f"(score={improvement.score:.2f})"
            )
            return True
        else:
            improvement.status = ImprovementStatus.FAILED
            improvement.evaluator_notes = (
                f"Score {improvement.score:.2f} below threshold 0.6"
            )
            logger.warning(
                f"[ImprovementPipeline] Improvement '{improvement.title}' FAILED "
                f"(score={improvement.score:.2f})"
            )
            return False

    # ------------------------------------------------------------------
    # Step 3: Deploy / Improve
    # ------------------------------------------------------------------

    async def deploy(self, improvement: Improvement) -> bool:
        """
        Deploy an improvement to the agent system.

        Returns:
            True if deployment succeeded
        """
        if improvement.status != ImprovementStatus.PASSED:
            logger.warning(
                f"[ImprovementPipeline] Cannot deploy improvement in status '{improvement.status.value}'"
            )
            return False

        try:
            # In a real system, this would:
            # 1. Save the new prompt/tool/config to the database
            # 2. Update the live agent configuration
            # 3. Restart affected agents if needed
            # 4. Run smoke tests

            improvement.status = ImprovementStatus.DEPLOYED
            improvement.deployed_at = time.time()

            logger.info(
                f"[ImprovementPipeline] Deployed improvement '{improvement.title}' to agent '{improvement.agent_id}'"
            )
            return True

        except Exception as e:
            improvement.status = ImprovementStatus.FAILED
            improvement.evaluator_notes = f"Deployment failed: {e}"
            logger.error(f"[ImprovementPipeline] Deployment failed: {e}")
            return False

    async def rollback(self, improvement: Improvement) -> bool:
        """Rollback a deployed improvement."""
        if improvement.status != ImprovementStatus.DEPLOYED:
            return False

        try:
            # Restore old value
            improvement.status = ImprovementStatus.ROLLED_BACK
            logger.info(
                f"[ImprovementPipeline] Rolled back improvement '{improvement.title}'"
            )
            return True
        except Exception as e:
            logger.error(f"[ImprovementPipeline] Rollback failed: {e}")
            return False

    # ------------------------------------------------------------------
    # Step 4: Notify
    # ------------------------------------------------------------------

    async def notify(self, improvement: Improvement, channel: str = "slack") -> bool:
        """
        Send notification about the improvement.

        Supports: slack, console, file
        """
        message = self._format_notification(improvement)

        if channel == "slack" and self._slack_webhook:
            try:
                import httpx

                async with httpx.AsyncClient(timeout=10) as client:
                    await client.post(
                        self._slack_webhook,
                        json={"text": message},
                    )
                logger.info("[ImprovementPipeline] Slack notification sent")
                return True
            except Exception as e:
                logger.warning(f"[ImprovementPipeline] Slack notification failed: {e}")

        # Always log to console
        logger.info(f"[ImprovementPipeline] Notification:\n{message}")
        return True

    def _format_notification(self, improvement: Improvement) -> str:
        """Format improvement as a notification message."""
        lines = [
            f"🤖 *Agent Improvement {'✅ Deployed' if improvement.status == ImprovementStatus.DEPLOYED else '❌ Failed'}*",
            f"*Agent:* {improvement.agent_id}",
            f"*Type:* {improvement.improvement_type}",
            f"*Title:* {improvement.title}",
            f"*Description:* {improvement.description}",
            f"*Score:* {improvement.score:.2f}",
        ]
        if improvement.deployed_at:
            import datetime

            dt = datetime.datetime.fromtimestamp(improvement.deployed_at)
            lines.append(f"*Deployed at:* {dt.strftime('%Y-%m-%d %H:%M:%S')}")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # History & Stats
    # ------------------------------------------------------------------

    def get_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get improvement history."""
        recent = self._history[-limit:]
        return [
            {
                "id": i.improvement_id,
                "agent": i.agent_id,
                "type": i.improvement_type,
                "title": i.title,
                "status": i.status.value,
                "score": i.score,
                "created": i.created_at,
            }
            for i in recent
        ]

    def get_stats(self) -> Dict[str, Any]:
        """Get pipeline statistics."""
        total = len(self._history)
        deployed = sum(
            1 for i in self._history if i.status == ImprovementStatus.DEPLOYED
        )
        failed = sum(1 for i in self._history if i.status == ImprovementStatus.FAILED)
        passed = sum(1 for i in self._history if i.status == ImprovementStatus.PASSED)

        return {
            "total_improvements": total,
            "deployed": deployed,
            "passed": passed,
            "failed": failed,
            "avg_score": round(sum(i.score for i in self._history) / max(total, 1), 3),
            "evaluators_registered": len(self._evaluators),
        }


# ============================================================================
# Convenience: run the full pipeline
# ============================================================================


async def run_improvement_pipeline(
    agent_id: str,
    performance_data: Dict[str, Any],
    llm_generate: Optional[Callable] = None,
    slack_webhook: str = "",
    deploy_automatically: bool = False,
) -> Improvement:
    """
    Run the full improvement pipeline for an agent.

    Flow:
    1. Generate improvement
    2. Evaluate improvement
    3. Deploy if evaluation passes (optional)
    4. Notify about result
    """
    pipeline = ImprovementPipeline(
        llm_generate=llm_generate,
        slack_webhook=slack_webhook,
    )

    # Step 1: Generate
    improvement = await pipeline.generate_improvement(agent_id, performance_data)

    # Step 2: Evaluate
    passed = await pipeline.evaluate(improvement)

    # Step 3: Deploy if configured
    if passed and deploy_automatically:
        await pipeline.deploy(improvement)

    # Step 4: Notify
    await pipeline.notify(improvement)

    return improvement
