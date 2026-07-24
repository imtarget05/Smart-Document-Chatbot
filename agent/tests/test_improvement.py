"""
Tests for Auto-Improvement Pipeline.
"""

import pytest

from improvement.pipeline import (
    Improvement,
    ImprovementPipeline,
    ImprovementStatus,
    run_improvement_pipeline,
)


class TestImprovement:
    """Improvement data model tests."""

    def test_initial_state(self):
        imp = Improvement(
            agent_id="rag_agent",
            improvement_type="prompt",
            title="Better system prompt",
            description="Improve clarity of instructions",
            old_value="Old prompt",
            new_value="New prompt",
        )
        assert imp.status == ImprovementStatus.PROPOSED
        assert imp.score == 0.0
        assert imp.improvement_id is not None


class TestImprovementPipeline:
    """ImprovementPipeline tests."""

    @pytest.mark.asyncio
    async def test_generate_rule_based(self):
        pipeline = ImprovementPipeline()
        imp = await pipeline.generate_improvement(
            agent_id="rag_agent",
            performance_data={
                "avg_latency_seconds": 8.0,
                "success_rate": 0.7,
                "avg_tokens": 2500,
            },
        )
        assert imp.agent_id == "rag_agent"
        assert "latency" in imp.description.lower()
        assert "success" in imp.description.lower()

    @pytest.mark.asyncio
    async def test_generate_with_good_performance(self):
        pipeline = ImprovementPipeline()
        imp = await pipeline.generate_improvement(
            agent_id="rag_agent",
            performance_data={
                "avg_latency_seconds": 1.0,
                "success_rate": 0.98,
                "avg_tokens": 500,
            },
        )
        assert "expected ranges" in imp.description.lower()

    @pytest.mark.asyncio
    async def test_register_evaluator(self):
        pipeline = ImprovementPipeline()

        async def my_evaluator(improvement):
            return 0.8

        pipeline.register_evaluator("test_eval", my_evaluator)
        assert "test_eval" in pipeline._evaluators

    @pytest.mark.asyncio
    async def test_evaluate_passes(self):
        pipeline = ImprovementPipeline()

        async def good_evaluator(improvement):
            return 0.9

        pipeline.register_evaluator("good", good_evaluator)
        imp = Improvement(agent_id="test", title="Test")
        result = await pipeline.evaluate(imp)
        assert result is True
        assert imp.status == ImprovementStatus.PASSED
        assert imp.score >= 0.6

    @pytest.mark.asyncio
    async def test_evaluate_fails(self):
        pipeline = ImprovementPipeline()

        async def bad_evaluator(improvement):
            return 0.3

        pipeline.register_evaluator("bad", bad_evaluator)
        imp = Improvement(agent_id="test", title="Test")
        result = await pipeline.evaluate(imp)
        assert result is False
        assert imp.status == ImprovementStatus.FAILED
        assert imp.score < 0.6

    @pytest.mark.asyncio
    async def test_deploy_passed_improvement(self):
        pipeline = ImprovementPipeline()
        imp = Improvement(agent_id="test", title="Test")
        imp.status = ImprovementStatus.PASSED
        imp.score = 0.8

        result = await pipeline.deploy(imp)
        assert result is True
        assert imp.status == ImprovementStatus.DEPLOYED

    @pytest.mark.asyncio
    async def test_deploy_failed_improvement(self):
        pipeline = ImprovementPipeline()
        imp = Improvement(agent_id="test", title="Test")
        imp.status = ImprovementStatus.FAILED

        result = await pipeline.deploy(imp)
        assert result is False
        assert imp.status == ImprovementStatus.FAILED

    @pytest.mark.asyncio
    async def test_rollback(self):
        pipeline = ImprovementPipeline()
        imp = Improvement(agent_id="test", title="Test")
        imp.status = ImprovementStatus.DEPLOYED

        result = await pipeline.rollback(imp)
        assert result is True
        assert imp.status == ImprovementStatus.ROLLED_BACK

    @pytest.mark.asyncio
    async def test_notify_console(self):
        pipeline = ImprovementPipeline()
        imp = Improvement(agent_id="test", title="Test improvement")
        imp.status = ImprovementStatus.DEPLOYED
        imp.score = 0.85

        result = await pipeline.notify(imp, channel="console")
        assert result is True

    @pytest.mark.asyncio
    async def test_history_tracking(self):
        pipeline = ImprovementPipeline()
        await pipeline.generate_improvement("agent1", {})
        await pipeline.generate_improvement("agent2", {})

        history = pipeline.get_history(limit=10)
        assert len(history) == 2
        assert history[0]["agent"] == "agent1"
        assert history[1]["agent"] == "agent2"

    @pytest.mark.asyncio
    async def test_get_stats(self):
        pipeline = ImprovementPipeline()
        imp = await pipeline.generate_improvement("agent1", {})
        imp.score = 0.5
        imp2 = await pipeline.generate_improvement("agent2", {})
        imp2.score = 0.8

        stats = pipeline.get_stats()
        assert stats["total_improvements"] == 2
        assert stats["avg_score"] > 0

    @pytest.mark.asyncio
    async def test_full_pipeline(self):
        """Test the convenience function."""
        imp = await run_improvement_pipeline(
            agent_id="test_agent",
            performance_data={"avg_latency_seconds": 5.0},
            deploy_automatically=False,
        )
        assert imp.agent_id == "test_agent"
        assert imp.status in (ImprovementStatus.PROPOSED, ImprovementStatus.FAILED)
