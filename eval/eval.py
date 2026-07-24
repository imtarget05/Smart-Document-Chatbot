#!/usr/bin/env python3
"""
Smart Document Chatbot — RAG Evaluation Pipeline

Evaluates the RAG system against a versioned question set and produces
structured metrics: retrieval accuracy, answer correctness,
hallucination rate, latency, and token estimates.

Usage:
    python eval.py --base-url http://localhost:8080/api \
                   --token <jwt> \
                   --document-id 1 \
                   --questions eval/questions.json \
                   --output eval/results/eval_results.json
"""

import argparse
import json
import os
import time
from datetime import datetime, timezone
from typing import Any

import requests

# Optional MLflow import — graceful fallback if not installed
try:
    import mlflow

    MLFLOW_AVAILABLE = True
except ImportError:
    MLFLOW_AVAILABLE = False


def load_questions(path: str) -> list[dict]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def ask_question(
    base_url: str, token: str, session_id: str, document_id: int, question: str
) -> dict[str, Any]:
    """Send a synchronous /chat/ask request and capture response + latency."""
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
    }
    payload = {
        "sessionId": session_id,
        "documentId": document_id,
        "message": question,
    }

    start = time.time()
    try:
        resp = requests.post(
            f"{base_url}/chat/ask", json=payload, headers=headers, timeout=120
        )
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


def evaluate_answer(result: dict, question: dict) -> dict[str, Any]:
    """Score a single answer against expected keywords."""
    answer = result["answer"].lower()
    sources = (result.get("source_chunks") or "").lower()

    # Answer correctness: at least one expected keyword found
    expected_keywords = [k.lower() for k in question["expected_answer_contains"]]
    keywords_found = [k for k in expected_keywords if k in answer]
    answer_correct = len(keywords_found) > 0

    # Retrieval accuracy: expected source keywords found in sourceChunks
    source_keywords = [k.lower() for k in question["expected_source_keywords"]]
    source_hits = [k for k in source_keywords if k in sources]
    retrieval_accurate = len(source_hits) > 0 if sources else False

    # Hallucination heuristic: answer is confident but retrieval has no sources
    is_hallucination = (
        not retrieval_accurate
        and answer_correct
        and "không tìm thấy" not in answer
        and result.get("confidence") != "low"
    )

    return {
        "question_id": question["id"],
        "difficulty": question["difficulty"],
        "answer_correct": answer_correct,
        "keywords_found": keywords_found,
        "retrieval_accurate": retrieval_accurate,
        "source_hits": source_hits,
        "is_hallucination": is_hallucination,
        "latency_ms": result["latency_ms"],
        "confidence": result.get("confidence"),
        "confidence_score": result.get("confidence_score"),
        "rag_strategy": result.get("rag_strategy"),
        "status": result["status"],
    }


