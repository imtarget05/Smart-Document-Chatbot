"""
LLM Factory – manages instantiation of local (DeepSeek) and remote (OpenRouter) models.
"""

import logging
from typing import Optional

from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI

from settings import settings

logger = logging.getLogger(__name__)

class LLMFactory:
    @staticmethod
    def get_reasoning_model(temperature: float = 0.3):
        """Returns a high-reasoning model via OpenRouter (OpenAI/Gemini)."""
        if not settings.openrouter_api_key:
            logger.warning("OPENROUTER_API_KEY not set. Falling back to local model for reasoning.")
            return LLMFactory.get_local_model(temperature)
        
        return ChatOpenAI(
            api_key=settings.openrouter_api_key,
            base_url="https://openrouter.ai/api/v1",
            model=settings.reasoning_model,
            temperature=temperature,
        )

    @staticmethod
    def get_local_model(temperature: float = 0.3):
        """Returns a local model via Ollama (DeepSeek)."""
        return ChatOllama(
            base_url=settings.llm_base_url,
            model=settings.llm_chat_model,
            temperature=temperature,
        )
