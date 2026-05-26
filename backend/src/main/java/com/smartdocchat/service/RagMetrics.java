package com.smartdocchat.service;

import io.micrometer.core.instrument.Counter;
import io.micrometer.core.instrument.DistributionSummary;
import io.micrometer.core.instrument.MeterRegistry;
import io.micrometer.core.instrument.Timer;
import org.springframework.stereotype.Component;

import java.time.Duration;

@Component
public class RagMetrics {
    private final MeterRegistry registry;

    public RagMetrics(MeterRegistry registry) {
        this.registry = registry;
    }

    public void request(String mode) {
        Counter.builder("rag.requests").tag("mode", mode).register(registry).increment();
    }

    public void confidence(double score) {
        DistributionSummary.builder("rag.retrieval.confidence")
                .baseUnit("score").register(registry).record(score);
    }

    public void fallback(String strategy) {
        Counter.builder("rag.fallbacks").tag("strategy", strategy).register(registry).increment();
    }

    public void llmLatency(long millis, String outcome) {
        Timer.builder("rag.llm.latency").tag("outcome", outcome).register(registry)
                .record(Duration.ofMillis(millis));
    }

    public void streamError() {
        Counter.builder("rag.stream.errors").register(registry).increment();
    }
}
