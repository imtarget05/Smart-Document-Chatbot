import os
from dataclasses import dataclass


def _float_env(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    local_base_url: str = os.getenv("LOCAL_LLM_BASE_URL", "http://llm:11434")
    local_model: str = os.getenv("LOCAL_LLM_MODEL", "llama3.2:3b")
    local_timeout_seconds: float = _float_env("LOCAL_LLM_TIMEOUT_SECONDS", 3.0)
    confidence_threshold: float = _float_env("ROUTER_CONFIDENCE_THRESHOLD", 0.7)

    anthropic_api_url: str = os.getenv("ANTHROPIC_API_URL", "https://api.anthropic.com/v1/messages")
    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")
    anthropic_model: str = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")
    anthropic_version: str = os.getenv("ANTHROPIC_VERSION", "2023-06-01")

    openai_api_url: str = os.getenv("OPENAI_API_URL", "https://api.openai.com/v1/chat/completions")
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    vision_model: str = os.getenv("OPENAI_VISION_MODEL", "gpt-4o")
    cloud_timeout_seconds: float = _float_env("CLOUD_LLM_TIMEOUT_SECONDS", 60.0)

    nvidia_api_url: str = os.getenv("NVIDIA_API_URL", "https://api.nvcf.nvidia.com/v2/nvcf/pexec/functions")
    nvidia_api_key: str = os.getenv("NVIDIA_API_KEY", "")
    nvidia_model: str = os.getenv("NVIDIA_MODEL_ID", "")

    internal_token: str = os.getenv("ROUTER_INTERNAL_TOKEN", "")



settings = Settings()
