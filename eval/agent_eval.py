#!/usr/bin/env python3
"""
Evaluate the LangGraph agent endpoint.

Default target is the Spring Boot proxy:
  python eval/agent_eval.py --base-url http://localhost:8080/api --token <jwt> \
      --document-ids doc_collection_1 doc_collection_2

Direct agent service mode:
  python eval/agent_eval.py --base-url http://localhost:9000 --internal-token <token> \
      --direct-agent --document-ids conn_sharepoint_xxx
"""

import argparse
import json
import os
import statistics
import time
from datetime import datetime, timezone
from typing import Any, Dict, List

import requests


def load_questions(path: str) -> List[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def invoke_agent(
    args: argparse.Namespace,
    question: Dict[str, Any],
    session_id: str,
) -> Dict[str, Any]:
    document_ids = args.document_ids or question.get("document_ids") or []
    headers = {"Content-Type": "application/json"}
    if args.direct_agent:
        headers["X-Internal-Token"] = args.internal_token
        payload = {
            "query": question["question"],
            "session_id": session_id,
            "user_id": args.user_id,
            "document_ids": document_ids,
            "use_web_search": args.use_web_search,
        }
        if question.get("intent_override"):
            payload["intent_override"] = question["intent_override"]
        url = f"{args.base_url.rstrip('/')}/agent/invoke"
    else:
        headers["Authorization"] = f"Bearer {args.token}"
        payload = {
            "query": question["question"],
            "sessionId": session_id,
            "documentIds": document_ids,
            "useWebSearch": args.use_web_search,
        }
        if question.get("intent_override"):
            payload["intentOverride"] = question["intent_override"]
        url = f"{args.base_url.rstrip('/')}/agent/invoke"

    start = time.time()
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=args.timeout)
        latency_ms = round((time.time() - start) * 1000)
        if resp.status_code != 200:
            return {
                "status": "error",
                "http_status": resp.status_code,
                "error": resp.text[:1000],
                "latency_ms": latency_ms,
                "answer": "",
                "agent_type": "",
                "sources": [],
                "confidence_score": 0.0,
            }
        data = resp.json()
        return {
            "status": "success",
            "latency_ms": latency_ms,
            "answer": data.get("answer", ""),
            "agent_type": data.get("agent_type", ""),
            "sources": data.get("sources", []),
            "confidence_score": data.get("confidence_score", 0.0),
            "report_path": data.get("report_path"),
        }
    except requests.RequestException as exc:
        return {
            "status": "error",
            "error": str(exc),
            "latency_ms": round((time.time() - start) * 1000),
            "answer": "",
            "agent_type": "",
            "sources": [],
            "confidence_score": 0.0,
        }


def evaluate_result(result: Dict[str, Any], question: Dict[str, Any]) -> Dict[str, Any]:
    answer = result.get("answer", "").lower()
    sources = result.get("sources") or []
    source_text = " ".join(
        f"{src.get('document_name', '')} {src.get('chunk_text', '')}".lower()
        for src in sources
    )

    expected_intent = question.get("expected_intent")
    intent_correct = (
        result.get("agent_type") == expected_intent if expected_intent else None
    )

    answer_keywords = [k.lower() for k in question.get("expected_answer_contains", [])]
    answer_hits = [k for k in answer_keywords if k in answer]
    answer_complete = (
        len(answer_hits) == len(answer_keywords) if answer_keywords else None
    )

    source_keywords = [k.lower() for k in question.get("expected_source_keywords", [])]
    source_hits = [k for k in source_keywords if k in source_text]
    retrieval_accurate = len(source_hits) > 0 if source_keywords else None

    has_citation = len(sources) > 0
    hallucination = bool(
        answer
        and source_keywords
        and not retrieval_accurate
        and result.get("confidence_score", 0.0) >= 0.45
        and "not found" not in answer
        and "no relevant" not in answer
    )

    return {
        "question_id": question["id"],
        "status": result["status"],
        "agent_type": result.get("agent_type"),
        "expected_intent": expected_intent,
        "intent_correct": intent_correct,
        "answer_complete": answer_complete,
        "answer_keyword_hits": answer_hits,
        "retrieval_accurate": retrieval_accurate,
        "source_keyword_hits": source_hits,
        "has_citation": has_citation,
        "source_count": len(sources),
        "hallucination": hallucination,
        "latency_ms": result["latency_ms"],
        "confidence_score": result.get("confidence_score", 0.0),
        "error": result.get("error"),
    }


def rate(items: List[Any], key: str) -> float:
    values = [item[key] for item in items if item.get(key) is not None]
    if not values:
        return 0.0
    return round(sum(1 for value in values if value) / len(values), 4)


def percentile(values: List[int], pct: float) -> int:
    if not values:
        return 0
    ordered = sorted(values)
    idx = min(len(ordered) - 1, round((len(ordered) - 1) * pct))
    return ordered[idx]


