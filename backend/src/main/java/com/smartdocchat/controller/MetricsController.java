package com.smartdocchat.controller;

import io.micrometer.core.instrument.MeterRegistry;
import io.micrometer.core.instrument.Timer;
import io.micrometer.core.instrument.Counter;
import io.micrometer.core.instrument.search.Search;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.LinkedHashMap;
import java.util.Map;
import java.util.concurrent.TimeUnit;

/**
 * Human-readable RAG metrics endpoint.
 * Aggregates Micrometer counters and timers into a concise JSON summary.
 */
@RestController
@RequestMapping("/system")
@RequiredArgsConstructor
public class MetricsController {

    private final MeterRegistry registry;

    @GetMapping("/metrics")
    public ResponseEntity<Map<String, Object>> getMetrics() {
        Map<String, Object> metrics = new LinkedHashMap<>();

        // Total RAG requests (sync + stream)
        double totalRequests = sumCounters("rag.requests");
        metrics.put("total_requests", (long) totalRequests);

        // Average LLM latency
        Timer llmTimer = registry.find("rag.llm.latency").timer();
        if (llmTimer != null && llmTimer.count() > 0) {
            metrics.put("average_latency_ms", Math.round(llmTimer.mean(TimeUnit.MILLISECONDS)));
            
            double p95 = 0.0;
            io.micrometer.core.instrument.distribution.ValueAtPercentile[] percentiles = llmTimer.takeSnapshot().percentileValues();
            for (io.micrometer.core.instrument.distribution.ValueAtPercentile vp : percentiles) {
                if (Math.abs(vp.percentile() - 0.95) < 0.01) {
                    p95 = vp.value(TimeUnit.MILLISECONDS);
                    break;
                }
            }
            metrics.put("p95_latency_ms", Math.round(p95));
        } else {
            metrics.put("average_latency_ms", 0);
            metrics.put("p95_latency_ms", 0);
        }

        // Fallback counts
        double correctiveFallbacks = countByTag("rag.fallbacks", "strategy", "corrective_retrieval");
        double webSearchFallbacks = countByTag("rag.fallbacks", "strategy", "web_search");
        double generalFallbacks = countByTag("rag.fallbacks", "strategy", "general_knowledge");
        double totalFallbacks = correctiveFallbacks + webSearchFallbacks + generalFallbacks;

        metrics.put("fallback_count", (long) totalFallbacks);
        metrics.put("fallback_rate", totalRequests > 0
                ? Math.round(totalFallbacks / totalRequests * 10000.0) / 10000.0 : 0.0);

        // Stream errors
        double streamErrors = sumCounters("rag.stream.errors");
        metrics.put("stream_errors", (long) streamErrors);
        metrics.put("error_rate", totalRequests > 0
                ? Math.round(streamErrors / totalRequests * 10000.0) / 10000.0 : 0.0);

        // Breakdown
        Map<String, Long> breakdown = new LinkedHashMap<>();
        breakdown.put("corrective_retrieval", (long) correctiveFallbacks);
        breakdown.put("web_search", (long) webSearchFallbacks);
        breakdown.put("general_knowledge", (long) generalFallbacks);
        metrics.put("fallback_breakdown", breakdown);

        return ResponseEntity.ok(metrics);
    }

    private double sumCounters(String name) {
        double total = 0.0;
        for (Counter counter : Search.in(registry).name(name).counters()) {
            total += counter.count();
        }
        return total;
    }

    private double countByTag(String name, String tagKey, String tagValue) {
        Counter counter = registry.find(name).tag(tagKey, tagValue).counter();
        return counter != null ? counter.count() : 0.0;
    }
}
