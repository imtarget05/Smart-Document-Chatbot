package com.smartdocchat.controller;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.BooleanNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import com.fasterxml.jackson.databind.node.TextNode;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import lombok.Data;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.*;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.client.HttpClientErrorException;
import org.springframework.web.client.RestTemplate;

import java.security.Principal;
import java.util.List;

/**
 * AgentController – proxies requests from the frontend to the Python Agent Service.
 *
 * All requests are authenticated by the existing JWT filter before reaching here.
 * The controller injects the INTERNAL_SERVICE_TOKEN before forwarding to the agent.
 *
 * Routes:
 *   POST /agent/invoke          → Orchestrator (auto-select sub-agent)
 *   POST /agent/report          → Report generation
 *   POST /agent/action          → Action execution (email, Jira, Notion, webhook)
 *   POST /agent/connector/ingest → Ingest from external connector
 *   GET  /agent/health          → Agent service health check
 */
@RestController
@RequestMapping("/agent")
@RequiredArgsConstructor
@Slf4j
public class AgentController {

    private static final String FIELD_USER_ID = "user_id";
    private static final String FIELD_ERROR   = "error";

    private final RestTemplate restTemplate;
    private final ObjectMapper objectMapper;

    @Value("${agent.service.url:http://localhost:9000}")
    private String agentServiceUrl;

    @Value("${service.internal-token}")
    private String internalServiceToken;

    // ──────────────────────────────────────────────────────────────────────
    // Request DTOs
    // ──────────────────────────────────────────────────────────────────────
    @Data
    public static class AgentInvokeRequest {
        @NotBlank
        @Size(max = 10000)
        private String query;

        @NotBlank
        @Size(max = 200)
        private String sessionId;

        private List<String> documentIds;
        private boolean useWebSearch = false;
        private String intentOverride;
    }

    @Data
    public static class ReportGenerateRequest {
        @NotBlank private String title;
        @NotBlank private String content;
    }

    @Data
    public static class ActionExecuteRequest {
        @NotBlank private String actionType;
        private Object payload;
    }

    @Data
    public static class ConnectorIngestRequest {
        @NotBlank private String source;
        private Object params;
    }

    // ──────────────────────────────────────────────────────────────────────
    // Endpoints
    // ──────────────────────────────────────────────────────────────────────

    /**
     * Main agent invocation – Orchestrator decides which sub-agent to use.
     */
    @PostMapping("/invoke")
    public ResponseEntity<JsonNode> invokeAgent(
            @Valid @RequestBody AgentInvokeRequest request,
            Principal principal) {

        ObjectNode body = objectMapper.createObjectNode();
        body.set("query",          TextNode.valueOf(request.getQuery()));
        body.set("session_id",     TextNode.valueOf(request.getSessionId()));
        body.set(FIELD_USER_ID,    TextNode.valueOf(principal.getName()));
        body.set("use_web_search", BooleanNode.valueOf(request.isUseWebSearch()));
        if (request.getIntentOverride() != null) {
            body.set("intent_override", TextNode.valueOf(request.getIntentOverride()));
        }
        if (request.getDocumentIds() != null) {
            body.putPOJO("document_ids", request.getDocumentIds());
        }

        return forwardToAgent("/agent/invoke", body);
    }

    /**
     * Explicit report generation endpoint.
     */
    @PostMapping("/report")
    public ResponseEntity<JsonNode> generateReport(
            @Valid @RequestBody ReportGenerateRequest request,
            Principal principal) {

        ObjectNode body = objectMapper.createObjectNode();
        body.set("title",     TextNode.valueOf(request.getTitle()));
        body.set("content",   TextNode.valueOf(request.getContent()));
        body.set(FIELD_USER_ID, TextNode.valueOf(principal.getName()));

        return forwardToAgent("/agent/report", body);
    }

    /**
     * Execute an action (send email, create Jira ticket, etc.).
     */
    @PostMapping("/action")
    public ResponseEntity<JsonNode> executeAction(
            @Valid @RequestBody ActionExecuteRequest request,
            Principal principal) {

        ObjectNode body = objectMapper.createObjectNode();
        body.set("action_type", TextNode.valueOf(request.getActionType()));
        body.set(FIELD_USER_ID,  TextNode.valueOf(principal.getName()));
        body.putPOJO("payload", request.getPayload());

        return forwardToAgent("/agent/action", body);
    }

    /**
     * Ingest data from an external connector (Google Drive, Gmail, Slack, SharePoint).
     */
    @PostMapping("/connector/ingest")
    public ResponseEntity<JsonNode> connectorIngest(
            @Valid @RequestBody ConnectorIngestRequest request,
            Principal principal) {

        ObjectNode body = objectMapper.createObjectNode();
        body.set("source",     TextNode.valueOf(request.getSource()));
        body.set(FIELD_USER_ID, TextNode.valueOf(principal.getName()));
        body.putPOJO("params", request.getParams());

        return forwardToAgent("/agent/connector/ingest", body);
    }

    /**
     * Health check – proxies to Python agent /health.
     */
    @GetMapping("/health")
    public ResponseEntity<JsonNode> agentHealth() {
        HttpHeaders headers = buildHeaders();
        try {
            ResponseEntity<JsonNode> response = restTemplate.exchange(
                    agentServiceUrl + "/health",
                    HttpMethod.GET,
                    new HttpEntity<>(headers),
                    JsonNode.class);
            return ResponseEntity.ok(response.getBody());
        } catch (Exception e) {
            log.warn("Agent health check failed: {}", e.getMessage());
            ObjectNode err = objectMapper.createObjectNode();
            err.put("status", "unavailable");
            err.put(FIELD_ERROR, e.getMessage());
            return ResponseEntity.status(503).body(err);
        }
    }

    // ──────────────────────────────────────────────────────────────────────
    // Internal helpers
    // ──────────────────────────────────────────────────────────────────────
    private ResponseEntity<JsonNode> forwardToAgent(String path, Object requestBody) {
        String url = agentServiceUrl + path;
        HttpHeaders headers = buildHeaders();
        HttpEntity<Object> entity = new HttpEntity<>(requestBody, headers);

        try {
            ResponseEntity<JsonNode> response = restTemplate.exchange(
                    url, HttpMethod.POST, entity, JsonNode.class);
            return ResponseEntity.status(response.getStatusCode()).body(response.getBody());
        } catch (HttpClientErrorException ex) {
            log.error("Agent service returned error {}: {}", ex.getStatusCode(), ex.getResponseBodyAsString());
            ObjectNode errNode = objectMapper.createObjectNode();
            errNode.put(FIELD_ERROR, "Agent service error");
            errNode.put("detail", ex.getResponseBodyAsString());
            return ResponseEntity.status(ex.getStatusCode()).body(errNode);
        } catch (Exception ex) {
            log.error("Failed to reach agent service at {}: {}", url, ex.getMessage());
            ObjectNode errNode = objectMapper.createObjectNode();
            errNode.put(FIELD_ERROR, "Agent service unavailable");
            errNode.put("detail", ex.getMessage());
            return ResponseEntity.status(503).body(errNode);
        }
    }

    private HttpHeaders buildHeaders() {
        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);
        headers.set("X-Internal-Token", internalServiceToken);
        return headers;
    }
}
