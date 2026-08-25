package com.smartdocchat.metrics;

import io.micrometer.core.instrument.simple.SimpleMeterRegistry;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;

/**
 * Blueprint #18 — AI-quality telemetry must be exposed as Prometheus metrics
 * with derivable citation-coverage and LLM-error rates.
 */
class RagMetricsTest {

    private SimpleMeterRegistry registry;
    private RagMetrics ragMetrics;

    @BeforeEach
    void setUp() {
        registry = new SimpleMeterRegistry();
        ragMetrics = new RagMetrics(registry);
    }

    @Test
    void answerCounterTracksStrategyAndCitationFlag() {
        ragMetrics.recordAnswer("direct", true);
        ragMetrics.recordAnswer("direct", true);
        ragMetrics.recordAnswer("web_search", false);

        assertEquals(2.0, registry.get("chat.answers.total")
                .tag("strategy", "direct").tag("cited", "true").counter().count());
        assertEquals(1.0, registry.get("chat.answers.total")
                .tag("strategy", "web_search").tag("cited", "false").counter().count());
    }

    @Test
    void llmErrorsAndTokensAreRecorded() {
        ragMetrics.recordLlmError();
        ragMetrics.recordLlmError();
        ragMetrics.recordTokens(180);
        ragMetrics.recordTokens(220);

        assertEquals(2.0, registry.get("chat.llm.errors").counter().count());
        assertEquals(400.0, registry.get("chat.tokens").summary().totalAmount());
    }

    @Test
    void existingQualityCountersStillWork() {
        ragMetrics.recordRequest("direct", "high");
        ragMetrics.recordAbstention();
        ragMetrics.recordInjectionBlocked();
        ragMetrics.recordLatency(1500);

        assertEquals(1.0, registry.get("chat.requests.total").counter().count());
        assertEquals(1.0, registry.get("chat.abstentions").counter().count());
        assertEquals(1.0, registry.get("chat.injection.blocked").counter().count());
        assertEquals(1, registry.get("chat.latency").timer().count());
    }
}