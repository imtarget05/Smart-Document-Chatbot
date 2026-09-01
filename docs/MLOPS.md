# MLOps Guide — Smart Document Chatbot

This document covers how to track experiments, compare runs, and manage model deployments using the built-in MLOps capabilities.

## Table of Contents

1. [Overview](#overview)
2. [Quick Start](#quick-start)
3. [Running Experiments](#running-experiments)
4. [Comparing Runs](#comparing-runs)
5. [Model Registry](#model-registry)
6. [Hugging Face Integration](#hugging-face-integration)
7. [Retrieval Tuning](#retrieval-tuning)
8. [Configuration](#configuration)

---

## Overview

The MLOps module provides:

| Feature | Module | Description |
|---------|--------|-------------|
| Experiment Tracking | `agent.mlops.tracker` | Log metrics, params, artifacts to MLflow |
| Model Registry | `agent.mlops.model_registry` | Version and promote models (Staging → Production) |
| Local Inference | `agent.mlops.hf_provider` | Hugging Face embeddings and chat |
| Retrieval Tuning | `agent.mlops.retrieval_tuner` | Grid search over chunk/top-k/embeddings |

---

## Quick Start

```python
from agent.mlops import log_eval_run, register_model, get_model

# Log an evaluation run
run_id = log_eval_run(
    metrics={"retrieval_accuracy": 0.85, "faithfulness": 0.78},
    params={"chunk_size": 512, "top_k": 5},
    run_name="eval-2026-09-01"
)

# Register the model if it passes quality gate
model = register_model(
    name="rag-retriever",
    version="1.2.0",
    metrics={"retrieval_accuracy": 0.85, "faithfulness": 0.78, "hallucination_rate": 0.12},
    config={"chunk_size": 512, "embedding_model": "all-MiniLM-L6-v2"},
    mlflow_run_id=run_id
)

# Get the current production model
prod_model = get_model("rag-retriever", stage="Production")
print(f"Production: {prod_model.version} | accuracy={prod_model.metrics['retrieval_accuracy']}")
```

---

## Running Experiments

### Log an Evaluation Run

```python
from agent.mlops.tracker import log_eval_run

run_id = log_eval_run(
    metrics={
        "retrieval_accuracy": 0.88,
        "answer_correctness": 0.82,
        "faithfulness": 0.79,
        "hallucination_rate": 0.11,
    },
    params={
        "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
        "chunk_size": 512,
        "chunk_overlap": 64,
        "top_k": 5,
        "reranker": "cross-encoder/ms-marco-MiniLM-L-6-v2",
    },
    artifacts={"eval_report": "./outputs/eval_report.json"},
    run_name="baseline-eval"
)
```

### Log a Retrieval Experiment

```python
from agent.mlops.tracker import log_retrieval_experiment

run_id = log_retrieval_experiment(
    chunk_size=1024,
    top_k=10,
    embedding_model="sentence-transformers/all-mpnet-base-v2",
    metrics={"retrieval_accuracy": 0.91, "avg_latency_ms": 45.2},
    additional_params={"hybrid_search": True, "bm25_weight": 0.3}
)
```

### Direct MLflow Access

```python
from agent.mlops.tracker import _get_client, compare_runs, get_best_run

# Get the best run by retrieval accuracy
best = get_best_run("retrieval_accuracy", mode="max")
print(f"Best run: {best['run_id']} | accuracy={best['metric_value']}")

# Compare specific runs
comparison = compare_runs(["run_id_1", "run_id_2", "run_id_3"])
for metric, values in comparison["comparison"].items():
    print(f"{metric}: {values}")
```

---

## Comparing Runs

### Programmatic Comparison

```python
from agent.mlops.tracker import compare_runs

result = compare_runs(["abc123", "def456", "ghi789"])

# View run details
for run_id, data in result["runs"].items():
    print(f"{data['run_name']}: {data['metrics']}")

# View metric comparison table
for metric, values in result["comparison"].items():
    print(f"{metric}:")
    for run_id, value in values.items():
        print(f"  {run_id}: {value}")
```

### Using MLflow UI

```bash
# Start the MLflow UI to browse experiments
mlflow ui --backend-store-uri mlruns/ --port 5000
```

Then open http://localhost:5000 to view all runs, compare metrics, and inspect artifacts.

---

## Model Registry

The model registry manages model lifecycle: **Staging → Production → Archived**.

### Register a Model

```python
from agent.mlops.model_registry import register_model

model = register_model(
    name="rag-retriever",
    version="2.0.0",
    metrics={
        "retrieval_accuracy": 0.90,
        "answer_correctness": 0.85,
        "hallucination_rate": 0.08,
    },
    config={"chunk_size": 512, "top_k": 5},
    mlflow_run_id="run_abc123",
    description="New embedding model with hybrid search"
)
```

If metrics don't pass the quality gate, registration returns `None`. Use `force=True` to bypass.

### Promote to Production

```python
from agent.mlops.model_registry import promote_model

# Promote to staging
promote_model("rag-retriever", "2.0.0", "Staging")

# Promote to production (auto-archives previous prod)
promote_model("rag-retriever", "2.0.0", "Production")
```

### Query Models

```python
from agent.mlops.model_registry import get_model, list_versions

# Get production model
prod = get_model("rag-retriever", stage="Production")

# List all versions
all_versions = list_versions("rag-retriever")
for v in all_versions:
    print(f"v{v.version} | stage={v.stage} | accuracy={v.metrics.get('retrieval_accuracy', 'N/A')}")
```

### Quality Gates

Default thresholds for automatic registration:

| Metric | Threshold | Direction |
|--------|-----------|-----------|
| retrieval_accuracy | 0.75 | ≥ |
| answer_correctness | 0.70 | ≥ |
| faithfulness | 0.70 | ≥ |
| hallucination_rate | 0.20 | ≤ |

---

## Hugging Face Integration

### Setup

```bash
pip install transformers torch
```

### Basic Usage

```python
from agent.mlops.hf_provider import HuggingFaceProvider

provider = HuggingFaceProvider()

# Check status
print(provider.get_model_info())
# {
#   "embedding_model": {"name": "sentence-transformers/all-MiniLM-L6-v2", "loaded": true, "dim": 384},
#   "chat_model": {"name": "microsoft/DialoGPT-medium", "loaded": true},
#   "device": "cpu"
# }

# Generate embeddings
embeddings = provider.embed(["Hello world", "RAG pipeline"])
print(len(embeddings), len(embeddings[0]))  # 2, 384

# Generate text
response = provider.generate("What is retrieval augmented generation?", max_tokens=100)
print(response)
```

### Custom Models

```python
from agent.mlops.hf_provider import HuggingFaceProvider

provider = HuggingFaceProvider(
    embedding_model="sentence-transformers/all-mpnet-base-v2",
    chat_model="microsoft/DialoGPT-large",
    device="cuda"  # Use GPU if available
)
```

### Lazy Loading

```python
# Don't load models on init (useful for testing)
provider = HuggingFaceProvider(load_on_init=False)
# Load manually when needed
provider._load_models()
```

### Fallback Mode

If `transformers` is not installed, the provider returns zero vectors and fallback text — useful for development environments.

---

## Retrieval Tuning

### Grid Search

```python
from agent.mlops.retrieval_tuner import RetrievalTuner

tuner = RetrievalTuner()
results = tuner.run_experiment(
    questions=[
        "What is the refund policy?",
        "How do I reset my password?",
        "What are the system requirements?",
    ],
    chunk_sizes=[256, 512, 1024],
    top_ks=[3, 5, 10],
    embedding_models=[
        "sentence-transformers/all-MiniLM-L6-v2",
        "sentence-transformers/all-mpnet-base-v2",
    ],
)

# Get the best configuration
best = tuner.get_best_config(metric="retrieval_accuracy")
print(f"Best: chunk_size={best.chunk_size}, top_k={best.top_k}")
print(f"  Model: {best.embedding_model}")
print(f"  Metrics: {best.metrics}")
```

### Compare Embeddings

```python
tuner = RetrievalTuner()
comparison = tuner.compare_embeddings(
    texts=["sample document text"],
    models=[
        "sentence-transformers/all-MiniLM-L6-v2",
        "sentence-transformers/all-mpnet-base-v2",
        "BAAI/bge-small-en-v1.5",
    ],
)

for model, info in comparison.items():
    print(f"{model}: dim={info.get('dim')}, latency={info.get('latency_ms', 'N/A')}ms")
```

### Reranker Tuning

```python
tuner = RetrievalTuner()
results = tuner.tune_reranker(
    questions=["test question"],
    reranker_models=[
        "cross-encoder/ms-marco-MiniLM-L-6-v2",
        "cross-encoder/ms-marco-TinyBERT-L-2-v2",
    ],
)

for model, info in results.items():
    print(f"{model}: improvement={info.get('improvement', 'N/A')}")
```

### Results Summary

```python
summary = tuner.get_results_summary()
print(f"Total experiments: {summary['count']}")
print(f"Best retrieval_accuracy: {summary['best_by_metric']['retrieval_accuracy']:.3f}")
print(f"Avg answer_correctness: {summary['avg_by_metric']['answer_correctness']:.3f}")
```

---

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MLFLOW_TRACKING_URI` | `mlruns/` | MLflow backend store URI |
| `MLFLOW_EXPERIMENT_NAME` | `smart-doc-chatbot` | Experiment name |
| `MODEL_REGISTRY_DIR` | `model_registry/` | Local registry storage |
| `HF_EMBEDDING_MODEL` | `sentence-transformers/all-MiniLM-L6-v2` | Default HF embedding model |
| `HF_CHAT_MODEL` | `microsoft/DialoGPT-medium` | Default HF chat model |

### Running with Docker

```yaml
# docker-compose.yml snippet
services:
  agent:
    environment:
      - MLFLOW_TRACKING_URI=http://mlflow:5000
      - MODEL_REGISTRY_DIR=/data/model_registry
    volumes:
      - mlruns:/data/mlruns

  mlflow:
    image: ghcr.io/mlflow/mlflow:v2.15.0
    ports:
      - "5000:5000"
    volumes:
      - mlruns:/mlruns
```

### MLflow Server

```bash
# Start MLflow tracking server
mlflow server \
  --backend-store-uri sqlite:///mlflow.db \
  --default-artifact-root ./mlruns \
  --host 0.0.0.0 \
  --port 5000
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    MLOps Module                          │
├─────────────┬──────────────┬────────────┬───────────────┤
│  tracker    │ model_registry│ hf_provider│retrieval_tuner│
│  (MLflow)   │  (JSON/MLflow)│(Transformers)│(Grid Search) │
└─────────────┴──────────────┴────────────┴───────────────┘
        │             │            │             │
   ┌────┴────┐   ┌────┴────┐  ┌───┴────┐  ┌────┴────┐
   │ MLflow  │   │ Registry│  │   HF   │  │ MLflow  │
   │ Server  │   │  JSON   │  │ Models │  │  Logs   │
   └─────────┘   └─────────┘  └────────┘  └─────────┘
```

---

## Testing

```bash
# Run MLOps tests
cd agent
pytest tests/test_mlops.py -v

# Run with coverage
pytest tests/test_mlops.py --cov=agent.mlops --cov-report=term-missing
```
