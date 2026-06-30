package com.smartdocchat.util;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.stereotype.Component;

@Component
@ConfigurationProperties(prefix = "qdrant")
@Data
public class QdrantConfig {
    private String host;
    private int port;
    private boolean useHttps = false;
    private String collectionName;
    private String apiKey;

    /**
     * Returns the full base URL for Qdrant REST API.
     * Supports both local HTTP (port 6333) and Qdrant Cloud HTTPS.
     */
    public String getBaseUrl() {
        String scheme = useHttps ? "https" : "http";
        return scheme + "://" + host + ":" + port;
    }
}
