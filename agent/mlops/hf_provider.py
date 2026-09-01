"""
Hugging Face Local Model Provider for Smart Document Chatbot.

Provides local inference capabilities using Hugging Face transformers.
Supports embeddings and text generation with graceful fallback.
"""

import os
import logging
from typing import List, Optional, Dict, Any

logger = logging.getLogger(__name__)

TRANSFORMERS_AVAILABLE = False
try:
    import torch
    from transformers import AutoTokenizer, AutoModel, AutoModelForCausalLM
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    logger.warning(
        "transformers/torch not installed. HuggingFaceProvider will use fallback mode. "
        "Install with: pip install transformers torch"
    )

DEFAULT_EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
DEFAULT_CHAT_MODEL = "microsoft/DialoGPT-medium"
MAX_LENGTH = 512
EMBEDDING_DIM = 384


class HuggingFaceProvider:
    """
    Local Hugging Face model provider for embeddings and text generation.

    Supports:
        - sentence-transformers/all-MiniLM-L6-v2 (embeddings)
        - microsoft/DialoGPT-medium (chat)

    Usage:
        provider = HuggingFaceProvider()
        embeddings = provider.embed(["Hello world"])
        response = provider.generate("What is RAG?")
    """

    def __init__(
        self,
        embedding_model: str = DEFAULT_EMBEDDING_MODEL,
        chat_model: str = DEFAULT_CHAT_MODEL,
        device: Optional[str] = None,
        load_on_init: bool = True,
    ):
        self.embedding_model_name = embedding_model
        self.chat_model_name = chat_model
        self.device = device or ("cuda" if TRANSFORMERS_AVAILABLE and torch.cuda.is_available() else "cpu")

        self._embedding_tokenizer = None
        self._embedding_model = None
        self._chat_tokenizer = None
        self._chat_model = None

        if load_on_init and TRANSFORMERS_AVAILABLE:
            self._load_models()

    def _load_models(self):
        """Load both embedding and chat models into memory."""
        if not TRANSFORMERS_AVAILABLE:
            logger.warning("Cannot load models: transformers not available")
            return

        logger.info(f"Loading embedding model: {self.embedding_model_name}")
        try:
            self._embedding_tokenizer = AutoTokenizer.from_pretrained(
                self.embedding_model_name
            )
            self._embedding_model = AutoModel.from_pretrained(
                self.embedding_model_name
            ).to(self.device)
            self._embedding_model.eval()
            logger.info(f"Embedding model loaded on {self.device}")
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            self._embedding_model = None

        logger.info(f"Loading chat model: {self.chat_model_name}")
        try:
            self._chat_tokenizer = AutoTokenizer.from_pretrained(
                self.chat_model_name
            )
            self._chat_model = AutoModelForCausalLM.from_pretrained(
                self.chat_model_name
            ).to(self.device)
            self._chat_model.eval()
            logger.info(f"Chat model loaded on {self.device}")
        except Exception as e:
            logger.error(f"Failed to load chat model: {e}")
            self._chat_model = None

    @property
    def is_available(self) -> bool:
        """Check if HuggingFace transformers is available."""
        return TRANSFORMERS_AVAILABLE

    @property
    def has_embedding_model(self) -> bool:
        """Check if embedding model is loaded."""
        return self._embedding_model is not None

    @property
    def has_chat_model(self) -> bool:
        """Check if chat model is loaded."""
        return self._chat_model is not None

    def embed(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for a list of texts.

        Args:
            texts: List of text strings to embed

        Returns:
            List of embedding vectors (list of floats)

        Raises:
            RuntimeError: If embedding model is not available
        """
        if not TRANSFORMERS_AVAILABLE or self._embedding_model is None:
            logger.warning("Embedding model not available, returning zero vectors")
            return [[0.0] * EMBEDDING_DIM for _ in texts]

        import torch

        embeddings = []
        with torch.no_grad():
            for text in texts:
                inputs = self._embedding_tokenizer(
                    text,
                    return_tensors="pt",
                    padding=True,
                    truncation=True,
                    max_length=MAX_LENGTH,
                ).to(self.device)

                outputs = self._embedding_model(**inputs)

                # Use mean pooling of last hidden state
                attention_mask = inputs["attention_mask"]
                token_embeddings = outputs.last_hidden_state
                expanded_mask = attention_mask.unsqueeze(-1).float()
                sum_embeddings = (token_embeddings * expanded_mask).sum(dim=1)
                pooled = sum_embeddings / expanded_mask.sum(dim=1).clamp(min=1e-9)

                embeddings.append(pooled[0].cpu().tolist())

        return embeddings

    def generate(self, prompt: str, max_tokens: int = 128) -> str:
        """
        Generate text response for a given prompt.

        Args:
            prompt: Input text prompt
            max_tokens: Maximum number of tokens to generate

        Returns:
            Generated text response

        Raises:
            RuntimeError: If chat model is not available
        """
        if not TRANSFORMERS_AVAILABLE or self._chat_model is None:
            logger.warning("Chat model not available, returning fallback response")
            return self._fallback_response(prompt)

        import torch

        inputs = self._chat_tokenizer(
            prompt,
            return_tensors="pt",
            truncation=True,
            max_length=MAX_LENGTH,
        ).to(self.device)

        with torch.no_grad():
            output_ids = self._chat_model.generate(
                inputs["input_ids"],
                attention_mask=inputs.get("attention_mask"),
                max_new_tokens=max_tokens,
                do_sample=True,
                temperature=0.7,
                top_p=0.9,
                pad_token_id=self._chat_tokenizer.eos_token_id,
            )

        response = self._chat_tokenizer.decode(
            output_ids[0][inputs["input_ids"].shape[1]:],
            skip_special_tokens=True,
        )
        return response.strip()

    def _fallback_response(self, prompt: str) -> str:
        """Generate a fallback response when model is unavailable."""
        return (
            f"[Fallback] Local model unavailable. "
            f"Received prompt: '{prompt[:100]}...' "
            f"Install transformers to enable local inference."
        )

    def get_model_info(self) -> Dict[str, Any]:
        """Get information about loaded models."""
        return {
            "embedding_model": {
                "name": self.embedding_model_name,
                "loaded": self.has_embedding_model,
                "dim": EMBEDDING_DIM,
            },
            "chat_model": {
                "name": self.chat_model_name,
                "loaded": self.has_chat_model,
            },
            "device": self.device,
            "transformers_available": TRANSFORMERS_AVAILABLE,
        }


def get_hf_provider(
    embedding_model: Optional[str] = None,
    chat_model: Optional[str] = None,
) -> HuggingFaceProvider:
    """
    Factory function to get a HuggingFaceProvider instance.

    Args:
        embedding_model: Override embedding model name
        chat_model: Override chat model name

    Returns:
        HuggingFaceProvider instance
    """
    return HuggingFaceProvider(
        embedding_model=embedding_model or os.getenv("HF_EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL),
        chat_model=chat_model or os.getenv("HF_CHAT_MODEL", DEFAULT_CHAT_MODEL),
    )
