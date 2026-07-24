"""Model pricing tables and token estimation utilities."""

from dataclasses import dataclass
from typing import Dict


@dataclass
class ModelPricing:
    provider: str
    model_id: str
    input_per_1k: float
    output_per_1k: float
    is_local: bool = True


MODEL_CATALOG: Dict[str, ModelPricing] = {
    "llama3.2:3b": ModelPricing("ollama", "llama3.2:3b", 0.15, 0.15, is_local=True),
    "llama3.2:1b": ModelPricing("ollama", "llama3.2:1b", 0.08, 0.08, is_local=True),
    "qwen2.5:32b-instruct": ModelPricing("ollama", "qwen2.5:32b-instruct", 0.90, 0.90, is_local=True),
    "qwen2.5:14b": ModelPricing("ollama", "qwen2.5:14b", 0.50, 0.50, is_local=True),
    "qwen2.5:7b": ModelPricing("ollama", "qwen2.5:7b", 0.25, 0.25, is_local=True),
    "nomic-embed-text": ModelPricing("ollama", "nomic-embed-text", 0.02, 0.02, is_local=True),
}

EMBEDDING_MODEL = "nomic-embed-text"
SIMPLE_CHAT_MODEL = "llama3.2:3b"
COMPLEX_CHAT_MODEL = "qwen2.5:32b-instruct"


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

    gpu_map = {
        "llama3.2:3b": {"gpu": "None (CPU)", "vram_gb": 2, "monthly_gpu_cost": 0},
        "llama3.2:1b": {"gpu": "None (CPU)", "vram_gb": 1, "monthly_gpu_cost": 0},
        "qwen2.5:7b": {"gpu": "T4 (16GB)", "vram_gb": 6, "monthly_gpu_cost": 350},
        "qwen2.5:14b": {"gpu": "T4 (16GB)", "vram_gb": 10, "monthly_gpu_cost": 350},
        "qwen2.5:32b-instruct": {
            "gpu": "A10G (24GB)",
            "vram_gb": 20,
            "monthly_gpu_cost": 750,
        },
        "nomic-embed-text": {"gpu": "None (CPU)", "vram_gb": 1, "monthly_gpu_cost": 0},
    }
    info = gpu_map.get(model_id, {"gpu": "Unknown", "vram_gb": 0, "monthly_gpu_cost": 0})

    avg_input_tokens = 500
    avg_output_tokens = 200
    per_query_cost = (
        (avg_input_tokens / 1000 * pricing.input_per_1k)
        + (avg_output_tokens / 1000 * pricing.output_per_1k)
        + info["monthly_gpu_cost"] / max(monthly_queries, 1)
    )

    return {
        "model": model_id,
        "recommended_gpu": info["gpu"],
        "vram_gb": info["vram_gb"],
        "monthly_gpu_cost_usd": info["monthly_gpu_cost"],
        "per_query_inference_cost_usd": round(per_query_cost, 6),
        "monthly_inference_cost_usd": round(per_query_cost * monthly_queries, 2),
        "monthly_total_usd": round(
            per_query_cost * monthly_queries + info["monthly_gpu_cost"], 2
        ),
        "monthly_queries": monthly_queries,
    }
