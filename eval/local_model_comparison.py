#!/usr/bin/env python3
"""
Local Model Comparison — RAG Context Evaluation

Tests LLM models with RAG context provided in the prompt.
This is the REAL use case: can the model extract answers from provided context?

Usage:
    python eval/local_model_comparison.py
"""

import json
import time
import httpx
from pathlib import Path

OLLAMA_URL = "http://localhost:11434"
ALL_MODELS = ["qwen2.5:3b", "llama3.2:1b", "qwen2.5:7b", "qwen2.5:14b"]

# RAG Context extracted from actual project documentation
RAG_CONTEXT = """
Smart Document Chatbot - Enterprise Agentic CRAG Platform

Tech Stack:
- Backend: Spring Boot 3.2.x (Java), REST API under context-path /api
- Frontend: React 18 + Vite 5 + TypeScript 5 (strict mode) + TanStack Query v5
- Vector Database: Qdrant for vector storage and similarity search
- Embeddings: Ollama with nomic-embed-text model
- LLM: Ollama local models, also supports Claude, GPT via LLM Router
- Database: PostgreSQL 15 for chat history, document metadata, user data
- ETL Pipeline: Apache Airflow for document ingestion
- Streaming: Server-Sent Events (SSE) via Spring Boot SseEmitter, NDJSON from Ollama
- Monitoring: Prometheus + Grafana

Architecture:
- Frontend -> Spring Boot API gateway -> Python Agent Service -> LangGraph Orchestrator -> Specialist Agents
- 7 specialist agents: orchestrator, rag, report, comparator, researcher, action, engineering_analysis
- Corrective RAG (CRAG) with confidence threshold of 0.45
- Query reformulation when confidence is low
- Web search fallback via Tavily API when documents lack information
- Deep reasoning fallback for questions outside document scope

Document Processing:
- Supports PDF, DOCX, TXT formats
- Hierarchical chunking with overlapping strategy
- Apache Airflow ETL pipeline: page splitting, content cleaning, embedding generation, Qdrant indexing
- Multi-document synthesis: single file mode or multi-file chat mode

Features:
- Visual Concept Mapping: AI extracts core concepts and builds mind maps as SVG
- Citations: transparent source attribution (file metadata, original paragraph content)
- Agent chat mode via Python FastAPI agent service
- n8n workflow automation integration
"""

QUESTIONS = [
    {
        "id": 1,
        "question": "Hệ thống sử dụng framework nào cho backend?",
        "expected": ["spring boot"],
    },
    {
        "id": 2,
        "question": "Vector database được sử dụng là gì?",
        "expected": ["qdrant"],
    },
    {
        "id": 3,
        "question": "Chunking strategy được sử dụng trong RAG là gì?",
        "expected": ["hierarchical", "overlapping"],
    },
    {
        "id": 4,
        "question": "Confidence threshold của hệ thống là bao nhiêu?",
        "expected": ["0.45"],
    },
    {
        "id": 5,
        "question": "Hệ thống hỗ trợ những định dạng tài liệu nào?",
        "expected": ["pdf", "docx", "txt"],
    },
    {
        "id": 6,
        "question": "Streaming response sử dụng protocol nào?",
        "expected": ["sse", "server-sent events"],
    },
    {
        "id": 7,
        "question": "Frontend sử dụng công nghệ gì?",
        "expected": ["react", "vite"],
    },
    {
        "id": 8,
        "question": "Hệ thống có bao nhiêu specialist agents?",
        "expected": ["7"],
    },
    {
        "id": 9,
        "question": "Ollama model nào được dùng để generate embeddings?",
        "expected": ["nomic-embed-text"],
    },
    {
        "id": 10,
        "question": "Corrective RAG hoạt động như thế nào?",
        "expected": ["confidence", "reformulation"],
    },
    {
        "id": 11,
        "question": "Khi nào hệ thống sử dụng web search fallback?",
        "expected": ["low confidence", "thấp", "thiếu", "lack"],
    },
    {
        "id": 12,
        "question": "Hệ thống lưu trữ lịch sử chat ở đâu?",
        "expected": ["postgresql"],
    },
    {
        "id": 13,
        "question": "LLM Router hỗ trợ những provider nào?",
        "expected": ["ollama", "claude", "gpt"],
    },
    {
        "id": 14,
        "question": "Airflow được sử dụng để làm gì?",
        "expected": ["etl", "ingestion", "pipeline"],
    },
    {
        "id": 15,
        "question": "Monitoring stack gồm những thành phần nào?",
        "expected": ["prometheus", "grafana"],
    },
]


def ask_ollama(model: str, question: str) -> dict:
    """Send a question with RAG context to Ollama and measure response."""
    prompt = f"""You are a helpful assistant. Use ONLY the context below to answer the question.
If the answer is not in the context, say "I don't have enough information".
Answer concisely in 1-2 sentences.

Context:
{RAG_CONTEXT}

Question: {question}

Answer:"""

    start = time.time()
    try:
        resp = httpx.post(
            f"{OLLAMA_URL}/api/generate",
            json={"model": model, "prompt": prompt, "stream": False},
            timeout=180,
        )
        latency_ms = round((time.time() - start) * 1000)

        if resp.status_code == 200:
            data = resp.json()
            return {
                "status": "success",
                "answer": data.get("response", ""),
                "latency_ms": latency_ms,
                "eval_count": data.get("eval_count", 0),
                "eval_duration_ns": data.get("eval_duration", 0),
            }
        else:
            return {"status": "error", "latency_ms": latency_ms, "answer": ""}
    except Exception as e:
        return {
            "status": "error",
            "latency_ms": round((time.time() - start) * 1000),
            "answer": "",
            "error": str(e),
        }


