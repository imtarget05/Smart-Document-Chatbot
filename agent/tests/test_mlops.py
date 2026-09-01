"""
Tests for the MLOps module.

Tests MLflow tracking, model registry CRUD, and HuggingFace provider fallback.
"""

import os
import json
import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock, ANY


# ── MLflow Tracker Tests ─────────────────────────────────────────────────────

class TestTracker:
    """Tests for mlops.tracker module."""

    def test_log_eval_run_no_mlflow(self, monkeypatch):
        """When mlflow is not installed, log_eval_run should return None."""
        import mlops.tracker as tracker
        monkeypatch.setattr(tracker, "MLFLOW_AVAILABLE", False)

        result = tracker.log_eval_run(
            metrics={"accuracy": 0.9},
            params={"model": "test"},
        )
        assert result is None

    def test_log_retrieval_experiment_no_mlflow(self, monkeypatch):
        """When mlflow is not installed, log_retrieval_experiment should return None."""
        import mlops.tracker as tracker
        monkeypatch.setattr(tracker, "MLFLOW_AVAILABLE", False)

        result = tracker.log_retrieval_experiment(
            chunk_size=512,
            top_k=5,
            embedding_model="test-model",
            metrics={"retrieval_accuracy": 0.85},
        )
        assert result is None

    def test_compare_runs_no_mlflow(self, monkeypatch):
        """When mlflow is not installed, compare_runs should return error dict."""
        import mlops.tracker as tracker
        monkeypatch.setattr(tracker, "MLFLOW_AVAILABLE", False)

        result = tracker.compare_runs(["run1", "run2"])
        assert "error" in result

    def def_test_get_best_run_no_mlflow(self, monkeypatch):
        """When mlflow is not installed, get_best_run should return None."""
        import mlops.tracker as tracker
        monkeypatch.setattr(tracker, "MLFLOW_AVAILABLE", False)

        result = tracker.get_best_run("accuracy")
        assert result is None

    def test_log_eval_run_success(self, monkeypatch):
        """Successful eval run logging with mocked mlflow."""
        import mlops.tracker as tracker

        # Create a mock mlflow module
        mock_mlflow = MagicMock()
        mock_mlflow.get_experiment_by_name.return_value = MagicMock(experiment_id="exp1")
        mock_mlflow.active_run.return_value.info.run_id = "run123"

        # Patch mlflow in the tracker module
        monkeypatch.setattr(tracker, "MLFLOW_AVAILABLE", True)
        monkeypatch.setattr(tracker, "mlflow", mock_mlflow)

        result = tracker.log_eval_run(
            metrics={"accuracy": 0.95, "f1": 0.88},
            params={"model": "test-v1"},
        )

        mock_mlflow.start_run.assert_called_once()
        mock_mlflow.log_metric.assert_any_call("accuracy", 0.95)
        mock_mlflow.log_metric.assert_any_call("f1", 0.88)
        mock_mlflow.log_param.assert_any_call("model", "test-v1")
        assert result == "run123"

    def test_log_retrieval_experiment_success(self, monkeypatch):
        """Successful retrieval experiment logging with mocked mlflow."""
        import mlops.tracker as tracker

        mock_mlflow = MagicMock()
        mock_mlflow.get_experiment_by_name.return_value = MagicMock(experiment_id="exp1")
        mock_mlflow.active_run.return_value.info.run_id = "run456"

        monkeypatch.setattr(tracker, "MLFLOW_AVAILABLE", True)
        monkeypatch.setattr(tracker, "mlflow", mock_mlflow)

        result = tracker.log_retrieval_experiment(
            chunk_size=256,
            top_k=3,
            embedding_model="test-embed",
            metrics={"retrieval_accuracy": 0.82},
        )

        assert result == "run456"
        mock_mlflow.log_param.assert_any_call("chunk_size", 256)
        mock_mlflow.log_param.assert_any_call("top_k", 3)
        mock_mlflow.log_param.assert_any_call("embedding_model", "test-embed")

    def test_get_git_commit(self):
        """Test git commit retrieval returns a string."""
        from mlops.tracker import _get_git_commit
        result = _get_git_commit()
        assert isinstance(result, str)
        assert len(result) > 0


# ── Model Registry Tests ─────────────────────────────────────────────────────

