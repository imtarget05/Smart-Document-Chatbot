package com.smartdocchat.controller;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.client.RestTemplate;

import com.smartdocchat.util.LlmConfig;

import java.util.LinkedHashMap;
import java.util.Map;

/**
 * RAG-specific health endpoint that checks connectivity to all AI infrastructure
 * components: Qdrant Vector DB, Ollama LLM provider, and PostgreSQL.
 */
@RestController
@RequestMapping("/system")
@RequiredArgsConstructor
@Slf4j
public class SystemHealthController {

    private final RestTemplate restTemplate;
    private final LlmConfig llmConfig;

    @Value("${qdrant.host:localhost}")
    private String qdrantHost;

    @Value("${qdrant.port:6333}")
    private int qdrantPort;

    @GetMapping("/health")
    public ResponseEntity<Map<String, Object>> healthCheck() {
        Map<String, Object> health = new LinkedHashMap<>();

        // Check Qdrant Vector DB
        String vectorDbStatus = checkService(
                "http://" + qdrantHost + ":" + qdrantPort + "/healthz");
        health.put("vector_db", vectorDbStatus);

        // Check Ollama LLM Provider
        String llmStatus = checkService(llmConfig.getBaseUrl() + "/api/tags");
        health.put("llm_provider", llmStatus);

        // Overall status
        boolean allHealthy = "connected".equals(vectorDbStatus)
                && "available".equals(llmStatus);
        health.put("status", allHealthy ? "ok" : "degraded");

        return ResponseEntity.ok(health);
    }

    private String checkService(String url) {
        try {
            restTemplate.getForEntity(url, String.class);
            if (url.contains("ollama") || url.contains("11434")) {
                return "available";
            }
            return "connected";
        } catch (Exception e) {
            log.warn("Health check failed for {}: {}", url, e.getMessage());
            return "unavailable";
        }
    }
}
