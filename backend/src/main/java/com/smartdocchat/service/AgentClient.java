package com.smartdocchat.service;

import com.smartdocchat.entity.AgentState;
import com.smartdocchat.repository.AgentStateRepository;
import com.smartdocchat.util.LlmConfig;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.*;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;

import java.time.LocalDateTime;
import java.util.*;

/**
 * Client cho agentic supply chain workflows.
 *
 * Gọi llm-router agent (LangGraph) để xử lý supply chain intent.
 * Agent trả về final_answer + tool_result — backend log vào agent_state table.
 *
 * Fallback: khi agent/service unreachable, trả deterministic placeholder
 * (grounded principle — không hallucinate).
 */
@Service
@RequiredArgsConstructor
@Slf4j
public class AgentClient {

    private final RestTemplate restTemplate;
    private final AgentStateRepository agentStateRepository;
    private final LlmConfig llmConfig;
    private final ObjectMapper objectMapper = new ObjectMapper();

    @Value("${agent.service.url:http://localhost:9000}")
    private String agentBaseUrl;

    @Value("${security.internal-token:}")
    private String internalToken;

    /**
     * Invoke agent cho supply chain question.
     * Trả final_answer từ agent; lưu state vào DB.
     */
    public AgentResponse invokeAgent(String ownerUsername, String sessionId,
                                      String userMessage, String traceId) {
        AgentState state = buildInitialState(sessionId, ownerUsername, traceId);
        state = agentStateRepository.save(state);
        String finalAnswer = buildFallbackAnswer();

        try {
            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.APPLICATION_JSON);
            if (internalToken != null && !internalToken.isBlank()) {
                headers.set("X-Internal-Token", internalToken);
            }
            // Propagate Langfuse trace id
            Map<String, String> traceHeaders = langfuseTraceHeaders(traceId);
            traceHeaders.forEach(headers::set);

            Map<String, Object> requestBody = new HashMap<>();
            requestBody.put("message", userMessage);
            requestBody.put("trace_id", traceId != null ? traceId : "");
            requestBody.put("tool_params", Map.of());

            ResponseEntity<Map> response = restTemplate.exchange(
                    agentBaseUrl + "/agent/invoke",
                    HttpMethod.POST,
                    new HttpEntity<>(requestBody, headers),
                    Map.class
            );

            if (response.getStatusCode().is2xxSuccessful() && response.getBody() != null) {
                Object answerObj = response.getBody().get("answer");
                Object stateObj = response.getBody().get("state");
                if (answerObj != null) {
                    finalAnswer = answerObj.toString();
                }
                if (stateObj != null && stateObj instanceof Map) {
                    @SuppressWarnings("unchecked")
                    Map<String, Object> agentState = (Map<String, Object>) stateObj;
                    updateStateFromAgent(state, agentState, finalAnswer);
                }
            } else {
                log.warn("Agent returned non-2xx: {}", response.getStatusCode());
            }
        } catch (Exception e) {
            log.error("Agent invoke failed: {}", e.getMessage(), e);
            // Fallback — deterministic, không hallucinate
            finalAnswer = "Xin lỗi, dịch vụ supply chain đang không khả dụng. Vui lòng thử lại sau.";
            state.setStatus("fallback");
            state.setToolResult("{\"status\": \"error\", \"detail\": \"" + e.getMessage() + "\"}");
        }

        state.setFinalAnswer(finalAnswer);
        state.setUpdatedAt(LocalDateTime.now());
        state.setStatus("completed");
        agentStateRepository.save(state);

        return new AgentResponse(finalAnswer, state.getToolChoice(), state.getToolResult());
    }

    private AgentState buildInitialState(String sessionId, String ownerUsername, String traceId) {
        return AgentState.builder()
                .sessionId(sessionId)
                .ownerUsername(ownerUsername)
                .traceId(traceId)
                .currentStep("intent")
                .status("active")
                .createdAt(LocalDateTime.now())
                .updatedAt(LocalDateTime.now())
                .build();
    }

    @SuppressWarnings("unchecked")
    private void updateStateFromAgent(AgentState state, Map<String, Object> agentStateMap,
                                        String finalAnswer) {
        Object toolChoice = agentStateMap.get("tool_choice");
        Object toolResult = agentStateMap.get("tool_result");
        state.setToolChoice(toolChoice != null ? toolChoice.toString() : "");
        state.setToolResult(toolResult != null ? toolResult.toString() : "");
        state.setCurrentStep("answer");
    }

    private Map<String, String> langfuseTraceHeaders(String traceId) {
        Map<String, String> headers = new HashMap<>();
        if (traceId != null && !traceId.isBlank()) {
            headers.put("X-Langfuse-Trace-Id", traceId);
        }
        return headers;
    }

    private String buildFallbackAnswer() {
        return "Xin lỗi, tôi đang xử lý yêu cầu supply chain của bạn. Vui lòng chờ tích cực.";
    }

    public record AgentResponse(String answer, String toolChoice, String toolResult) {}
}
