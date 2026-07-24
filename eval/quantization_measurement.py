#!/usr/bin/env python3
"""
Quantization Measurement — Model Size vs Speed vs Quality

Measures the impact of different quantization levels on:
- Model size on disk (GB)
- Memory usage during inference (GB, estimated from Ollama)
- Inference speed (tokens/second)
- Answer quality (accuracy against eval questions)

Supports Ollama models with different quantization tags, e.g.:
  - qwen2.5:7b        (default Q4_0)
  - qwen2.5:7b-fp16   (FP16 - full precision)
  - qwen2.5:7b-q8_0   (Q8_0 - 8-bit)
  - qwen2.5:7b-q4_0   (Q4_0 - 4-bit, compact)

Usage:
    python eval/quantization_measurement.py
    python eval/quantization_measurement.py --models qwen2.5:3b qwen2.5:7b --questions eval/agent_questions.json
    python eval/quantization_measurement.py --output eval/results/quantization_report.json
"""

import json
import time
import logging
import sys
from typing import Any, Dict, List, Optional
from pathlib import Path
from datetime import datetime, timezone

import httpx

logger = logging.getLogger(__name__)

OLLAMA_URL = "http://localhost:11434"
DEFAULT_MODELS = [
    "qwen2.5:0.5b",
    "qwen2.5:1.5b",
    "qwen2.5:3b",
    "qwen2.5:7b",
]

# Benchmark: measure raw generation speed (no RAG context)
BENCHMARK_PROMPTS = [
    "Explain the concept of Retrieval-Augmented Generation in 3-5 sentences.",
    "Write a short poem about artificial intelligence and document processing.",
    "Summarise the key benefits of using vector databases for semantic search.",
    "What are the main differences between corrective RAG and traditional RAG?",
    "Describe how LangGraph orchestrates multiple specialist agents.",
]


# ============================================================================
# Ollama API helpers
# ============================================================================


def get_model_details() -> List[Dict[str, Any]]:
    """Fetch all models from Ollama with size info."""
    try:
        resp = httpx.get(f"{OLLAMA_URL}/api/tags", timeout=10)
        if resp.status_code == 200:
            models = []
            for m in resp.json().get("models", []):
                # Parse quantization info from model name
                name = m.get("name", "")
                details = m.get("details", {})
                models.append(
                    {
                        "name": name,
                        "size_bytes": m.get("size", 0),
                        "size_gb": round(m.get("size", 0) / (1024**3), 2),
                        "quantization": details.get("quantization_level", "unknown"),
                        "parameter_size": details.get("parameter_size", "unknown"),
                        "family": details.get("family", "unknown"),
                        "modified_at": m.get("modified_at", ""),
                    }
                )
            return models
    except Exception as e:
        logger.warning(f"Failed to fetch model details: {e}")
    return []


def get_running_models() -> List[Dict[str, Any]]:
    """Fetch currently loaded models from Ollama's ps endpoint."""
    try:
        resp = httpx.get(f"{OLLAMA_URL}/api/ps", timeout=5)
        if resp.status_code == 200:
            return resp.json().get("models", [])
    except Exception as e:
        logger.warning(f"Failed to fetch running models: {e}")
    return []


def measure_generation_speed(
    model: str,
    prompt: str,
    timeout: int = 120,
) -> Dict[str, Any]:
    """
    Measure raw generation speed for a model.
    Returns tokens/second and detailed timing.
    """
    full_prompt = f"{prompt}\n\nProvide a concise answer."

    try:
        start = time.time()
        resp = httpx.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": model,
                "prompt": full_prompt,
                "stream": False,
                "options": {
                    "num_predict": 256,
                    "temperature": 0.0,
                },
            },
            timeout=timeout,
        )
        wall_time_s = time.time() - start

        if resp.status_code != 200:
            return {
                "status": "error",
                "error": f"HTTP {resp.status_code}: {resp.text[:200]}",
                "wall_time_s": round(wall_time_s, 3),
            }

        data = resp.json()
        eval_count = data.get("eval_count", 0)
        eval_duration_ns = data.get("eval_duration", 0)
        prompt_eval_count = data.get("prompt_eval_count", 0)
        prompt_eval_duration_ns = data.get("prompt_eval_duration", 0)

        tokens_per_second = 0.0
        if eval_duration_ns > 0:
            tokens_per_second = round(eval_count / (eval_duration_ns / 1e9), 2)

        return {
            "status": "success",
            "model": model,
            "response": data.get("response", ""),
            "prompt_tokens": prompt_eval_count,
            "completion_tokens": eval_count,
            "total_tokens": prompt_eval_count + eval_count,
            "tokens_per_second": tokens_per_second,
            "prompt_eval_duration_ns": prompt_eval_duration_ns,
            "eval_duration_ns": eval_duration_ns,
            "wall_time_s": round(wall_time_s, 3),
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "model": model,
            "wall_time_s": round(time.time() - start, 3) if "start" in dir() else 0,
        }


