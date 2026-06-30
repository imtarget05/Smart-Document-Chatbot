package com.smartdocchat.service;

import com.smartdocchat.util.LlmConfig;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.slf4j.MDC;
import org.springframework.http.*;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;

import java.util.*;
import java.util.concurrent.CompletableFuture;

/**
 * MlflowTracker — Single Responsibility: fire-and-forget logging to MLflow.
 * All methods are non-blocking (async) so they never impact RAG latency.
 */
@Service
@RequiredArgsConstructor
@Slf4j
public class MlflowTracker {

    private final LlmConfig llmConfig;
    private final RestTemplate restTemplate;

    private static final String MLFLOW_URL = "http://mlflow:5000/api/2.0/mlflow";

    // -----------------------------------------------------------------------
    // Public API
    // -----------------------------------------------------------------------

    /**
     * Asynchronously log a completed RAG chat exchange to MLflow.
     */
    public void logChatExchange(String userMessage, String aiResponse, long latencyMs) {
        CompletableFuture.runAsync(() -> {
            try {
                HttpHeaders headers = new HttpHeaders();
                headers.setContentType(MediaType.APPLICATION_JSON);

                Map<String, Object> runBody = new HashMap<>();
                runBody.put("experiment_id", "0");
                runBody.put("run_name", "RAG_ChatQuery_" + UUID.randomUUID().toString().substring(0, 8));

                List<Map<String, String>> tags = new ArrayList<>();
                tags.add(Map.of("key", "user_query",
                        "value", userMessage.substring(0, Math.min(userMessage.length(), 250))));
                tags.add(Map.of("key", "llm_model", "value", llmConfig.getChatModel()));
                runBody.put("tags", tags);

                HttpEntity<Map<String, Object>> entity = new HttpEntity<>(runBody, headers);
                ResponseEntity<Map> response = restTemplate.exchange(
                        MLFLOW_URL + "/runs/create",
                        HttpMethod.POST,
                        entity,
                        Map.class
                );

                if (response.getStatusCode().is2xxSuccessful() && response.getBody() != null) {
                    Map<String, Object> run = (Map<String, Object>) response.getBody().get("run");
                    if (run != null) {
                        Map<String, Object> info = (Map<String, Object>) run.get("info");
                        if (info != null) {
                            String runId = (String) info.get("run_id");
                            logParameter(runId, "model_name", llmConfig.getChatModel());
                            logParameter(runId, "temperature", String.valueOf(llmConfig.getTemperature()));
                            logParameter(runId, "prompt_length", String.valueOf(userMessage.length()));
                            logMetric(runId, "latency_ms", (double) latencyMs);
                            logMetric(runId, "response_length", (double) aiResponse.length());
                            log.info("MLflow Tracking: Logged chat query execution under run ID: {}", runId);
                        }
                    }
                }
            } catch (Exception e) {
                log.debug("MLflow server not reachable or failed to log metrics: {}", e.getMessage());
            }
        });
    }

    /**
     * Log a structured RAG request summary using SLF4J MDC for correlation.
     */
    public void logStructuredRequest(String userMessage, int retrievedDocs,
                                     double topScore, String strategy,
                                     long latencyMs, String status) {
        log.info("RAG request: requestId={} questionLen={} retrievedDocs={} topScore={} model={} strategy={} latencyMs={} status={}",
                MDC.get("requestId"), userMessage.length(), retrievedDocs,
                String.format(Locale.US, "%.3f", topScore),
                llmConfig.getChatModel(), strategy, latencyMs, status);
    }

    // -----------------------------------------------------------------------
    // Private helpers
    // -----------------------------------------------------------------------

    private void logParameter(String runId, String key, String value) {
        try {
            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.APPLICATION_JSON);

            Map<String, Object> body = new HashMap<>();
            body.put("run_id", runId);
            body.put("key", key);
            body.put("value", value);

            HttpEntity<Map<String, Object>> entity = new HttpEntity<>(body, headers);
            restTemplate.exchange(MLFLOW_URL + "/runs/log-parameter", HttpMethod.POST, entity, String.class);
        } catch (Exception e) {
            log.warn("Failed to log MLflow parameter: {}", key, e);
        }
    }

    private void logMetric(String runId, String key, double value) {
        try {
            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.APPLICATION_JSON);

            Map<String, Object> body = new HashMap<>();
            body.put("run_id", runId);
            body.put("key", key);
            body.put("value", value);
            body.put("timestamp", System.currentTimeMillis());
            body.put("step", 0);

            HttpEntity<Map<String, Object>> entity = new HttpEntity<>(body, headers);
            restTemplate.exchange(MLFLOW_URL + "/runs/log-metric", HttpMethod.POST, entity, String.class);
        } catch (Exception e) {
            log.warn("Failed to log MLflow metric: {}", key, e);
        }
    }
}
