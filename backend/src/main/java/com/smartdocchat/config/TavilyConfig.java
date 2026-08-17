package com.smartdocchat.config;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.stereotype.Component;

/**
 * Tavily web search configuration. Web search is disabled when the API key
 * is empty, so the CRAG fallback degrades gracefully to general knowledge.
 */
@Component
@ConfigurationProperties(prefix = "tavily")
@Data
public class TavilyConfig {
    private String apiKey = "";
    private String url = "https://api.tavily.com/search";

    public boolean isConfigured() {
        return apiKey != null && !apiKey.isBlank();
    }
}
