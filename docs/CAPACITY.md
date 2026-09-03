# Capacity Planning

## Current (free tier)

- Backend: 1 instance, 2G/1.5 CPU (docker-compose limits), Render free shared CPU
- Agent: 1 instance
- DB: Neon serverless autoscale, Qdrant Cloud free tier
- Load test baseline: `scripts/load_test.py` 50 users/60s, P95 5s threshold, success 95% (`load-test.yml` nightly)

## Paid scaling

Render:
```yaml
scaling:
  minInstances: 2
  maxInstances: 5
  targetCPUPercent: 70
  targetMemoryPercent: 80
```

K8s HPA (future):
```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata: {name: smart-doc-backend}
spec:
  minReplicas: 2
  maxReplicas: 10
  metrics:
    - type: Resource
      resource: {name: cpu, target: {type: Utilization, averageUtilization: 70}}
```

## Forecast

- 100 RPS needs ~3 backend replicas (p95 <2s) per load test.
- Qdrant hybrid search is CPU-bound (embeddings); scale Qdrant separately.
- Cost: LLM $0.0003/1k tokens, ~$0.01 per 30-token answer.

Run `make load-test` monthly and compare to baseline in `eval/results/`.
