# MLOps — Experiment Tracking & Model Lifecycle

## Overview

Smart Document Chatbot uses **MLflow** for experiment tracking, combined with **Prometheus + Grafana** for production monitoring. This document describes the MLOps setup.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    MLOps Stack                               │
│                                                             │
│  ┌───────────┐   ┌──────────┐   ┌──────────┐              │
│  │  MLflow   │   │Prometheus│   │ Grafana  │              │
│  │ Tracking  │   │ Metrics  │   │Dashboard │              │
│  │  Server   │   │          │   │          │              │
│  └─────┬─────┘   └────┬─────┘   └────┬─────┘              │
│        │              │              │                      │
│        ▼              ▼              ▼                      │
│  ┌─────────────────────────────────────────┐              │
│  │            Smart Document Chatbot       │              │
│  │  ┌──────────┐  ┌──────────┐  ┌───────┐ │              │
│  │  │ Java API │  │ Python   │  │ React │ │              │
│  │  │(Spring   │  │ Agent    │  │Frontend│ │              │
│  │  │ Boot)    │  │(FastAPI) │  │       │ │              │
│  │  └──────────┘  └──────────┘  └───────┘ │              │
│  └─────────────────────────────────────────┘              │
└─────────────────────────────────────────────────────────────┘
```

## MLflow Setup

### Start MLflow (Docker)

```bash
cd docker
docker compose -f docker-compose.yml -f docker-compose.mlops.yml up -d mlflow
```

MLflow UI: http://localhost:5000

### Log Experiments from Eval Pipeline

```bash
python eval/eval.py \
  --base-url http://localhost:8080/api \
  --token <jwt-token> \
  --document-id 1 \
  --mlflow \
  --mlflow-uri http://localhost:5000
```

### What Gets Logged

| Parameter | Description |
|-----------|-------------|
| `base_url` | API endpoint URL |
| `document_id` | Target document for evaluation |
| `total_questions` | Number of test questions |
| `session_id` | Unique eval session ID |

| Metric | Description |
|--------|-------------|
| `retrieval_accuracy` | % of questions where source chunks match expected keywords |
| `answer_correctness` | % of questions with correct answer |
| `hallucination_rate` | % of answers where AI answered but had no source support |
| `avg_latency_ms` | Average response latency in milliseconds |
| `p95_latency_ms` | 95th percentile latency |
| `q{i}_latency_ms` | Per-question latency (step-level) |
| `q{i}_correct` | Per-question correctness (0 or 1) |
| `q{i}_retrieval` | Per-question retrieval accuracy (0 or 1) |

## Python Agent — MLflow Tracker Module

The agent service includes `agent/mlflow_tracker.py` — a singleton tracker for logging parameters, metrics, and artifacts from the Python AI layer.

```python
from agent.mlflow_tracker import tracker

tracker.start_run(run_name="my-run")
tracker.log_params({"model": "llama3.2:3b", "temperature": 0.7})
tracker.log_metrics({"latency_ms": 1420, "confidence": 0.87})
tracker.end_run()
```

Config via environment variables:
- `MLFLOW_TRACKING_URI` — MLflow server URL (default: `http://mlflow:5000`)
- `MLFLOW_EXPERIMENT_NAME` — Experiment name (default: `smart-document-chatbot`)

## Java Backend — MLflow Tracker

The Spring Boot backend includes `MlflowTracker.java` which logs per-query parameters and metrics via REST API (fire-and-forget, non-blocking).

Logged per chat query:
- `model_name`, `temperature`, `prompt_length`
- `latency_ms`, `response_length`

## Production Monitoring (Prometheus + Grafana)

### Custom RAG Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `rag_requests_total{mode}` | Counter | Total sync/streaming requests |
| `rag_retrieval_confidence` | Histogram | Retrieval confidence distribution |
| `rag_fallbacks_total{strategy}` | Counter | Corrective/web/general-knowledge fallbacks |
| `rag_llm_latency_seconds{outcome}` | Histogram | LLM request latency |
| `rag_stream_errors_total` | Counter | Streaming failures |

### Alert Rules

| Alert | Condition |
|-------|-----------|
| BackendDown | API unavailable for 2 min |
| HighErrorRate | 5xx error rate > 5% for 5 min |
| HighResponseTime | p95 latency > 5s for 5 min |
| HighMemoryUsage | Heap usage > 85% |
| DBPoolExhaustion | Connection pool > 90% |

## Model Lifecycle

