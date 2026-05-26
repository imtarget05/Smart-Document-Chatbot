# Observability Runbook

## Signals

Spring Actuator exports standard HTTP/JVM/database metrics plus RAG metrics:

| Metric | Meaning |
| --- | --- |
| `rag_requests_total{mode}` | Sync or streaming question count |
| `rag_retrieval_confidence` | Retrieval confidence distribution |
| `rag_fallbacks_total{strategy}` | Corrective retrieval, web search or general-knowledge fallback count |
| `rag_llm_latency_seconds{outcome}` | LLM request latency and failure state |
| `rag_stream_errors_total` | Streaming failures |

Logs are JSON and include `requestId`; clients can supply or record the returned `X-Request-Id`. Micrometer tracing exports OTLP spans when `OTEL_EXPORTER_OTLP_TRACES_ENDPOINT` targets a collector.

## Local Monitoring

Set the same development internal token in Prometheus configuration and backend, then run:

```bash
docker compose -f docker/docker-compose.yml -f docker/docker-compose.monitoring.yml up -d
```

For production, do not use the committed local Prometheus credential. Supply the token through a secret-backed Prometheus configuration and set:

```bash
JWT_SECRET=<base64-32-byte-secret>
INTERNAL_SERVICE_TOKEN=<random-service-token>
OTEL_EXPORTER_OTLP_TRACES_ENDPOINT=http://otel-collector:4318/v1/traces
```

## Alerts and Service Levels

Start with these review thresholds and tune after collecting traffic:

| Signal | Alert threshold |
| --- | --- |
| API availability | less than 99.5% over 30 minutes |
| Chat p95 latency | above 10 seconds for 15 minutes |
| LLM failure ratio | above 5% for 10 minutes |
| Corrective/general fallback ratio | above 30% for 30 minutes |

The fallback ratio is a retrieval-quality warning, not merely an infrastructure incident.
