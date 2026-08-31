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


def _bool_env(name: str, default: bool) -> bool:
    val = os.getenv(name, "")
    if val == "":
        return default
    return val.lower() in ("1", "true", "yes", "on")


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
    # Local Ollama (opt-in): when LOCAL_OLLAMA_URL is set (e.g.
    # http://localhost:11434) and the server answers its health probe, chat
    # requests are served by the locally downloaded model (user pulled it via
    # `ollama pull`, e.g. qwen3:8b). When unset or unreachable the router uses
    # Cloudflare — deliberately WITHOUT mid-request fallback between the two,
    # so behaviour stays predictable (Decision: local-first, no auto-fallback).
    local_ollama_url: str = os.getenv("LOCAL_OLLAMA_URL", "")
    local_ollama_model: str = os.getenv("LOCAL_OLLAMA_MODEL", "qwen3:8b")
    local_ollama_timeout_seconds: float = _float_env(
        "LOCAL_OLLAMA_TIMEOUT_SECONDS", 120.0
    )
    local_ollama_health_ttl_seconds: float = _float_env(
        "LOCAL_OLLAMA_HEALTH_TTL_SECONDS", 10.0
    )
    # Supply chain module API (agentic tool backend). Empty = tools fall back
    # to deterministic mock results (module has no deployed API yet).
    supply_chain_api_url: str = os.getenv("SUPPLY_CHAIN_API_URL", "")
    supply_chain_timeout_seconds: float = _float_env(
        "SUPPLY_CHAIN_TIMEOUT_SECONDS", 15.0
    )
    # Prompt compression: heuristic-based token reduction before LLM calls.
    prompt_compression_enabled: bool = _bool_env("PROMPT_COMPRESSION_ENABLED", True)
    prompt_compression_ratio: float = _float_env("PROMPT_COMPRESSION_RATIO", 0.5)
    prompt_compression_min_tokens: int = _int_env("PROMPT_COMPRESSION_MIN_TOKENS", 1000)
    # Response cache: Redis-backed LLM response caching.
    response_cache_enabled: bool = _bool_env("RESPONSE_CACHE_ENABLED", True)
    response_cache_ttl_seconds: int = _int_env("RESPONSE_CACHE_TTL_SECONDS", 300)


settings = Settings()
