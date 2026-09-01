"""Tests for LLM Judge evaluation module."""

import json
import pytest

from eval.llm_judge import (
    JudgeLLM,
    JudgeResult,
    JudgeScore,
    LLMJudge,
    _parse_judge_json,
    evaluate_faithfulness,
    evaluate_relevance,
    evaluate_completeness,
    evaluate_tone,
)


class TestParseJudgeJson:
    """Test JSON parsing from judge responses."""

    def test_valid_json(self):
        text = '{"score": 0.85, "explanation": "Good answer"}'
        score, explanation = _parse_judge_json(text)
        assert score == 0.85
        assert explanation == "Good answer"

    def test_json_with_surrounding_text(self):
        text = 'Here is my evaluation:\n{"score": 0.9, "explanation": "Relevant"}\nDone.'
        score, explanation = _parse_judge_json(text)
        assert score == 0.9
        assert explanation == "Relevant"

    def test_score_clamping_high(self):
        text = '{"score": 1.5, "explanation": "Too high"}'
        score, _ = _parse_judge_json(text)
        assert score == 1.0

    def test_score_clamping_low(self):
        text = '{"score": -0.5, "explanation": "Too low"}'
        score, _ = _parse_judge_json(text)
        assert score == 0.0

    def test_invalid_json_fallback(self):
        text = "The score is 0.75 and this is good."
        score, explanation = _parse_judge_json(text)
        assert score == 0.75
        assert "good" in explanation

    def test_empty_text(self):
        score, explanation = _parse_judge_json("")
        assert score == 0.5
        assert "Could not parse" in explanation


class TestJudgeScore:
    """Test JudgeScore dataclass."""

    def test_to_dict(self):
        score = JudgeScore(score=0.9, explanation="Good", metric="faithfulness")
        d = score.to_dict()
        assert d["score"] == 0.9
        assert d["explanation"] == "Good"
        assert d["metric"] == "faithfulness"


class TestJudgeResult:
    """Test JudgeResult aggregation."""

    def test_average_score_with_all_metrics(self):
        result = JudgeResult(
            faithfulness=JudgeScore(0.8, "f", "faithfulness"),
            relevance=JudgeScore(0.9, "r", "relevance"),
            completeness=JudgeScore(0.7, "c", "completeness"),
            tone = JudgeScore(0.95, "t", "tone"),
        )
        # tone is not a JudgeScore here, let's fix
        result.tone = JudgeScore(0.95, "t", "tone")
        assert result.average_score is not None
        assert 0.8 < result.average_score < 0.95

    def test_average_score_with_none(self):
        result = JudgeResult()
        assert result.average_score is None

    def test_to_dict(self):
        result = JudgeResult(
            faithfulness=JudgeScore(0.8, "f", "faithfulness"),
            relevance=JudgeScore(0.9, "r", "relevance"),
        )
        d = result.to_dict()
        assert d["faithfulness"]["score"] == 0.8
        assert d["relevance"]["score"] == 0.9
        assert d["completeness"] is None
        assert d["tone"] is None


class TestJudgeLLM:
    """Test the LLM client."""

    def test_mock_mode_returns_faithfulness(self):
        llm = JudgeLLM(mock=True)
        response = llm.complete("Is this faithful?")
        data = json.loads(response)
        assert "score" in data
        assert "explanation" in data

    def test_mock_mode_returns_relevance(self):
        llm = JudgeLLM(mock=True)
        response = llm.complete("Is this relevant?")
        data = json.loads(response)
        assert "score" in data

    def test_mock_mode_returns_completeness(self):
        llm = JudgeLLM(mock=True)
        response = llm.complete("Is this complete?")
        data = json.loads(response)
        assert "score" in data

    def test_mock_mode_returns_tone(self):
        llm = JudgeLLM(mock=True)
        response = llm.complete("Is this tone appropriate?")
        data = json.loads(response)
        assert "score" in data


