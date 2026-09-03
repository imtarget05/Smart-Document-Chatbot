"""
Lightweight DSPy RAG pipeline.

Provides structured LLM prompting for RAG using DSPy signatures.
Falls back gracefully if dspy-ai is not installed.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)

try:
    import dspy

    DSPY_AVAILABLE = True

    class RAGSignature(dspy.Signature):
        """DSPy signature for RAG: given context and question, produce an answer."""

        context = dspy.InputField(desc="Retrieved document context")
        question = dspy.InputField(desc="User question")
        answer = dspy.OutputField(desc="Generated answer based on context")

except ImportError:
    DSPY_AVAILABLE = False
    logger.warning("dspy-ai not installed. DspyRag will use fallback mode.")
    RAGSignature = None  # type: ignore


class DspyRag:
    """DSPy-based RAG pipeline for structured LLM prompting.

    Defines a DSPy signature for RAG and provides a query method that
    generates answers from context and questions.
    """

    def __init__(
        self,
        llm_model: str = "llama3.1",
        llm_base_url: str = "http://localhost:11434",
        use_ollama: bool = True,
    ) -> None:
        self.llm_model = llm_model
        self.llm_base_url = llm_base_url
        self.use_ollama = use_ollama
        self._rag_module: Optional[Any] = None
        self._fallback_mode = not DSPY_AVAILABLE

    def _configure_lm(self) -> None:
        """Configure the DSPy language model."""
        if self._fallback_mode:
            return
        if self.use_ollama:
            lm = dspy.OllamaLocal(
                model=self.llm_model,
                base_url=self.llm_base_url,
            )
        else:
            lm = dspy.LM(model=self.llm_model)
        dspy.settings.configure(lm=lm)

    def _build_module(self) -> None:
        """Build the DSPy RAG module."""
        if self._fallback_mode:
            return
        self._configure_lm()
        self._rag_module = dspy.ChainOfThought(RAGSignature)

    def query(self, context: str, question: str) -> str:
        """Generate an answer from context and question using DSPy.

        Args:
            context: Retrieved document context.
            question: User question.

        Returns:
            Generated answer string.
        """
        if self._fallback_mode:
            return (
                "DSPy is not installed. Install with: pip install dspy-ai"
            )
        if self._rag_module is None:
            self._build_module()
        if self._rag_module is None:
            return "DSPy module not initialized."
        try:
            result = self._rag_module(context=context, question=question)
            return str(result.answer)
        except Exception as exc:  # noqa: BLE001 — degrade gracefully when LLM unreachable
            logger.warning("DSPy LLM call failed (%s): %s; falling backto a helpful message",
                          type(exc).__name__, exc)
            return ("DSPy could not reach its LLM endpoint, so no answer could be "
                    "generated. Check that the LLM router / Ollama is reachable.")

    @property
    def is_available(self) -> bool:
        """Check if DSPy is available."""
        return DSPY_AVAILABLE

    @property
    def is_ready(self) -> bool:
        """Check if the DSPy module is built and ready."""
        return self._rag_module is not None
