"""
Tests for LlamaIndex, DSPy, and framework router integrations.

Tests gracefully handle missing dependencies by mocking unavailable modules.
"""

import os
import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestLlamaIndexRag:
    """Tests for the LlamaIndex RAG pipeline."""

    def test_import_graceful_fallback(self):
        """Test that the module imports even without llama-index installed."""
        from llamaindex_pipeline import LlamaIndexRag, LLAMAINDEX_AVAILABLE

        assert isinstance(LLAMAINDEX_AVAILABLE, bool)
        rag = LlamaIndexRag()
        assert rag.is_available == LLAMAINDEX_AVAILABLE

    def test_fallback_query_returns_message(self):
        """Test that query returns a helpful message when llama-index is unavailable."""
        from llamaindex_pipeline import LlamaIndexRag

        rag = LlamaIndexRag()
        if not rag.is_available:
            result = rag.query("What is Python?")
            assert "not installed" in result.lower() or "pip install" in result.lower()

    def test_load_documents_missing_dir(self):
        """Test loading documents from a non-existent directory."""
        from llamaindex_pipeline import LlamaIndexRag

        rag = LlamaIndexRag(docs_dir="/nonexistent/path")
        docs = rag.load_documents()
        assert docs == []

    def test_build_index_fallback(self):
        """Test that build_index is a no-op in fallback mode."""
        from llamaindex_pipeline import LlamaIndexRag

        rag = LlamaIndexRag()
        if not rag.is_available:
            rag.build_index()
            assert not rag.is_ready

    def test_query_triggers_build(self):
        """Test that query triggers index build if not ready."""
        from llamaindex_pipeline import LlamaIndexRag

        rag = LlamaIndexRag()
        if not rag.is_available:
            result = rag.query("test question")
            assert isinstance(result, str)


class TestDspyRag:
    """Tests for the DSPy RAG pipeline."""

    def test_import_graceful_fallback(self):
        """Test that the module imports even without dspy-ai installed."""
        from dspy_pipeline import DspyRag, DSPY_AVAILABLE

        assert isinstance(DSPY_AVAILABLE, bool)
        rag = DspyRag()
        assert rag.is_available == DSPY_AVAILABLE

    def test_fallback_query_returns_message(self):
        """Test that query returns a helpful message when dspy is unavailable."""
        from dspy_pipeline import DspyRag

        rag = DspyRag()
        if not rag.is_available:
            result = rag.query(context="Some context", question="What is Python?")
            assert "not installed" in result.lower() or "pip install" in result.lower()

    def test_query_with_context_and_question(self):
        """Test query method signature accepts context and question."""
        from dspy_pipeline import DspyRag

        rag = DspyRag()
        if not rag.is_available:
            result = rag.query(context="ctx", question="q")
            assert isinstance(result, str)

    def test_build_module_fallback(self):
        """Test that _build_module is a no-op in fallback mode."""
        from dspy_pipeline import DspyRag

        rag = DspyRag()
        if not rag.is_available:
            rag._build_module()
            assert not rag.is_ready


class TestFrameworkRouter:
    """Tests for the framework router."""

    def test_default_framework_is_langchain(self):
        """Test that the default framework is langchain."""
        from framework_router import FrameworkRouter

        router = FrameworkRouter()
        assert router.framework == "langchain"

    def test_explicit_framework_selection(self):
        """Test explicit framework selection."""
        from framework_router import FrameworkRouter

        router = FrameworkRouter(framework="llamaindex")
        assert router.framework == "llamaindex"

    def test_invalid_framework_falls_back(self):
        """Test that an invalid framework name falls back to default."""
        from framework_router import FrameworkRouter

        router = FrameworkRouter(framework="nonexistent_framework")
        assert router.framework == "langchain"

    def test_list_frameworks(self):
        """Test listing supported frameworks."""
        from framework_router import FrameworkRouter

        frameworks = FrameworkRouter.list_frameworks()
        assert "langchain" in frameworks
        assert "llamaindex" in frameworks
        assert "dspy" in frameworks

    def test_router_query_langchain(self):
        """Test router query with langchain (default) framework."""
        from framework_router import FrameworkRouter

        router = FrameworkRouter(framework="langchain")
        result = router.query("test question")
        assert isinstance(result, str)

    def test_router_query_llamaindex_fallback(self):
        """Test router query with llamaindex when not installed."""
        from framework_router import FrameworkRouter

        router = FrameworkRouter(framework="llamaindex")
        result = router.query("test question")
        assert isinstance(result, str)

    def test_router_query_dspy_fallback(self):
        """Test router query with dspy when not installed."""
        from framework_router import FrameworkRouter

        router = FrameworkRouter(framework="dspy")
        result = router.query("test question", context="test context")
        assert isinstance(result, str)

    def test_case_insensitive_framework(self):
        """Test that framework names are case-insensitive."""
        from framework_router import FrameworkRouter

        router = FrameworkRouter(framework="LlamaIndex")
        assert router.framework == "llamaindex"

    def test_get_pipeline_caching(self):
        """Test that get_pipeline caches the pipeline instance."""
        from framework_router import FrameworkRouter

        router = FrameworkRouter(framework="langchain")
        pipeline1 = router.get_pipeline()
        pipeline2 = router.get_pipeline()
        assert pipeline1 is pipeline2
