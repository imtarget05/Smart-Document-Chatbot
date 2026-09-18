"""
LLM factory for the Ollama-compatible LLM Router service.

The router talks to Cloudflare Workers AI behind the scenes; this client speaks
the Ollama wire format to the router endpoint. On the M1 Pro 16GB local plan
(2026-09-18), when LOCAL_OLLAMA_URL is set the factory points directly at the
local Ollama server — qwen2.5:3b for chat/RAG, qwen2.5-coder:1.5b for task=code.
"""

try:
    from langchain_ollama import ChatOllama
except ImportError:
    try:
        from langchain_community.chat_models import ChatOllama
    except ImportError:
        class ChatOllama:  # type: ignore[no-redef]
            def __init__(self, *args, **kwargs):
                self.args = args
                self.kwargs = kwargs

            def invoke(self, *args, **kwargs):
                raise RuntimeError("langchain_ollama is not installed")

from settings import settings


class LLMFactory:
    CODE_TASKS = {"code"}

    @staticmethod
    def _local_enabled() -> bool:
        return bool(getattr(settings, "local_ollama_url", ""))

    @staticmethod
    def model_for_task(task: str = "chat") -> str:
        """Task routing: ``code`` → coder model, else chat model.

        Returns the local model when LOCAL_OLLAMA_URL is set, otherwise the
        cloud router model.
        """
        if LLMFactory._local_enabled():
            if (task or "chat").lower() in LLMFactory.CODE_TASKS:
                return settings.local_ollama_code_model
            return settings.local_ollama_chat_model
        return settings.llm_chat_model

    @staticmethod
    def get_reasoning_model(temperature: float = 0.3, task: str = "chat"):
        """Return the router client; the router selects the model for the task."""
        return LLMFactory.get_model(temperature, task)

    @staticmethod
    def get_model(temperature: float = 0.3, task: str = "chat"):
        """Return a ChatOllama client pointed at the local Ollama server when
        LOCAL_OLLAMA_URL is set, else at the cloud-backed LLM Router."""
        if LLMFactory._local_enabled():
            return ChatOllama(
                base_url=settings.local_ollama_url,
                model=LLMFactory.model_for_task(task),
                temperature=temperature,
            )
        return ChatOllama(
            base_url=settings.llm_base_url,
            model=settings.llm_chat_model,
            temperature=temperature,
        )