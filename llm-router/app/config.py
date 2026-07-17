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

    openrouter_api_key: str = os.getenv("OPENROUTER_API_KEY", "")
    openrouter_base_url: str = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    openrouter_model: str = os.getenv("OPENROUTER_MODEL", "qwen2.5:72b-instruct")
    cloud_timeout_seconds: float = _float_env("CLOUD_LLM_TIMEOUT_SECONDS", 60.0)

    nvidia_api_url: str = os.getenv("NVIDIA_API_URL", "https://api.nvcf.nvidia.com/v2/nvcf/pexec/functions")
    nvidia_api_key: str = os.getenv("NVIDIA_API_KEY", "")
    nvidia_model: str = os.getenv("NVIDIA_MODEL_ID", "")

    internal_token: str = os.getenv("ROUTER_INTERNAL_TOKEN", "")



settings = Settings()
