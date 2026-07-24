import os
from dataclasses import dataclass


def _float_env(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    local_base_url: str = os.getenv("LOCAL_LLM_BASE_URL", "http://ollama:11434")
    chat_model_simple: str = os.getenv("LOCAL_CHAT_MODEL_SIMPLE", "llama3.2:3b")
    chat_model_complex: str = os.getenv("LOCAL_CHAT_MODEL_COMPLEX", "qwen2.5:32b-instruct")
    embed_model: str = os.getenv("LOCAL_EMBED_MODEL", "nomic-embed-text")
    local_timeout_seconds: float = _float_env("LOCAL_LLM_TIMEOUT_SECONDS", 180.0)
    confidence_threshold: float = _float_env("ROUTER_CONFIDENCE_THRESHOLD", 0.7)
    internal_token: str = os.getenv("ROUTER_INTERNAL_TOKEN", "")


settings = Settings()
