package com.smartdocchat.util;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.stereotype.Component;

@Component
@ConfigurationProperties(prefix = "ollama")
@Data
public class OllamaConfig {
    private String baseUrl = "http://localhost:11434";
    private String chatModel = "deepseek-r1:1.5b";
    private String embeddingModel = "nomic-embed-text";
    private double temperature = 0.3;

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
