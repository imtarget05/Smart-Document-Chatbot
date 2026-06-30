package com.smartdocchat.util;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.stereotype.Component;

/**
 * Enterprise-grade LLM infrastructure configuration.
 * Decouples the application code from specific LLM providers (e.g. Ollama).
 */
@Component
@ConfigurationProperties(prefix = "llm")
@Data
public class LlmConfig {
    private String baseUrl = "http://localhost:8001";
    private String chatModel = "llama3.2:3b";
    private String embeddingModel = "nomic-embed-text";
    private double temperature = 0.3;
    
    // Retry configurations
    private int maxAttempts = 3;
    private long retryBackoffMs = 250;

    public String getChatUrl() {
        return stripTrailingSlash(baseUrl) + "/api/chat";
    }

    public String getEmbeddingUrl() {
        return stripTrailingSlash(baseUrl) + "/api/embeddings";
    }

    private String stripTrailingSlash(String url) {
        return url.endsWith("/") ? url.substring(0, url.length() - 1) : url;
    }
}