def evaluate_answer(answer: str, expected_keywords: list) -> dict:
    """Check if expected keywords appear in the answer."""
    answer_lower = answer.lower()
    found = [k for k in expected_keywords if k.lower() in answer_lower]
    return {
        "correct": len(found) > 0,
        "keywords_found": found,
        "keywords_expected": expected_keywords,
    }


def run_comparison():
    """Run comparison across all models."""
    results = {}

    for model in MODELS:
        print(f"\n{'=' * 50}")
        print(f"🤖 Model: {model}")
        print(f"{'=' * 50}")

        model_results = []
        for q in QUESTIONS:
            print(f"  [{q['id']:2d}/15] {q['question'][:50]}...", end=" ", flush=True)

            response = ask_ollama(model, q["question"])
            evaluation = evaluate_answer(response["answer"], q["expected"])

            result = {
                "question_id": q["id"],
                "question": q["question"],
                "answer": response["answer"],
                "correct": evaluation["correct"],
                "keywords_found": evaluation["keywords_found"],
                "latency_ms": response["latency_ms"],
                "eval_count": response.get("eval_count", 0),
                "status": response["status"],
            }
            model_results.append(result)

            icon = "✅" if evaluation["correct"] else "❌"
            print(f"{icon} ({response['latency_ms']}ms)")

        # Aggregate
        successful = [r for r in model_results if r["status"] == "success"]
        correct = [r for r in model_results if r["correct"]]
        latencies = [r["latency_ms"] for r in successful]

        summary = {
            "model": model,
            "total": len(model_results),
            "successful": len(successful),
            "accuracy": round(len(correct) / max(len(model_results), 1), 4),
            "avg_latency_ms": round(sum(latencies) / max(len(latencies), 1)),
            "p95_latency_ms": round(
                sorted(latencies)[int(len(latencies) * 0.95) - 1] if latencies else 0
            ),
            "total_tokens": sum(r.get("eval_count", 0) for r in model_results),
            "details": model_results,
        }
        results[model] = summary

        print(f"\n  Accuracy:    {summary['accuracy']:.2%}")
        print(f"  Avg Latency: {summary['avg_latency_ms']}ms")
        print(f"  P95 Latency: {summary['p95_latency_ms']}ms")
        print(f"  Total Tokens: {summary['total_tokens']:,}")

    return results


def print_final_report(results: dict):
    """Print comparative report."""
    print(f"\n\n{'=' * 60}")
    print("📊 FINAL COMPARISON REPORT (RAG Context)")
    print(f"{'=' * 60}")

    sorted_models = sorted(results.values(), key=lambda x: x["accuracy"], reverse=True)

    header = f"{'Model':20s} {'Accuracy':>10s} {'Avg Latency':>12s} {'P95 Latency':>12s} {'Tokens':>10s}"
    print(header)
    print("-" * len(header))

    for r in sorted_models:
        print(
            f"{r['model']:20s} {r['accuracy']:>10.2%} {r['avg_latency_ms']:>10d}ms {r['p95_latency_ms']:>10d}ms {r['total_tokens']:>10,}"
        )

    winner = sorted_models[0]
    print(f"\n🏆 Winner: {winner['model']} (Accuracy: {winner['accuracy']:.2%})")
    print(f"{'=' * 60}")


def main():
    print("🔬 Local Model Comparison — RAG Context Evaluation")
    print(f"   Questions: {len(QUESTIONS)}")
    print("   Mode: With RAG context (real use case)")

    # Check Ollama and find available models
    try:
        resp = httpx.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        available = [m["name"] for m in resp.json().get("models", [])]
    except Exception as e:
        print(f"❌ Cannot connect to Ollama: {e}")
        return

    # Filter to only available models
    models = [m for m in ALL_MODELS if m in available]
    if not models:
        print(f"❌ No target models found. Available: {available}")
        return
    print(f"   Models: {', '.join(models)}")
    skipped = [m for m in ALL_MODELS if m not in available]
    if skipped:
        print(f"   Skipped (not downloaded): {', '.join(skipped)}")

    # Override global MODELS
    global MODELS
    MODELS = models

    results = run_comparison()
    print_final_report(results)

    # Save results
    output_path = Path("eval/results/local_model_comparison_rag.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    save_data = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "models": MODELS,
        "questions_count": len(QUESTIONS),
        "mode": "rag_context",
        "results": {
            k: {kk: vv for kk, vv in v.items() if kk != "details"}
            for k, v in results.items()
        },
        "per_model_details": results,
    }
    with open(output_path, "w") as f:
        json.dump(save_data, f, indent=2, ensure_ascii=False)
    print(f"\n💾 Results saved to: {output_path}")


if __name__ == "__main__":
    main()
