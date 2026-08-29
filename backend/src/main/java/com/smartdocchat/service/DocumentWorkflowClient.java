package com.smartdocchat.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestTemplate;

import java.util.HashMap;
import java.util.Map;

/**
 * Client gọi llm-router /document/workflow (Phase 2 document agentic pipeline).
 *
 * Flow: upload -> extract text (backend) -> gửi text sang router -> router chạy
 * LangGraph document workflow (classify -> extract -> map -> match PO↔Invoice)
 * -> trả final_result. Backend lưu kết quả vào Document.workflowResult.
 *
 * Gọi bất đồng bộ (fire-and-forget) để không block upload response. Nếu router
 * lỗi hoặc chưa deploy, upload vẫn thành công (graceful degradation).
 */
@Component
@Slf4j
public class DocumentWorkflowClient {

    private final RestTemplate restTemplate;
    private final ObjectMapper objectMapper;
    private final String routerBaseUrl;
    private final String internalToken;

    public DocumentWorkflowClient(RestTemplate restTemplate,
                                   ObjectMapper objectMapper,
                                   @Value("${llm.base-url:http://localhost:8001}") String routerBaseUrl,
                                   @Value("${security.internal-token:}") String internalToken) {
        this.restTemplate = restTemplate;
        this.objectMapper = objectMapper;
        this.routerBaseUrl = routerBaseUrl;
        this.internalToken = internalToken;
    }

    /**
     * Gửi văn bản sang router chạy document workflow.
     * Trả về JSON string kết quả, hoặc null nếu lỗi.
     */
    public String runWorkflow(String text, String filename) {
        String url = routerBaseUrl + "/document/workflow";
        try {
            Map<String, Object> body = new HashMap<>();
            body.put("text", text);
            body.put("filename", filename);

            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.APPLICATION_JSON);
            if (internalToken != null && !internalToken.isBlank()) {
                headers.set("X-Internal-Token", internalToken);
            }
            HttpEntity<Map<String, Object>> entity = new HttpEntity<>(body, headers);

            Map<?, ?> resp = restTemplate.postForObject(url, entity, Map.class);
            if (resp != null) {
                return objectMapper.writeValueAsString(resp);
            }
        } catch (Exception e) {
            log.warn("Document workflow call failed ({}): {}", url, e.getMessage());
        }
        return null;
    }
}