class TestModelRegistry:
    """Tests for mlops.model_registry module."""

    @pytest.fixture
    def tmp_registry_dir(self, tmp_path):
        """Create a temporary registry directory."""
        reg_dir = tmp_path / "test_registry"
        reg_dir.mkdir()
        return str(reg_dir)

    @pytest.fixture
    def registry(self, tmp_registry_dir):
        """Create a ModelRegistry instance with temp dir."""
        from mlops.model_registry import ModelRegistry
        return ModelRegistry(registry_dir=tmp_registry_dir)

    def test_register_model_success(self, registry):
        """Register a model successfully."""
        result = registry.register_model(
            name="test-model",
            version="1.0.0",
            metrics={"retrieval_accuracy": 0.85, "answer_correctness": 0.80, "hallucination_rate": 0.10},
            config={"chunk_size": 512},
        )
        assert result is not None
        assert result.version == "1.0.0"
        assert result.stage == "Staging"

    def test_register_model_quality_gate_fail(self, registry):
        """Model with poor metrics should fail quality gate."""
        result = registry.register_model(
            name="test-model",
            version="1.0.0",
            metrics={"retrieval_accuracy": 0.50},
        )
        assert result is None

    def test_register_model_quality_gate_force(self, registry):
        """Force registration bypasses quality gate."""
        result = registry.register_model(
            name="test-model",
            version="1.0.0",
            metrics={"retrieval_accuracy": 0.50},
            force=True,
        )
        assert result is not None

    def test_register_duplicate_version(self, registry):
        """Duplicate version registration should fail without force."""
        registry.register_model(name="test-model", version="1.0.0", force=True)
        result = registry.register_model(name="test-model", version="1.0.0", force=False)
        assert result is None

    def test_register_duplicate_version_force(self, registry):
        """Force re-registration of same version should succeed."""
        registry.register_model(name="test-model", version="1.0.0", force=True)
        result = registry.register_model(name="test-model", version="1.0.0", force=True)
        assert result is not None

    def test_promote_model(self, registry):
        """Promote model from Staging to Production."""
        registry.register_model(name="test-model", version="1.0.0", force=True)
        result = registry.promote_model("test-model", "1.0.0", "Production")
        assert result is True

        model = registry.get_model("test-model", stage="Production")
        assert model is not None
        assert model.version == "1.0.0"

    def test_promote_model_invalid_stage(self, registry):
        """Promotion to invalid stage should fail."""
        registry.register_model(name="test-model", version="1.0.0", force=True)
        result = registry.promote_model("test-model", "1.0.0", "InvalidStage")
        assert result is False

    def test_promote_auto_archive(self, registry):
        """Promoting to Production auto-archives previous Production."""
        registry.register_model(name="test-model", version="1.0.0", force=True)
        registry.register_model(name="test-model", version="2.0.0", force=True)
        registry.promote_model("test-model", "1.0.0", "Production")
        registry.promote_model("test-model", "2.0.0", "Production")

        old = registry.get_model("test-model", stage="Production")
        assert old.version == "2.0.0"

        archived = registry.get_model("test-model", stage="Archived")
        assert archived is not None
        assert archived.version == "1.0.0"

    def test_get_model_not_found(self, registry):
        """Getting non-existent model returns None."""
        result = registry.get_model("nonexistent", stage="Production")
        assert result is None

    def test_list_versions(self, registry):
        """List all versions of a model."""
        registry.register_model(name="test-model", version="1.0.0", force=True)
        registry.register_model(name="test-model", version="2.0.0", force=True)

        versions = registry.list_versions("test-model")
        assert len(versions) == 2

    def test_compare_versions(self, registry):
        """Compare two model versions."""
        registry.register_model(
            name="test-model", version="1.0.0",
            metrics={"accuracy": 0.80}, force=True
        )
        registry.register_model(
            name="test-model", version="2.0.0",
            metrics={"accuracy": 0.90}, force=True
        )

        comparison = registry.compare_versions("test-model", "1.0.0", "2.0.0")
        assert abs(comparison["metric_diff"]["accuracy"] - 0.10) < 1e-9

    def test_compare_versions_not_found(self, registry):
        """Comparing non-existent versions returns error."""
        result = registry.compare_versions("test-model", "1.0.0", "2.0.0")
        assert "error" in result

    def test_quality_gate_all_metrics(self):
        """Test quality gate with all threshold metrics."""
        from mlops.model_registry import ModelRegistry
        reg = ModelRegistry()

        metrics = {
            "retrieval_accuracy": 0.80,
            "answer_correctness": 0.75,
            "hallucination_rate": 0.15,
            "faithfulness": 0.80,
        }
        passed, failures = reg.passes_quality_gate(metrics)
        assert passed is True
        assert len(failures) == 0

    def test_quality_gate_fail_hallucination(self):
        """Test quality gate failure on high hallucination rate."""
        from mlops.model_registry import ModelRegistry
        reg = ModelRegistry()

        metrics = {
            "retrieval_accuracy": 0.80,
            "hallucination_rate": 0.30,  # Above threshold
        }
        passed, failures = reg.passes_quality_gate(metrics)
        assert passed is False
        assert len(failures) > 0


# ── Hugging Face Provider Tests ────────────────────────────────────────────────