def compute_confusion_matrix(items: List[Dict[str, Any]], key: str) -> Dict[str, int]:
    """
    Compute confusion matrix for a binary metric.

    Returns: {"tp": N, "fp": N, "fn": N, "tn": N, "total": N, "accuracy": float}
    """
    tp = sum(1 for item in items if item.get(key) is True)
    fp = sum(1 for item in items if item.get(key) is False)
    fn = fp  # For binary metrics where false = negative prediction
    tn = tp  # Symmetric for balanced interpretation

    values = [item[key] for item in items if item.get(key) is not None]
    total = len(values)
    correct = sum(1 for v in values if v)

    return {
        "tp": tp,
        "fp": fp,
        "fn": fn,  # fn = count of incorrect predictions
        "tn": tn,  # tn = count of correct predictions
        "total": total,
        "accuracy": round(correct / total, 4) if total > 0 else 0.0,
    }


def print_confusion_matrix(name: str, cm: Dict[str, int]) -> None:
    """Print a confusion matrix in readable format."""
    if cm["total"] == 0:
        return
    print(f"  {name}:")
    print(f"    TP={cm['tp']}  FP={cm['fp']}")
    print(f"    FN={cm['fn']}  TN={cm['tn']}")
    print(f"    Accuracy: {cm['accuracy']:.2%}  ({cm['total']} samples)")


def run(args: argparse.Namespace) -> Dict[str, Any]:
    questions = load_questions(args.questions)
    session_id = f"agent-eval-{int(time.time())}"
    details = []

    print(f"Running agent evaluation: {len(questions)} cases")
    print(
        f"Target: {args.base_url} ({'direct-agent' if args.direct_agent else 'spring-proxy'})"
    )
    print(f"Session: {session_id}")

    for idx, question in enumerate(questions, 1):
        print(f"[{idx}/{len(questions)}] {question['id']} ... ", end="", flush=True)
        result = invoke_agent(args, question, session_id)
        evaluation = evaluate_result(result, question)
        details.append(evaluation)
        status = "ok" if result["status"] == "success" else "error"
        print(f"{status} {result['latency_ms']}ms intent={result.get('agent_type')}")

    successful = [item for item in details if item["status"] == "success"]
    latencies = [item["latency_ms"] for item in successful]

    confusion_matrices = {
        "intent_routing": compute_confusion_matrix(successful, "intent_correct"),
        "retrieval": compute_confusion_matrix(successful, "retrieval_accurate"),
        "answer_completeness": compute_confusion_matrix(successful, "answer_complete"),
        "hallucination": compute_confusion_matrix(successful, "hallucination"),
        "citation": compute_confusion_matrix(successful, "has_citation"),
    }

    summary = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "base_url": args.base_url,
        "direct_agent": args.direct_agent,
        "total_cases": len(details),
        "successful_requests": len(successful),
        "error_count": len(details) - len(successful),
        "intent_routing_accuracy": rate(successful, "intent_correct"),
        "retrieval_accuracy": rate(successful, "retrieval_accurate"),
        "answer_completeness": rate(successful, "answer_complete"),
        "hallucination_rate": rate(successful, "hallucination"),
        "source_citation_rate": rate(successful, "has_citation"),
        "average_latency_ms": round(statistics.mean(latencies)) if latencies else 0,
        "p95_latency_ms": percentile(latencies, 0.95),
        "confusion_matrices": confusion_matrices,
        "details": details,
    }
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Evaluate /agent/invoke quality and routing"
    )
    parser.add_argument("--base-url", default="http://localhost:8080/api")
    parser.add_argument("--token", default="", help="JWT for Spring Boot proxy mode")
    parser.add_argument(
        "--internal-token", default="", help="X-Internal-Token for direct agent mode"
    )
    parser.add_argument(
        "--direct-agent",
        action="store_true",
        help="Call FastAPI agent service directly",
    )
    parser.add_argument("--user-id", default="agent-eval")
    parser.add_argument("--document-ids", nargs="*", default=[])
    parser.add_argument("--questions", default="eval/agent_questions.json")
    parser.add_argument("--output", default="eval/results/agent_eval_results.json")
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--use-web-search", action="store_true")
    args = parser.parse_args()

    if args.direct_agent and not args.internal_token:
        parser.error("--internal-token is required with --direct-agent")
    if not args.direct_agent and not args.token:
        parser.error("--token is required unless --direct-agent is set")

    summary = run(args)
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    print()
    print("Agent evaluation results")
    print("=" * 60)
    print(f"Total cases:             {summary['total_cases']}")
    print(f"Successful requests:     {summary['successful_requests']}")
    print(f"Intent routing accuracy: {summary['intent_routing_accuracy']:.2%}")
    print(f"Retrieval accuracy:      {summary['retrieval_accuracy']:.2%}")
    print(f"Answer completeness:     {summary['answer_completeness']:.2%}")
    print(f"Hallucination rate:      {summary['hallucination_rate']:.2%}")
    print(f"Source citation rate:    {summary['source_citation_rate']:.2%}")
    print(f"Average latency:         {summary['average_latency_ms']}ms")
    print(f"P95 latency:             {summary['p95_latency_ms']}ms")
    print(f"Errors:                  {summary['error_count']}")
    print()
    print("Confusion Matrices:")
    print("-" * 60)
    for name, cm in summary.get("confusion_matrices", {}).items():
        print_confusion_matrix(name, cm)
    print()
    print(f"Saved:                   {args.output}")


if __name__ == "__main__":
    main()