# ============================================================================
# Quality evaluation with quantization
# ============================================================================


def evaluate_quality(
    model: str,
    questions: List[Dict[str, Any]],
    context: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Evaluate answer quality for a given model.
    Uses keyword-based correctness checking.
    """
    results = []
    for q in questions:
        question = q.get("question", q.get("query", ""))
        expected_keywords = q.get("expected", q.get("expected_answer_contains", []))

        prompt = question
        if context:
            prompt = f"""Use ONLY the context below to answer the question.

Context:
{context}

Question: {question}

Answer concisely in 1-2 sentences."""

        try:
            start = time.time()
            resp = httpx.post(
                f"{OLLAMA_URL}/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.0, "num_predict": 256},
                },
                timeout=120,
            )
            latency_ms = round((time.time() - start) * 1000)

            if resp.status_code != 200:
                results.append(
                    {
                        "question": question,
                        "status": "error",
                        "error": f"HTTP {resp.status_code}",
                        "latency_ms": latency_ms,
                        "correct": False,
                    }
                )
                continue

            data = resp.json()
            answer = data.get("response", "")
            eval_count = data.get("eval_count", 0)

            answer_lower = answer.lower()
            found = [k for k in expected_keywords if k.lower() in answer_lower]
            correct = len(found) > 0

            results.append(
                {
                    "question": question,
                    "answer": answer[:200],
                    "expected_keywords": expected_keywords,
                    "keywords_found": found,
                    "correct": correct,
                    "latency_ms": latency_ms,
                    "eval_count": eval_count,
                    "status": "success",
                }
            )
        except Exception as e:
            results.append(
                {
                    "question": question,
                    "status": "error",
                    "error": str(e),
                    "correct": False,
                }
            )

    total = len(results)
    correct = sum(1 for r in results if r.get("correct"))
    successful = [r for r in results if r["status"] == "success"]
    latencies = [r.get("latency_ms", 0) for r in successful if r.get("latency_ms")]
    tokens = [r.get("eval_count", 0) for r in successful]

    return {
        "model": model,
        "total_questions": total,
        "correct_answers": correct,
        "accuracy": round(correct / max(total, 1), 4),
        "avg_latency_ms": round(sum(latencies) / max(len(latencies), 1))
        if latencies
        else 0,
        "total_tokens_generated": sum(tokens),
        "details": results,
    }


# ============================================================================
# Quantization Report Generator
# ============================================================================


def generate_quantization_report(
    speed_results: Dict[str, Dict[str, Any]],
    quality_results: Dict[str, Dict[str, Any]],
    model_details: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Generate a comprehensive quantization report comparing:
    - Model size
    - Inference speed (tokens/sec)
    - Answer quality (accuracy)
    - Size/speed trade-off ratio
    """
    model_info_map = {m["name"]: m for m in model_details}

    comparisons = []
    for model_name in speed_results:
        speed = speed_results.get(model_name, {})
        quality = quality_results.get(model_name, {})
        info = model_info_map.get(model_name, {})

        avg_speed = 0.0
        all_speeds = speed.get("per_prompt_speeds", [])
        if all_speeds:
            avg_speed = round(sum(all_speeds) / len(all_speeds), 2)

        comparisons.append(
            {
                "model": model_name,
                "size_gb": info.get("size_gb", 0),
                "quantization": info.get("quantization", "unknown"),
                "avg_tokens_per_second": avg_speed,
                "accuracy": quality.get("accuracy", 0),
                "avg_latency_ms": quality.get("avg_latency_ms", 0),
                "parameter_size": info.get("parameter_size", "unknown"),
            }
        )

    # Sort by tokens per second (descending)
    comparisons.sort(key=lambda x: x["avg_tokens_per_second"], reverse=True)

    # Calculate trade-off scores
    # Efficiency = tokens_per_sec / size_gb  (higher is better)
    for c in comparisons:
        if c["size_gb"] > 0 and c["avg_tokens_per_second"] > 0:
            c["efficiency_score"] = round(c["avg_tokens_per_second"] / c["size_gb"], 2)
        else:
            c["efficiency_score"] = 0

    return {
        "report_timestamp": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "total_models_measured": len(comparisons),
            "fastest_model": comparisons[0]["model"] if comparisons else None,
            "most_accurate": max(comparisons, key=lambda x: x["accuracy"])["model"]
            if comparisons
            else None,
            "most_efficient": max(comparisons, key=lambda x: x["efficiency_score"])[
                "model"
            ]
            if comparisons
            else None,
        },
        "quantization_insights": _generate_quantization_insights(comparisons),
        "comparisons": comparisons,
        "raw_speed_results": speed_results,
        "raw_quality_results": quality_results,
    }


