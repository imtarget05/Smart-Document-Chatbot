# Performance Benchmark Plan

Performance claims require measured results; none are asserted by the repository alone.

## Workloads

Run at least these scenarios against a fixed test corpus and model configuration:

| Scenario | Measurement |
| --- | --- |
| Upload and index 10/100 page PDFs | end-to-end ingestion latency, chunk count, failures |
| Single-document chat | p50/p95/p99 first-token and completion latency |
| Five-document synthesis | retrieval latency, LLM tokens, p95 response latency |
| Low-confidence question | corrective/web fallback rate and latency |
| Concurrent streams (10/50 clients) | error rate, CPU/memory, DB pool use |

## Quality Evaluation

Maintain a versioned question set with expected source passages. Record retrieval recall@k, citation correctness, grounded-answer rate and fallback rate. Compare changes to chunking, embeddings, prompts and confidence thresholds on the same set.

## Tools

Use `k6` or Gatling for API/SSE load, Prometheus/Grafana for latency and resource metrics, and MLflow for experiment comparisons. Store corpus version, model name, threshold and environment alongside every reported result.
