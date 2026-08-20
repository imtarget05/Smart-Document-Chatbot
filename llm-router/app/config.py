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
    chat_model_simple: str = os.getenv("LOCAL_CHAT_MODEL_SIMPLE", "qwen2.5:7b")
    chat_model_complex: str = os.getenv("LOCAL_CHAT_MODEL_COMPLEX", "qwen2.5:7b")
    embed_model: str = os.getenv("LOCAL_EMBED_MODEL", "nomic-embed-text")
    local_timeout_seconds: float = _float_env("LOCAL_LLM_TIMEOUT_SECONDS", 180.0)
    confidence_threshold: float = _float_env("ROUTER_CONFIDENCE_THRESHOLD", 0.7)
    internal_token: str = os.getenv("ROUTER_INTERNAL_TOKEN", "")

    # Cloudflare Workers AI (primary provider, optional fallback to local Ollama)
    cloudflare_account_id: str = os.getenv("CLOUDFLARE_ACCOUNT_ID", "")
    cloudflare_api_token: str = os.getenv("CLOUDFLARE_API_TOKEN", "")
    cloudflare_chat_model: str = os.getenv(
        "CLOUDFLARE_CHAT_MODEL", "@cf/meta/llama-3.3-70b-instruct-fp8-fast"
    )
    cloudflare_embed_model: str = os.getenv(
        "CLOUDFLARE_EMBED_MODEL", "@cf/baai/bge-base-en-v1.5"
    )
    cloudflare_api_base: str = os.getenv(
        "CLOUDFLARE_API_BASE", "https://api.cloudflare.com/client/v4"
    )
    cloudflare_timeout_seconds: float = _float_env("CLOUDFLARE_TIMEOUT_SECONDS", 60.0)
    # Consecutive failures before the circuit breaker locks Cloudflare out.
    circuit_breaker_threshold: int = int(
        os.getenv("CIRCUIT_BREAKER_THRESHOLD", "5")
    )


settings = Settings()