def _generate_quantization_insights(
    comparisons: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Generate human-readable insights about quantization trade-offs."""
    if len(comparisons) < 2:
        return {"note": "Need at least 2 models to generate insights."}

    insights = []
    speed_range = max(
        c["avg_tokens_per_second"]
        for c in comparisons
        if c["avg_tokens_per_second"] > 0
    )
    speed_min = min(
        c["avg_tokens_per_second"]
        for c in comparisons
        if c["avg_tokens_per_second"] > 0
    )
    speed_gap = round(speed_range - speed_min, 2) if speed_min > 0 else 0

    if speed_gap > 0:
        insights.append(
            f"Speed gap between fastest and slowest: {speed_gap} tokens/sec "
            f"(fastest={speed_range}, slowest={speed_min})"
        )

    accuracy_range = max(c["accuracy"] for c in comparisons) - min(
        c["accuracy"] for c in comparisons
    )
    if accuracy_range <= 0.05:
        insights.append(
            f"Accuracy is stable across quantization levels "
            f"(range={accuracy_range:.2%}), suggesting quantization has minimal quality impact."
        )
    elif accuracy_range > 0.10:
        insights.append(
            f"Accuracy varies significantly (range={accuracy_range:.2%}). "
            f"Consider higher precision for quality-critical tasks."
        )

    recommended = None
    for c in comparisons:
        if c["accuracy"] >= 0.80 and c["avg_tokens_per_second"] >= speed_range * 0.5:
            recommended = c["model"]
            break

    if recommended:
        insights.append(
            f"Recommended balance: {recommended} "
            f"(accuracy={next(c['accuracy'] for c in comparisons if c['model'] == recommended):.2%}, "
            f"speed={next(c['avg_tokens_per_second'] for c in comparisons if c['model'] == recommended):.1f} tok/s)"
        )

    return {"count": len(comparisons), "insights": insights}


# ============================================================================
# Main
# ============================================================================


def load_questions(path: str) -> List[Dict[str, Any]]:
    """Load questions from a JSON file."""
    p = Path(path)
    if not p.exists():
        logger.warning(f"Questions file not found: {path}, using defaults.")
        return BENCHMARK_PROMPTS  # fallback to benchmark prompts
    with open(p, "r", encoding="utf-8") as f:
        data = json.load(f)
    # Handle both list and dict-with-questions formats
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return data.get("questions", data.get("eval_questions", []))
    return []


def main():
    import argparse

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    )

    parser = argparse.ArgumentParser(
        description="Quantization Measurement — Model Size vs Speed vs Quality"
    )
    parser.add_argument(
        "--models",
        nargs="+",
        default=DEFAULT_MODELS,
        help=f"Models to test (default: {' '.join(DEFAULT_MODELS)})",
    )
    parser.add_argument(
        "--questions",
        default="",
        help="Path to questions JSON for quality eval (optional, uses benchmark prompts if omitted)",
    )
    parser.add_argument(
        "--output",
        default="eval/results/quantization_report.json",
        help="Path to write quantization report",
    )
    parser.add_argument(
        "--benchmark-only",
        action="store_true",
        help="Only run speed benchmarks, skip quality evaluation",
    )
    args = parser.parse_args()

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"{'=' * 60}")
    print("📊 Quantization Measurement")
    print(f"{'=' * 60}")
    print(f"Models: {', '.join(args.models)}")

    # Step 1: Fetch model details from Ollama
    print("\n🔍 Fetching model details from Ollama...")
    model_details = get_model_details()
    available_models = {m["name"]: m for m in model_details}
    print(f"   Found {len(model_details)} models in Ollama")

    # Filter to requested models
    test_models = [m for m in args.models if m in available_models]
    if not test_models:
        print("❌ None of the requested models found in Ollama.")
        print(f"   Available: {list(available_models.keys())[:20]}")
        sys.exit(1)

    skipped = [m for m in args.models if m not in available_models]
    if skipped:
        print(f"   Skipped (not found): {', '.join(skipped)}")

    # Print model size info
    print(f"\n{'─' * 60}")
    print(f"{'Model':25s} {'Size':>8s} {'Quant':>10s} {'Params':>10s}")
    print(f"{'─' * 60}")
    for m in test_models:
        info = available_models[m]
        print(
            f"{m:25s} {info['size_gb']:>7.1f}GB {info['quantization']:>10s} {info['parameter_size']:>10s}"
        )
    print(f"{'─' * 60}")

    # Step 2: Measure generation speed
    print(f"\n⚡ Measuring generation speed ({len(BENCHMARK_PROMPTS)} prompts)...")
    speed_results: Dict[str, Dict[str, Any]] = {}

    for model in test_models:
        print(f"\n   🤖 {model}")
        per_prompt_speeds = []
        per_prompt_details = []

        for i, prompt in enumerate(BENCHMARK_PROMPTS, 1):
            print(
                f"      [{i}/{len(BENCHMARK_PROMPTS)}] Measuring...",
                end=" ",
                flush=True,
            )
            result = measure_generation_speed(model, prompt)

            if result["status"] == "success":
                tok_s = result.get("tokens_per_second", 0)
                per_prompt_speeds.append(tok_s)
                print(f"✅ {tok_s:.1f} tok/s ({result['completion_tokens']} tokens)")
            else:
                print(f"❌ {result.get('error', 'unknown error')[:50]}")

            per_prompt_details.append(result)

        avg_speed = (
            round(sum(per_prompt_speeds) / max(len(per_prompt_speeds), 1), 2)
            if per_prompt_speeds
            else 0
        )
        speed_results[model] = {
            "model": model,
            "avg_tokens_per_second": avg_speed,
            "per_prompt_speeds": per_prompt_speeds,
            "details": per_prompt_details,
        }
        print(f"      📊 Avg: {avg_speed} tok/s")

    # Step 3: Evaluate quality (optional)
    quality_results: Dict[str, Dict[str, Any]] = {}

    if not args.benchmark_only:
        questions = []
        if args.questions:
            questions = load_questions(args.questions)

        if questions:
            print(f"\n🎯 Evaluating answer quality ({len(questions)} questions)...")
            for model in test_models:
                print(f"   🤖 {model}...", end=" ", flush=True)
                quality = evaluate_quality(model, questions)
                quality_results[model] = quality
                print(
                    f"accuracy={quality['accuracy']:.2%}, latency={quality['avg_latency_ms']}ms"
                )
        else:
            print(
                "\n⏭️  Skipping quality eval (no questions file provided, use --questions)"
            )
            for model in test_models:
                quality_results[model] = {
                    "model": model,
                    "accuracy": 0,
                    "avg_latency_ms": 0,
                    "total_questions": 0,
                }
    else:
        print("\n⏭️  Skipping quality eval (--benchmark-only)")
        for model in test_models:
            quality_results[model] = {
                "model": model,
                "accuracy": 0,
                "avg_latency_ms": 0,
                "total_questions": 0,
            }

    # Step 4: Generate and save report
    print("\n📊 Generating quantization report...")
    report = generate_quantization_report(speed_results, quality_results, model_details)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"   💾 Report saved to: {output_path}")

    # Print summary
    print(f"\n{'=' * 60}")
    print("📊 QUANTIZATION REPORT SUMMARY")
    print(f"{'=' * 60}")

    summary = report["summary"]
    if summary.get("most_efficient"):
        print(f"  ⚡ Most efficient:  {summary['most_efficient']}")
    if summary.get("fastest_model"):
        print(f"  🚀 Fastest:         {summary['fastest_model']}")
    if summary.get("most_accurate"):
        print(f"  🎯 Most accurate:   {summary['most_accurate']}")

    print(f"\n{'─' * 60}")
    print(f"{'Model':25s} {'Size':>7s} {'Speed':>10s} {'Acc':>7s} {'Eff':>8s}")
    print(f"{'─' * 60}")
    for c in report["comparisons"]:
        speed_str = (
            f"{c['avg_tokens_per_second']:.1f}t/s"
            if c["avg_tokens_per_second"] > 0
            else "N/A"
        )
        acc_str = f"{c['accuracy']:.1%}" if c["accuracy"] > 0 else "N/A"
        eff_str = f"{c['efficiency_score']:.1f}" if c["efficiency_score"] > 0 else "N/A"
        print(
            f"{c['model']:25s} {c['size_gb']:>5.1f}GB {speed_str:>10s} {acc_str:>7s} {eff_str:>8s}"
        )
    print(f"{'─' * 60}")

    # Print insights
    insights = report.get("quantization_insights", {}).get("insights", [])
    if insights:
        print("\n💡 Insights:")
        for insight in insights:
            print(f"  • {insight}")

    print(f"\n{'=' * 60}")
    print(f"Done. Full report: {output_path}")


if __name__ == "__main__":
    main()
