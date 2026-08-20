"""
LLM factory for the Ollama-compatible LLM Router service.

The router talks to Cloudflare Workers AI behind the scenes; this client speaks
the Ollama wire format to the router endpoint.
"""

from langchain_ollama import ChatOllama

from settings import settings


class LLMFactory:
    @staticmethod
    def get_reasoning_model(temperature: float = 0.3):
        """Return the router client; the router selects the model for the task."""
        return LLMFactory.get_model(temperature)

    @staticmethod
    def get_model(temperature: float = 0.3):
        """Return a ChatOllama client pointed at the cloud-backed LLM Router."""
        return ChatOllama(
            base_url=settings.llm_base_url,
            model=settings.llm_chat_model,
            temperature=temperature,
        )