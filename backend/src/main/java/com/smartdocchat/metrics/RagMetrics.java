package com.smartdocchat.metrics;

import io.micrometer.core.instrument.Counter;
import io.micrometer.core.instrument.MeterRegistry;
import io.micrometer.core.instrument.Timer;
import org.springframework.stereotype.Component;

import java.time.Duration;

/**
 * AI-quality and request telemetry for the classic chat path.
 * Metrics are scraped by Prometheus via /actuator/prometheus (token-guarded).
 */
@Component
public class RagMetrics {

    private final MeterRegistry meterRegistry;

    public RagMetrics(MeterRegistry meterRegistry) {
        this.meterRegistry = meterRegistry;
    }

    public void recordRequest(String strategy, String confidence) {
        Counter.builder("chat.requests.total")
                .tag("strategy", strategy)
                .tag("confidence", confidence)
                .register(meterRegistry)
                .increment();
    }

    public void recordAbstention() {
        Counter.builder("chat.abstentions").register(meterRegistry).increment();
    }

    public void recordInjectionBlocked() {
        Counter.builder("chat.injection.blocked").register(meterRegistry).increment();
    }

    public void recordLatency(long durationMs) {
        Timer.builder("chat.latency")
                .publishPercentiles(0.5, 0.95, 0.99)
                .sla(Duration.ofMillis(2000), Duration.ofMillis(5000), Duration.ofMillis(10000))
                .register(meterRegistry)
                .record(Duration.ofMillis(durationMs));
    }
}