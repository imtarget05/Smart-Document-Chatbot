package com.smartdocchat.metrics;

import io.micrometer.core.instrument.MeterRegistry;
import io.micrometer.core.instrument.simple.SimpleMeterRegistry;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;

class RagMetricsTest {

    private MeterRegistry registry = new SimpleMeterRegistry();
    private RagMetrics metrics = new RagMetrics(registry);

    @Test
    void recordRequestIncrementsCounterWithTags() {
        metrics.recordRequest("direct", "0.8");
        metrics.recordRequest("direct", "0.8");
        metrics.recordRequest("web_search", "0.1");

        assertEquals(2, registry.counter("chat.requests.total", "strategy", "direct", "confidence", "0.8").count());
        assertEquals(1, registry.counter("chat.requests.total", "strategy", "web_search", "confidence", "0.1").count());
    }

    @Test
    void recordAbstentionAndInjectionBlockedIncrementCounters() {
        metrics.recordAbstention();
        metrics.recordAbstention();
        metrics.recordInjectionBlocked();

        assertEquals(2, registry.counter("chat.abstentions").count());
        assertEquals(1, registry.counter("chat.injection.blocked").count());
    }

    @Test
    void recordLatencyRecordsTimer() {
        metrics.recordLatency(1500);
        assertEquals(1, registry.timer("chat.latency").count());
    }
}