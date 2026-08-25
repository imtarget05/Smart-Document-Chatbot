import os
from dataclasses import dataclass


def _float_env(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except ValueError:
        return default


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    cloudflare_account_id: str = os.getenv("CLOUDFLARE_ACCOUNT_ID", "")
    cloudflare_api_token: str = os.getenv("CLOUDFLARE_API_TOKEN", "")
    cloudflare_api_base: str = os.getenv(
        "CLOUDFLARE_API_BASE", "https://api.cloudflare.com/client/v4"
    )
    cloudflare_chat_model: str = os.getenv(
        "CLOUDFLARE_CHAT_MODEL", "@cf/meta/llama-3.3-70b-instruct-fp8-fast"
    )
    cloudflare_embed_model: str = os.getenv(
        "CLOUDFLARE_EMBED_MODEL", "@cf/baai/bge-base-en-v1.5"
    )
    cloudflare_timeout_seconds: float = _float_env("CLOUDFLARE_TIMEOUT_SECONDS", 60.0)
    # Circuit breaker: after this many consecutive provider failures the
    # circuit opens and requests fail fast for circuit_open_seconds.
    circuit_failure_threshold: int = _int_env("CIRCUIT_FAILURE_THRESHOLD", 5)
    circuit_open_seconds: float = _float_env("CIRCUIT_OPEN_SECONDS", 30.0)
    confidence_threshold: float = _float_env("ROUTER_CONFIDENCE_THRESHOLD", 0.7)
    internal_token: str = os.getenv("ROUTER_INTERNAL_TOKEN", "")


settings = Settings()