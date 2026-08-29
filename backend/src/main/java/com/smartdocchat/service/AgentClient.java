package com.smartdocchat.service;

import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestTemplate;

import java.util.HashMap;
import java.util.Map;

@Component
@Slf4j
public class AgentClient {

    private final RestTemplate restTemplate;
    private final String agentBaseUrl;
    private final int timeoutMs;

    public AgentClient(RestTemplate restTemplate,
                       @Value("${agent.base-url:http://localhost:8001}") String agentBaseUrl,
                       @Value("${agent.timeout-ms:15000}") int timeoutMs) {
        this.restTemplate = restTemplate;
        this.agentBaseUrl = agentBaseUrl;
        this.timeoutMs = timeoutMs;
    }

    public record AgentResponse(String answer, String traceId) {}

    public AgentResponse invokeAgent(String ownerUsername, String sessionId,
                                     String message, String traceId) {
        String url = agentBaseUrl + "/agent/invoke";
        Map<String, Object> body = new HashMap<>();
        body.put("message", message);
        body.put("trace_id", traceId);
        body.put("session_id", sessionId);
        body.put("owner", ownerUsername);
        try {
            @SuppressWarnings("unchecked")
            Map<String, Object> resp = restTemplate.postForObject(url, body, Map.class);
            if (resp != null) {
                String answer = (String) resp.get("answer");
                String respTraceId = (String) resp.getOrDefault("trace_id", traceId);
                return new AgentResponse(answer != null ? answer : "", respTraceId);
            }
        } catch (Exception e) {
            log.warn("Agent invoke failed url={} err={}", url, e.getMessage());
            throw new RuntimeException("agent unavailable: " + e.getMessage(), e);
        }
        return new AgentResponse("", traceId);
    }
}