class TestHuggingFaceProvider:
    """Tests for mlops.hf_provider module."""

    def test_fallback_when_transformers_unavailable(self, monkeypatch):
        """Provider should work in fallback mode without transformers."""
        import mlops.hf_provider as hf
        monkeypatch.setattr(hf, "TRANSFORMERS_AVAILABLE", False)

        provider = hf.HuggingFaceProvider(load_on_init=False)
        assert provider.is_available is False
        assert provider.has_embedding_model is False

    def test_embed_fallback_returns_zero_vectors(self, monkeypatch):
        """embed() should return zero vectors when model unavailable."""
        import mlops.hf_provider as hf
        monkeypatch.setattr(hf, "TRANSFORMERS_AVAILABLE", False)

        provider = hf.HuggingFaceProvider(load_on_init=False)
        result = provider.embed(["test text"])
        assert len(result) == 1
        assert len(result[0]) == hf.EMBEDDING_DIM
        assert all(v == 0.0 for v in result[0])

    def test_generate_fallback_response(self, monkeypatch):
        """generate() should return fallback text when model unavailable."""
        import mlops.hf_provider as hf
        monkeypatch.setattr(hf, "TRANSFORMERS_AVAILABLE", False)

        provider = hf.HuggingFaceProvider(load_on_init=False)
        result = provider.generate("test prompt")
        assert "Fallback" in result or "unavailable" in result

    def test_get_model_info(self, monkeypatch):
        """get_model_info() should return model status dict."""
        import mlops.hf_provider as hf
        monkeypatch.setattr(hf, "TRANSFORMERS_AVAILABLE", False)

        provider = hf.HuggingFaceProvider(load_on_init=False)
        info = provider.get_model_info()
        assert "embedding_model" in info
        assert "chat_model" in info
        assert info["embedding_model"]["name"] == hf.DEFAULT_EMBEDDING_MODEL
        assert info["chat_model"]["name"] == hf.DEFAULT_CHAT_MODEL

    def test_get_hf_provider_factory(self):
        """Factory function should return a HuggingFaceProvider."""
        from mlops.hf_provider import get_hf_provider, HuggingFaceProvider
        provider = get_hf_provider()
        assert isinstance(provider, HuggingFaceProvider)

    def test_custom_model_names(self):
        """Provider accepts custom model names."""
        from mlops.hf_provider import HuggingFaceProvider
        provider = HuggingFaceProvider(
            embedding_model="custom-embed-model",
            chat_model="custom-chat-model",
            load_on_init=False,
        )
        assert provider.embedding_model_name == "custom-embed-model"
        assert provider.chat_model_name == "custom-chat-model"


# ── Retrieval Tuner Tests ─────────────────────────────────────────────────────

class TestRetrievalTuner:
    """Tests for mlops.retrieval_tuner module."""

    def test_run_experiment_returns_results(self):
        """run_experiment should return results for each config."""
        from mlops.retrieval_tuner import RetrievalTuner
        tuner = RetrievalTuner()
        results = tuner.run_experiment(
            questions=["test question"],
            chunk_sizes=[256],
            top_ks=[3],
            embedding_models=["test-model"],
            log_to_mlflow=False,
        )
        assert len(results) == 1
        assert results[0].chunk_size == 256
        assert results[0].top_k == 3

    def test_run_experiment_grid_size(self):
        """Grid search should produce correct number of results."""
        from mlops.retrieval_tuner import RetrievalTuner
        tuner = RetrievalTuner()
        results = tuner.run_experiment(
            questions=["test"],
            chunk_sizes=[256, 512],
            top_ks=[3, 5],
            embedding_models=["model-a", "model-b"],
            log_to_mlflow=False,
        )
        assert len(results) == 8

    def test_get_best_config(self):
        """get_best_config should return the best configuration."""
        from mlops.retrieval_tuner import RetrievalTuner
        tuner = RetrievalTuner()
        tuner.run_experiment(
            questions=["test"],
            chunk_sizes=[256],
            top_ks=[3],
            embedding_models=["model-a"],
            log_to_mlflow=False,
        )
        best = tuner.get_best_config(metric="retrieval_accuracy")
        assert best is not None

    def test_compare_embeddings(self):
        """compare_embeddings should return status for each model."""
        from mlops.retrieval_tuner import RetrievalTuner
        tuner = RetrievalTuner()
        result = tuner.compare_embeddings(
            texts=["test"],
            models=["model-a", "model-b"],
        )
        assert "model-a" in result
        assert "model-b" in result

    def test_tune_reranker(self):
        """tune_reranker should return results for each reranker."""
        from mlops.retrieval_tuner import RetrievalTuner
        tuner = RetrievalTuner()
        result = tuner.tune_reranker(
            questions=["test"],
            reranker_models=["reranker-a"],
        )
        assert "reranker-a" in result

    def test_results_summary(self):
        """get_results_summary should aggregate metrics."""
        from mlops.retrieval_tuner import RetrievalTuner
        tuner = RetrievalTuner()
        tuner.run_experiment(
            questions=["test"],
            chunk_sizes=[256, 512],
            top_ks=[3],
            embedding_models=["model-a"],
            log_to_mlflow=False,
        )
        summary = tuner.get_results_summary()
        assert summary["count"] == 2
        assert "best_by_metric" in summary
        assert "avg_by_metric" in summary
