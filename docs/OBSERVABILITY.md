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

## Gaps (current limitations)

- **Distributed tracing**: OTel SDK/Jaeger/Zipkin chưa được tích hợp. Hiện tại observability dựa trên: correlation-id trong structured log (RequestIdFilter), Prometheus metrics cho RAG (chat.requests.total, chat.abstraction, chat.injection.blocked, chat.latency) qua `/actuator/prometheus`, và Maven test coverage (JaCoCo). Nếu triển khai multi-service (backend + agent service + LLM router riêng), cần thêm OpenTelemetry SDK để trace propagation giữa services.
- **Evaluation CI**: evaluation chỉ validation-only trong CI (kiểm tra cấu trúc question set). Evaluation thực tế (retrieval_accuracy, answer_correctness) cần backend live + JWT + document đã upload → không thể chạy trong CI hiện tại. Xem [`docs/eval_state.md`](eval_state.md).
- **Golden reference answer**: không có dataset câu hỏi + golden reference answer semantic. Evaluation hiện tại chỉ đo lexical coverage, không đo semantic correctness chính xác.

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

## Alerts and Service Levels (SLO: 99.5% availability, p95 <10s)

SLOs codified in `docker/monitoring/alert-rules.yml`:

| Signal | SLO | Alert | Burn |
| --- | --- | --- | --- |
| API availability | 99.5% over 30m | SloBurnSlow (warning) | 1x |
| API availability fast burn | 99.5% over 5m *2 | SloBurnFast (critical) | 2x |
| Chat p95 latency | <10s for 15m | SloLatencyP95 | - |
| LLM failure ratio | <5% for 10m | HighErrorRate (>5%) | - |
| Circuit breaker OPEN | 0 open | CircuitBreakerOpen | - |
| Cost rate | < $0.05/min | HighCostRate | - |
| Corrective/general fallback ratio | <30% for 30m | (review threshold) | - |

Burn rate formula: `(1 - availability) > (1 - 0.995)*burn`. Error budget = 0.5% * window.

The fallback ratio is a retrieval-quality warning, not merely an infrastructure incident.

Distributed tracing now active via `X-Request-Id` + `X-Langfuse-Trace-Id` propagation (Phase1). See `backend/src/main/java/com/smartdocchat/config/RequestIdFilter.java` and `agent/main.py:tracing_correlation`.
