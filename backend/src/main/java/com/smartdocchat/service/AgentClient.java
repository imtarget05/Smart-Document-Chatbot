package com.smartdocchat.service;

import com.smartdocchat.entity.AgentState;
import com.smartdocchat.repository.AgentStateRepository;
import io.github.resilience4j.circuitbreaker.annotation.CircuitBreaker;
import io.github.resilience4j.retry.annotation.Retry;
import lombok.extern.slf4j.Slf4j;
import org.slf4j.MDC;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestTemplate;

import java.util.HashMap;
import java.util.Map;

/**
 * Client gọi llm-router agentic path (/v1/agent/invoke).
 *
 * Persistence: mỗi lần invoke được ghi 1 dòng vào agent_state table
 * (session, owner, trace, answer, status). Lỗi DB không ảnh hưởng
 * tới luồng agent — chỉ log warn.
 */
@Component
@Slf4j
public class AgentClient {

    private final RestTemplate restTemplate;
    private final AgentStateRepository agentStateRepository;
    private final String agentBaseUrl;
    private final int timeoutMs;

    public AgentClient(@Qualifier("agentRestTemplate") RestTemplate restTemplate,
                       @org.springframework.lang.Nullable AgentStateRepository agentStateRepository,
                       @Value("${agent.base-url:http://localhost:9000}") String agentBaseUrl,
                       @Value("${agent.timeout-ms:15000}") int timeoutMs) {
        this.restTemplate = restTemplate;
        this.agentStateRepository = agentStateRepository;
        this.agentBaseUrl = agentBaseUrl;
        this.timeoutMs = timeoutMs;
    }

    public record AgentResponse(String answer, String agentType, java.util.List<?> sources,
                                 Double confidence, String traceId) {
        public AgentResponse(String answer, String traceId) {
            this(answer, null, java.util.List.of(), null, traceId);
        }
    }

    @CircuitBreaker(name = "agentService", fallbackMethod = "invokeAgentFallback")
    @Retry(name = "agentService")
    public AgentResponse invokeAgent(String ownerUsername, String sessionId,
                                     String message, String traceId) {
        String url = agentBaseUrl + "/v1/agent/invoke";
        Map<String, Object> body = new HashMap<>();
        body.put("query", message);
        body.put("session_id", sessionId);
        body.put("user_id", ownerUsername);
        if (traceId != null) {
            body.put("trace_id", traceId);
        }
        String requestId = MDC.get("requestId");
        if (requestId != null) {
            body.put("request_id", requestId);
        }

        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);
        if (traceId != null) {
            headers.set("X-Langfuse-Trace-Id", traceId);
        }
        if (requestId != null) {
            headers.set("X-Request-Id", requestId);
        }
        HttpEntity<Map<String, Object>> entity = new HttpEntity<>(body, headers);

        AgentResponse result;
        try {
            @SuppressWarnings("unchecked")
            Map<String, Object> resp = restTemplate.postForObject(url, entity, Map.class);
            if (resp != null) {
                String answer = (String) resp.get("answer");
                String agentType = (String) resp.getOrDefault("agent_type", "rag");
                Object sourcesObj = resp.getOrDefault("sources", java.util.List.of());
                java.util.List<?> sources = sourcesObj instanceof java.util.List<?>
                        ? (java.util.List<?>) sourcesObj : java.util.List.of();
                Object confidenceObj = resp.get("confidence_score");
                Double confidence = confidenceObj instanceof Number
                        ? ((Number) confidenceObj).doubleValue() : null;
                String respTraceId = (String) resp.getOrDefault("trace_id", traceId);
                result = new AgentResponse(answer != null ? answer : "", agentType, sources,
                        confidence, respTraceId);
            } else {
                result = new AgentResponse("", traceId);
            }
        } catch (Exception e) {
            log.warn("Agent invoke failed url={} traceId={} err={}", url, traceId, e.getMessage());
            persistState(ownerUsername, sessionId, traceId, null, "failed", e.getMessage());
            throw new RuntimeException("agent unavailable: " + e.getMessage(), e);
        }
        persistState(ownerUsername, sessionId, traceId, result.answer(), "done", null);
        return result;
    }

    @SuppressWarnings("unused")
    private AgentResponse invokeAgentFallback(String ownerUsername, String sessionId,
                                              String message, String traceId, Exception ex) {
        log.warn("Agent circuit breaker fallback traceId={} err={}", traceId, ex.getMessage());
        persistState(ownerUsername, sessionId, traceId, null, "failed", "circuit_open: " + ex.getMessage());
        throw new RuntimeException("agent unavailable (circuit open): " + ex.getMessage(), ex);
    }

    private void persistState(String owner, String sessionId, String traceId,
                              String answer, String status, String error) {
        if (agentStateRepository == null) {
            return;
        }
        try {
            AgentState state = AgentState.builder()
                    .sessionId(sessionId)
                    .ownerUsername(owner)
                    .traceId(traceId)
                    .currentStep("invoke")
                    .finalAnswer(answer != null ? answer : (error != null ? "ERROR: " + error : null))
                    .status(status)
                    .build();
            agentStateRepository.save(state);
        } catch (Exception dbEx) {
            log.warn("Failed to persist agent state session={} err={}", sessionId, dbEx.getMessage());
        }
    }
}