class TestLLMJudge:
    """Test the main LLMJudge class with mock LLM."""

    def setup_method(self):
        self.judge = LLMJudge(mock=True)

    def test_evaluate_faithfulness(self):
        score = self.judge.evaluate_faithfulness(
            answer="The system uses Spring Boot.",
            context="The backend framework is Spring Boot 3.2.",
        )
        assert isinstance(score, JudgeScore)
        assert 0.0 <= score.score <= 1.0
        assert score.metric == "faithfulness"
        assert len(score.explanation) > 0

    def test_evaluate_relevance(self):
        score = self.judge.evaluate_relevance(
            question="What framework does the system use?",
            answer="The system uses Spring Boot for the backend.",
        )
        assert isinstance(score, JudgeScore)
        assert 0.0 <= score.score <= 1.0
        assert score.metric == "relevance"

    def test_evaluate_completeness(self):
        score = self.judge.evaluate_completeness(
            question="What are the authentication methods?",
            answer="The system uses JWT tokens and OAuth2.",
            expected_concepts=["JWT", "OAuth2"],
        )
        assert isinstance(score, JudgeScore)
        assert 0.0 <= score.score <= 1.0
        assert score.metric == "completeness"

    def test_evaluate_tone(self):
        score = self.judge.evaluate_tone(
            answer="The system architecture follows microservices patterns.",
            expected_tone="professional",
        )
        assert isinstance(score, JudgeScore)
        assert 0.0 <= score.score <= 1.0
        assert score.metric == "tone"

    def test_evaluate_all(self):
        result = self.judge.evaluate_all(
            question="What database is used?",
            answer="The system uses PostgreSQL for data storage.",
            context="PostgreSQL is the primary database.",
            expected_concepts=["PostgreSQL"],
            expected_tone="professional",
        )
        assert isinstance(result, JudgeResult)
        assert result.faithfulness is not None
        assert result.relevance is not None
        assert result.completeness is not None
        assert result.tone is not None
        assert result.average_score is not None

    def test_evaluate_all_without_context(self):
        result = self.judge.evaluate_all(
            question="What database is used?",
            answer="The system uses PostgreSQL.",
        )
        assert result.faithfulness is None
        assert result.relevance is not None

    def test_evaluate_all_without_concepts(self):
        result = self.judge.evaluate_all(
            question="What database is used?",
            answer="PostgreSQL is used.",
            context="The database is PostgreSQL.",
        )
        assert result.completeness is None
        assert result.faithfulness is not None


class TestModuleLevelFunctions:
    """Test module-level convenience functions."""

    def test_evaluate_faithfulness_function(self):
        score = evaluate_faithfulness(
            answer="Test answer",
            context="Test context",
            mock=True,
        )
        assert isinstance(score, JudgeScore)
        assert score.metric == "faithfulness"

    def test_evaluate_relevance_function(self):
        score = evaluate_relevance(
            question="Test question",
            answer="Test answer",
            mock=True,
        )
        assert isinstance(score, JudgeScore)
        assert score.metric == "relevance"

    def test_evaluate_completeness_function(self):
        score = evaluate_completeness(
            question="Test question",
            answer="Test answer",
            expected_concepts=["concept1", "concept2"],
            mock=True,
        )
        assert isinstance(score, JudgeScore)
        assert score.metric == "completeness"

    def test_evaluate_tone_function(self):
        score = evaluate_tone(
            answer="Test answer",
            expected_tone="professional",
            mock=True,
        )
        assert isinstance(score, JudgeScore)
        assert score.metric == "tone"


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_answer(self):
        judge = LLMJudge(mock=True)
        score = judge.evaluate_faithfulness(answer="", context="Some context")
        assert isinstance(score, JudgeScore)
        assert 0.0 <= score.score <= 1.0

    def test_empty_context(self):
        judge = LLMJudge(mock=True)
        score = judge.evaluate_faithfulness(answer="Some answer", context="")
        assert isinstance(score, JudgeScore)

    def test_very_long_answer(self):
        judge = LLMJudge(mock=True)
        long_answer = "word " * 1000
        score = judge.evaluate_relevance(question="Test?", answer=long_answer)
        assert isinstance(score, JudgeScore)

    def test_unicode_content(self):
        judge = LLMJudge(mock=True)
        score = judge.evaluate_faithfulness(
            answer="Hệ thống sử dụng Spring Boot cho backend.",
            context="Backend framework là Spring Boot 3.2.",
        )
        assert isinstance(score, JudgeScore)
        assert 0.0 <= score.score <= 1.0

    def test_special_characters_in_answer(self):
        judge = LLMJudge(mock=True)
        score = judge.evaluate_relevance(
            question="What is the API format?",
            answer='JSON format: {"key": "value"}',
        )
        assert isinstance(score, JudgeScore)
