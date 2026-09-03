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

    /**
     * AI-quality telemetry (Blueprint #18): one answer-level counter per
     * strategy with a cited flag, so citation coverage and CRAG/web-search
     * fallback rates are derivable from Prometheus.
     */
    public void recordAnswer(String strategy, boolean cited) {
        Counter.builder("chat.answers.total")
                .tag("strategy", strategy)
                .tag("cited", Boolean.toString(cited))
                .register(meterRegistry)
                .increment();
    }

    /** Counts upstream LLM failures (unexpected structure or call errors). */
    public void recordLlmError() {
        Counter.builder("chat.llm.errors").register(meterRegistry).increment();
    }

    /** Records generated-token usage per LLM response when reported. */
    public void recordTokens(long tokens) {
        io.micrometer.core.instrument.DistributionSummary
                .builder("chat.tokens")
                .publishPercentiles(0.5, 0.95)
                .register(meterRegistry)
                .record(tokens);
    }

    public void recordTokensWithCost(long promptTokens, long completionTokens, double costUsd) {
        long total = promptTokens + completionTokens;
        if (total > 0) {
            io.micrometer.core.instrument.DistributionSummary
                    .builder("chat.tokens")
                    .publishPercentiles(0.5, 0.95)
                    .register(meterRegistry)
                    .record(total);
        }
        if (costUsd > 0) {
            io.micrometer.core.instrument.DistributionSummary
                    .builder("chat.cost.usd")
                    .publishPercentiles(0.5, 0.95)
                    .register(meterRegistry)
                    .record(costUsd);
            Counter.builder("chat.cost.total")
                    .register(meterRegistry)
                    .increment(costUsd);
        }
        // also per-direction counters
        if (promptTokens > 0) {
            Counter.builder("chat.tokens.total").tag("direction", "prompt").register(meterRegistry).increment(promptTokens);
        }
        if (completionTokens > 0) {
            Counter.builder("chat.tokens.total").tag("direction", "completion").register(meterRegistry).increment(completionTokens);
        }
    }
}