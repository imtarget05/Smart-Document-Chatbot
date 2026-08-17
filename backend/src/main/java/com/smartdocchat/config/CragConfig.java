package com.smartdocchat.config;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.stereotype.Component;

/**
 * Corrective RAG (CRAG) configuration for the classic Chat endpoints.
 *
 * Mirrors the agent-service CRAG loop: if the top retrieval score is below
 * {@code confidenceThreshold}, the query is reformulated (and re-retrieved);
 * if it is still low, the system falls back to web search or general knowledge.
 */
@Component
@ConfigurationProperties(prefix = "crag")
@Data
public class CragConfig {
    private double confidenceThreshold = 0.6;

    private int topK = 3;

    private int maxReformulations = 2;

    /** Allow automatic web-search fallback on low confidence. */
    private boolean webSearchEnabled = false;
}
