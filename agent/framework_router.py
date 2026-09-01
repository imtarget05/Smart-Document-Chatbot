"""
Framework router for selecting RAG implementations.

Selects which RAG framework to use based on the RAG_FRAMEWORK environment variable.
Options: "langchain" (default), "llamaindex", "dspy".
"""

from __future__ import annotations

import logging
import os
from typing import Any, Optional

logger = logging.getLogger(__name__)

SUPPORTED_FRAMEWORKS = {"langchain", "llamaindex", "dspy"}
DEFAULT_FRAMEWORK = "langchain"


class FrameworkRouter:
    """Routes RAG queries to the configured framework implementation."""

    def __init__(self, framework: Optional[str] = None) -> None:
        self._framework = (framework or os.getenv("RAG_FRAMEWORK", DEFAULT_FRAMEWORK)).lower().strip()
        if self._framework not in SUPPORTED_FRAMEWORKS:
            logger.warning(
                "Unknown framework '%s', falling back to '%s'. Supported: %s",
                self._framework,
                DEFAULT_FRAMEWORK,
                SUPPORTED_FRAMEWORKS,
            )
            self._framework = DEFAULT_FRAMEWORK
        self._pipelines: dict[str, Any] = {}

    @property
    def framework(self) -> str:
        """Return the currently selected framework name."""
        return self._framework

    def get_pipeline(self) -> Any:
        """Get or create the pipeline for the selected framework."""
        if self._framework in self._pipelines:
            return self._pipelines[self._framework]

        if self._framework == "llamaindex":
            from llamaindex_pipeline import LlamaIndexRag

            pipeline = LlamaIndexRag()
        elif self._framework == "dspy":
            from dspy_pipeline import DspyRag

            pipeline = DspyRag()
        else:
            pipeline = None

        self._pipelines[self._framework] = pipeline
        return pipeline

    def query(self, question: str, context: str = "") -> str:
        """Route a query to the selected framework's pipeline.

        Args:
            question: The user's question.
            context: Optional context (used by DSPy pipeline).

        Returns:
            The generated answer.
        """
        pipeline = self.get_pipeline()
        if pipeline is None:
            return f"LangChain pipeline is the default. Set RAG_FRAMEWORK env var to use llamaindex or dspy."
        if self._framework == "llamaindex":
            return pipeline.query(question)
        if self._framework == "dspy":
            return pipeline.query(context=context, question=question)
        return "No pipeline available."

    @staticmethod
    def list_frameworks() -> list[str]:
        """Return list of supported framework names."""
        return sorted(SUPPORTED_FRAMEWORKS)
