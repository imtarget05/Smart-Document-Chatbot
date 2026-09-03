package com.smartdocchat.service;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.smartdocchat.config.TavilyConfig;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;

/**
 * Optional Tavily web-search used by the CRAG fallback.
 * When the API key is not configured ({@link TavilyConfig#isConfigured()} is
 * false) {@link #search} returns an empty Optional and the pipeline degrades
 * to the general-knowledge fallback.
 */
@Service
@RequiredArgsConstructor
@Slf4j
public class WebSearchService {

    private static final int DEFAULT_MAX_RESULTS = 3;

    private final TavilyConfig tavilyConfig;
    private final RestTemplate restTemplate;
    private final ObjectMapper objectMapper = new ObjectMapper();

    public boolean isConfigured() {
        return tavilyConfig.isConfigured();
    }

    public Optional<List<String>> search(String query) {
        return search(query, DEFAULT_MAX_RESULTS);
    }

    public Optional<List<String>> search(String query, int maxResults) {
        if (!isConfigured()) {
            return Optional.empty();
        }

        try {
            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.APPLICATION_JSON);

            Map<String, Object> body = new HashMap<>();
            body.put("api_key", tavilyConfig.getApiKey());
            body.put("query", query);
            body.put("max_results", maxResults);
            body.put("search_depth", "advanced");

            ResponseEntity<JsonNode> response = restTemplate.postForEntity(
                    tavilyConfig.getUrl(),
                    new HttpEntity<>(body, headers),
                    JsonNode.class);

            if (response == null || !response.getStatusCode().is2xxSuccessful() || response.getBody() == null) {
                log.warn("Tavily search returned {}", response == null ? "null" : response.getStatusCode());
                return Optional.empty();
            }

            List<String> snippets = new ArrayList<>();
            for (JsonNode result : response.getBody().path("results")) {
                String content = result.path("content").asText("");
                if (content.length() >= 20) {
                    snippets.add(content);
                }
            }
            return snippets.isEmpty() ? Optional.empty() : Optional.of(snippets);
        } catch (Exception e) {
            log.warn("Tavily search error: {}", e.getMessage());
            return Optional.empty();
        }
    }
}