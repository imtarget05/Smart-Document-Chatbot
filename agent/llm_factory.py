"""
LLM factory for the Ollama-compatible LLM Router service.
"""

from langchain_ollama import ChatOllama

from settings import settings


class LLMFactory:
    @staticmethod
    def get_reasoning_model(temperature: float = 0.3):
        """Return the router client; the router selects Claude for complex work."""
        return LLMFactory.get_local_model(temperature)

    @staticmethod
    def get_local_model(temperature: float = 0.3):
        """Return an Ollama client pointed at the LLM Router endpoint."""
        return ChatOllama(
            base_url=settings.llm_base_url,
            model=settings.llm_chat_model,
            temperature=temperature,
        )
