#!/usr/bin/env python3
"""
Model Comparison Report — Qwen vs GPT-4o vs Claude

Runs the same RAG evaluation questions against different LLM backends
and produces a comparative report with metrics per model.

Metrics: Accuracy, Hallucination Rate, Latency, Cost Estimation

Usage:
    python eval/model_comparison_report.py \
        --base-url http://localhost:8080/api \
        --token <jwt> \
        --document-id 1 \
        --output eval/results/model_comparison.json
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from typing import Any, Dict, List

import requests


def load_questions(path: str) -> List[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def ask_question_with_model(base_url: str, token: str, session_id: str,
                            document_id: int, question: str,
                            model_override: str = None) -> Dict[str, Any]:
    """Send a chat request, optionally overriding the model."""
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
    }
    payload = {
        "sessionId": session_id,
        "documentId": document_id,
        "message": question,
    }
    if model_override:
        payload["model"] = model_override

    start = time.time()
    try:
        resp = requests.post(f"{base_url}/chat/ask", json=payload,
                             headers=headers, timeout=120)
        latency_ms = round((time.time() - start) * 1000)

        if resp.status_code != 200:
            return {
                "status": "error",
                "http_status": resp.status_code,
                "latency_ms": latency_ms,
                "answer": "",
                "source_chunks": "",
                "confidence": None,
                "confidence_score": None,
            }

        data = resp.json()
        return {
            "status": "success",
            "latency_ms": latency_ms,
            "answer": data.get("aiResponse", ""),
            "source_chunks": data.get("sourceChunks", ""),
            "confidence": data.get("confidence"),
            "confidence_score": data.get("confidenceScore"),
            "rag_strategy": data.get("ragStrategy"),
            "model": data.get("model"),
        }
    except requests.exceptions.RequestException as e:
        return {
            "status": "error",
            "error": str(e),
            "latency_ms": round((time.time() - start) * 1000),
            "answer": "",
            "source_chunks": "",
            "confidence": None,
            "confidence_score": None,
        }


def evaluate_answer(result: Dict, question: Dict) -> Dict[str, Any]:
    """Score a single answer against expected keywords."""
    answer = result["answer"].lower()
    sources = (result.get("source_chunks") or "").lower()

    expected_keywords = [k.lower() for k in question["expected_answer_contains"]]
    keywords_found = [k for k in expected_keywords if k in answer]
    answer_correct = len(keywords_found) > 0

    source_keywords = [k.lower() for k in question["expected_source_keywords"]]
    source_hits = [k for k in source_keywords if k in sources]
    retrieval_accurate = len(source_hits) > 0 if sources else False

    is_hallucination = (not retrieval_accurate and answer_correct
                        and "không tìm thấy" not in answer
                        and result.get("confidence") != "low")

    return {
        "question_id": question["id"],
        "answer_correct": answer_correct,
        "keywords_found": keywords_found,
        "retrieval_accurate": retrieval_accurate,
        "is_hallucination": is_hallucination,
        "latency_ms": result["latency_ms"],
        "confidence": result.get("confidence"),
        "model": result.get("model"),
    }


def run_comparison_for_model(args, questions, model_name, model_override=None):
    """Run full eval for a single model."""
    session_id = f"compare-{model_name}-{int(time.time())}"
    details = []

    for q in questions:
        result = ask_question_with_model(
            args.base_url, args.token, session_id,
            args.document_id, q["question"], model_override
        )
        evaluation = evaluate_answer(result, q)
        details.append(evaluation)

    total = len(details)
    successful = [d for d in details if d.get("model")]
    correct = [d for d in successful if d["answer_correct"]]
    hallucinations = [d for d in successful if d["is_hallucination"]]
    latencies = [d["latency_ms"] for d in successful]

    return {
        "model": model_name,
        "total_questions": total,
        "successful": len(successful),
        "accuracy": round(len(correct) / max(len(successful), 1), 4),
        "hallucination_rate": round(len(hallucinations) / max(len(successful), 1), 4),
        "avg_latency_ms": round(sum(latencies) / max(len(latencies), 1)),
        "p95_latency_ms": round(sorted(latencies)[int(len(latencies) * 0.95) - 1] if latencies else 0),
        "details": details,
    }


def generate_report(results: List[Dict]) -> Dict[str, Any]:
    """Generate comparative report from per-model results."""
    comparison = {}
    for r in results:
        comparison[r["model"]] = {
            "accuracy": r["accuracy"],
            "hallucination_rate": r["hallucination_rate"],
            "avg_latency_ms": r["avg_latency_ms"],
            "p95_latency_ms": r["p95_latency_ms"],
        }

    sorted_by_accuracy = sorted(results, key=lambda x: x["accuracy"], reverse=True)
    winner = sorted_by_accuracy[0]["model"] if sorted_by_accuracy else None

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "winner": winner,
        "comparison": comparison,
        "per_model_results": results,
    }


def main():
    parser = argparse.ArgumentParser(description="Model Comparison Report")
    parser.add_argument("--base-url", default="http://localhost:8080/api")
    parser.add_argument("--token", required=True)
    parser.add_argument("--document-id", type=int, required=True)
    parser.add_argument("--questions", default="eval/questions.json")
    parser.add_argument("--output", default="eval/results/model_comparison.json")
    parser.add_argument("--models", nargs="+",
                        default=["local", "gpt-4o", "claude"],
                        help="Model names to compare")
    args = parser.parse_args()

    questions = load_questions(args.questions)
    print(f"🔬 Model Comparison: {len(args.models)} models × {len(questions)} questions")
    print(f"   Models: {', '.join(args.models)}")
    print()

    all_results = []
    for model in args.models:
        print(f"\n{'='*50}")
        print(f"🤖 Evaluating: {model}")
        print(f"{'='*50}")

        override = None if model == "local" else model
        result = run_comparison_for_model(args, questions, model, override)
        all_results.append(result)

        print(f"  Accuracy:        {result['accuracy']:.2%}")
        print(f"  Hallucination:   {result['hallucination_rate']:.2%}")
        print(f"  Avg Latency:     {result['avg_latency_ms']}ms")
        print(f"  P95 Latency:     {result['p95_latency_ms']}ms")

    report = generate_report(all_results)

    print(f"\n\n{'='*60}")
    print(f"📊 COMPARISON REPORT")
    print(f"{'='*60}")
    print(f"  🏆 Winner: {report['winner']}")
    print()
    for model, metrics in report["comparison"].items():
        print(f"  {model:15s} — Acc: {metrics['accuracy']:.2%}  "
              f"Hallucination: {metrics['hallucination_rate']:.2%}  "
              f"Latency: {metrics['avg_latency_ms']}ms")
    print(f"{'='*60}")

    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"\n💾 Report saved to: {args.output}")


if __name__ == "__main__":
    main()