```
Develop → Evaluate → Register → Deploy → Monitor → Retrain
   │          │           │          │          │         │
   ▼          ▼           ▼          ▼          ▼         ▼
Code      eval.py     Model      Docker/    Prometheus  retrain.py
changes   + eval/     Registry   K8s        + Grafana   (auto)
            │         (quality
            │          gate)
            ▼
         Drift Detector ──→ A/B Testing
```

### Current Status

| Component | Status | Implementation |
|-----------|--------|---------------|
| Experiment Tracking (MLflow) | ✅ | `eval/eval.py` logs to MLflow, `agent/mlflow_tracker.py` |
| Per-query Metrics (MLflow) | ✅ | Java `MlflowTracker.java` logs via REST |
| Production Monitoring | ✅ | Prometheus + Grafana + Loki |
| CI/CD | ✅ | GitHub Actions (build, test, SonarCloud, Trivy) |
| Model Registry | ✅ | `agent/model_registry.py` — quality gate + version management |
| Automated Retraining | ✅ | `agent/retrain.py` — auto re-evaluate + register |
| Drift Detection | ✅ | `agent/drift_detector.py` — PSI + Z-score monitoring |
| A/B Testing | ✅ | `agent/ab_testing.py` — variant routing + metrics |

---

## Model Registry

**Module:** `agent/model_registry.py`

Local model registry backed by JSON files + MLflow. Manages model versions with quality gates.

### Quality Gate Thresholds

| Metric | Threshold | Direction |
|--------|-----------|-----------|
| `retrieval_accuracy` | ≥ 75% | Higher is better |
| `answer_correctness` | ≥ 70% | Higher is better |
| `hallucination_rate` | ≤ 20% | Lower is better |

### Usage

```python
from agent.model_registry import registry

# Register (fails if quality gate not met)
mv = registry.register_model(
    model_name="rag-retriever",
    version="v20260716.143000",
    metrics={"retrieval_accuracy": 0.85, "hallucination_rate": 0.10},
    config={"chunk_size": 512},
)

# Promote to production
registry.promote_model("rag-retriever", "v20260716.143000", "Production")

# Get current production model
prod = registry.get_model("rag-retriever", stage="Production")
```

---

## Automated Retraining

**Module:** `agent/retrain.py`

Monitors eval results, compares with previous runs, and auto-registers improved models.

### Trigger Conditions

1. Previous eval results exist for comparison
2. Improvement exceeds threshold (accuracy +2%)
3. Quality gate passes (retrieval ≥75%, correctness ≥70%, hallucination ≤20%)

### Usage

```bash
# One-shot retrain check
python -m agent.retrain \
  --base-url http://localhost:8080/api \
  --token <jwt> \
  --document-id 1

# Force retrain (skip quality gate)
python -m agent.retrain --token <jwt> --document-id 1 --force
```

---

## Drift Detection

**Module:** `agent/drift_detector.py`

Monitors incoming queries for distribution shifts using PSI (Population Stability Index) and Z-score tests.

### Metrics Monitored

| Metric | Method | Alert Threshold |
|--------|--------|-----------------|
| Confidence score | PSI | > 0.20 |
| Latency | PSI | > 0.20 |
| Query length | PSI | > 0.20 |
| Latency spike | Z-score | > 2.5σ |
| RAG strategy shift | % change | > 15% |

### Usage

```python
from agent.drift_detector import drift_detector

# Log each prediction
drift_detector.log_prediction({
    "query_length": 120,
    "confidence_score": 0.78,
    "rag_strategy": "direct",
    "latency_ms": 1420,
})

# Check for drift
report = drift_detector.check_drift()
if report["drift_detected"]:
    for alert in report["alerts"]:
        print(f"[{alert['severity']}] {alert['message']}")
```

---

## A/B Testing

**Module:** `agent/ab_testing.py`

Routes queries between model configurations and tracks per-variant performance.

### Default Experiment: `rag-config-v1`

| Variant | Description | Config |
|---------|-------------|--------|
| **Control** | Default RAG config | confidence=0.45, chunk_size=512 |
| **Variant A** | Aggressive retrieval | confidence=0.35, chunk_size=1024 |

### Usage

```python
from agent.ab_testing import ab_manager

# Assign variant (deterministic via query_id hash)
variant = ab_manager.assign_variant(query_id="q-123")
print(f"Variant: {variant.name} — {variant.config}")

# Log result
ab_manager.log_result(
    query_id="q-123",
    variant_id=variant.id,
    latency_ms=1420,
    confidence_score=0.87,
    answer_correct=True,
)

# Get experiment report
report = ab_manager.get_report()
print(f"Winner: {report['winner']}")
```
