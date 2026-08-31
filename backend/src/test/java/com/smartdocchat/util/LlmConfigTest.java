package com.smartdocchat.util;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

class LlmConfigTest {

    @Test
    void buildsChatAndEmbeddingUrlsStrippingTrailingSlash() {
        LlmConfig config = new LlmConfig();
        config.setBaseUrl("http://localhost:8001/");

        assertEquals("http://localhost:8001/api/chat", config.getChatUrl());
        assertEquals("http://localhost:8001/api/embeddings", config.getEmbeddingUrl());
        assertEquals("http://localhost:8001", config.getBaseUrl().replaceFirst("/$", ""));
    }

    @Test
    void defaultsAreSensible() {
        LlmConfig config = new LlmConfig();
        assertTrue(config.getChatUrl().endsWith("/api/chat"));
        assertTrue(config.getMaxAttempts() >= 1);
        assertTrue(config.getRetryBackoffMs() > 0);
        assertEquals(0.3, config.getTemperature());
        assertEquals(0.95, config.getTopP());
    }
}