def run_evaluation(args: argparse.Namespace) -> dict[str, Any]:
    questions = load_questions(args.questions)
    session_id = f"eval-{int(time.time())}"

    print(f"🔬 Running evaluation: {len(questions)} questions")
    print(f"   Target: {args.base_url}")
    print(f"   Document ID: {args.document_id}")
    print(f"   Session: {session_id}")
    print()

    # Start MLflow run if available
    mlflow_run = None
    if args.mlflow and MLFLOW_AVAILABLE:
        try:
            mlflow.set_tracking_uri(args.mlflow_uri)
            mlflow.set_experiment("rag-evaluation")
            mlflow_run = mlflow.start_run(run_name=f"eval-{session_id}")
            mlflow.log_params(
                {
                    "base_url": args.base_url,
                    "document_id": args.document_id,
                    "total_questions": len(questions),
                    "session_id": session_id,
                }
            )
        except Exception as e:
            print(f"  ⚠️  MLflow unavailable: {e}")
            mlflow_run = None

    details = []
    for i, q in enumerate(questions, 1):
        print(f"  [{i}/{len(questions)}] {q['question'][:60]}...", end=" ", flush=True)
        result = ask_question(
            args.base_url, args.token, session_id, args.document_id, q["question"]
        )
        evaluation = evaluate_answer(result, q)
        details.append(evaluation)

        status_icon = "✅" if evaluation["answer_correct"] else "❌"
        print(f"{status_icon} ({result['latency_ms']}ms)")

        # Log per-question metrics to MLflow
        if mlflow_run:
            try:
                mlflow.log_metrics(
                    {
                        f"q{i}_latency_ms": evaluation["latency_ms"],
                        f"q{i}_correct": 1.0 if evaluation["answer_correct"] else 0.0,
                        f"q{i}_retrieval": 1.0
                        if evaluation["retrieval_accurate"]
                        else 0.0,
                    },
                    step=i,
                )
            except Exception:
                pass

    # Aggregate metrics
    total = len(details)
    successful = [d for d in details if d["status"] == "success"]
    correct = [d for d in successful if d["answer_correct"]]
    retrieval_accurate = [d for d in successful if d["retrieval_accurate"]]
    hallucinations = [d for d in successful if d["is_hallucination"]]
    latencies = [d["latency_ms"] for d in successful]

    summary = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "base_url": args.base_url,
        "document_id": args.document_id,
        "total_questions": total,
        "successful_requests": len(successful),
        "retrieval_accuracy": round(
            len(retrieval_accurate) / max(len(successful), 1), 4
        ),
        "answer_correctness": round(len(correct) / max(len(successful), 1), 4),
        "hallucination_cases": len(hallucinations),
        "hallucination_rate": round(len(hallucinations) / max(len(successful), 1), 4),
        "average_latency_ms": round(sum(latencies) / max(len(latencies), 1)),
        "p95_latency_ms": round(
            sorted(latencies)[int(len(latencies) * 0.95) - 1] if latencies else 0
        ),
        "min_latency_ms": min(latencies) if latencies else 0,
        "max_latency_ms": max(latencies) if latencies else 0,
        "error_count": total - len(successful),
        "details": details,
    }

    # Log aggregate metrics to MLflow
    if mlflow_run:
        try:
            mlflow.log_metrics(
                {
                    "retrieval_accuracy": summary["retrieval_accuracy"],
                    "answer_correctness": summary["answer_correctness"],
                    "hallucination_rate": summary["hallucination_rate"],
                    "avg_latency_ms": summary["average_latency_ms"],
                    "p95_latency_ms": summary["p95_latency_ms"],
                    "total_questions": total,
                    "error_count": summary["error_count"],
                }
            )
            mlflow.end_run(status="FINISHED")
        except Exception:
            try:
                mlflow.end_run(status="FAILED")
            except Exception:
                pass

    return summary


def main():
    parser = argparse.ArgumentParser(description="RAG Evaluation Pipeline")
    parser.add_argument(
        "--base-url", default="http://localhost:8080/api", help="Backend API base URL"
    )
    parser.add_argument("--token", required=True, help="JWT auth token")
    parser.add_argument(
        "--document-id", type=int, required=True, help="Document ID to evaluate against"
    )
    parser.add_argument(
        "--questions", default="eval/questions.json", help="Path to questions JSON file"
    )
    parser.add_argument(
        "--output",
        default="eval/results/eval_results.json",
        help="Path to write evaluation results",
    )
    parser.add_argument(
        "--mlflow", action="store_true", help="Log results to MLflow tracking server"
    )
    parser.add_argument(
        "--mlflow-uri", default="http://mlflow:5000", help="MLflow tracking server URI"
    )
    args = parser.parse_args()

    summary = run_evaluation(args)

    # Print summary
    print()
    print("=" * 60)
    print("📊 EVALUATION RESULTS")
    print("=" * 60)
    print(f"  Total Questions:      {summary['total_questions']}")
    print(f"  Retrieval Accuracy:   {summary['retrieval_accuracy']:.2%}")
    print(f"  Answer Correctness:   {summary['answer_correctness']:.2%}")
    print(f"  Hallucination Cases:  {summary['hallucination_cases']}")
    print(f"  Hallucination Rate:   {summary['hallucination_rate']:.2%}")
    print(f"  Avg Latency:          {summary['average_latency_ms']}ms")
    print(f"  P95 Latency:          {summary['p95_latency_ms']}ms")
    print(f"  Errors:               {summary['error_count']}")
    print("=" * 60)

    # Save results
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    print(f"\n💾 Results saved to: {args.output}")


if __name__ == "__main__":
    main()
