"""Model pricing tables and token estimation utilities."""

from dataclasses import dataclass
from typing import Dict


@dataclass
class ModelPricing:
    provider: str
    model_id: str
    input_per_1k: float
    output_per_1k: float
    is_local: bool = False


CHAT_MODEL = "@cf/meta/llama-3.3-70b-instruct-fp8-fast"
EMBEDDING_MODEL = "@cf/baai/bge-base-en-v1.5"

MODEL_CATALOG: Dict[str, ModelPricing] = {
    CHAT_MODEL: ModelPricing("cloudflare", CHAT_MODEL, 0.0, 0.0),
    EMBEDDING_MODEL: ModelPricing("cloudflare", EMBEDDING_MODEL, 0.0, 0.0),
}

SIMPLE_CHAT_MODEL = CHAT_MODEL
COMPLEX_CHAT_MODEL = CHAT_MODEL


def estimate_tokens(text: str) -> int:
    return int(len(text.split()) * 1.3 + 0.5)


def calculate_cost(model_id: str, input_text: str, output_text: str) -> Dict:
    pricing = MODEL_CATALOG.get(model_id)
    if not pricing:
        return {"error": f"Unknown model: {model_id}", "estimated_cost_usd": 0}

    input_tokens = estimate_tokens(input_text)
    output_tokens = estimate_tokens(output_text)
    cost = (input_tokens / 1000 * pricing.input_per_1k) + (
        output_tokens / 1000 * pricing.output_per_1k
    )

    return {
        "model": model_id,
        "provider": pricing.provider,
        "is_local": pricing.is_local,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": input_tokens + output_tokens,
        "estimated_cost_usd": round(cost, 6),
        "input_rate_per_1k": pricing.input_per_1k,
        "output_rate_per_1k": pricing.output_per_1k,
    }


def get_hardware_cost_estimate(model_id: str, monthly_queries: int = 100000) -> Dict:
    pricing = MODEL_CATALOG.get(model_id)
    if not pricing or not pricing.is_local:
        return {"note": "Hardware cost estimate only for local models"}
    return {
        "model": model_id,
        "recommended_gpu": "None",
        "vram_gb": 0,
        "monthly_gpu_cost_usd": 0,
        "per_query_inference_cost_usd": 0,
        "monthly_inference_cost_usd": 0,
        "monthly_total_usd": 0,
        "monthly_queries": monthly_queries,
    }