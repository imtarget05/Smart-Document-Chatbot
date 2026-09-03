package com.smartdocchat.service;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.*;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;

import java.util.Map;

/**
 * Proxies requests from the React frontend to the FastAPI Supply Chain module.
 * The backend injects the internal token so the frontend never sees it.
 */
@Service
@RequiredArgsConstructor
@Slf4j
public class SupplyChainService {

    private final RestTemplate restTemplate = new RestTemplate();

    @Value("${supply.chain.api-url:http://localhost:8000}")
    private String supplyChainBaseUrl;

    @Value("${SUPPLY_CHAIN_INTERNAL_TOKEN:}")
    private String internalToken;

    private HttpHeaders buildHeaders() {
        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);
        if (internalToken != null && !internalToken.isBlank()) {
            headers.set("X-Internal-Token", internalToken);
        }
        return headers;
    }

    public Map<String, Object> forecast(Map<String, Object> body) {
        return post("/forecast", body);
    }

    public Map<String, Object> optimizeRoute(Map<String, Object> body) {
        return post("/optimize-route", body);
    }

    public Map<String, Object> supplierRisk(Map<String, Object> body) {
        return post("/supplier-risk", body);
    }

    public Map<String, Object> anomalyDetect(Map<String, Object> body) {
        return post("/anomaly-detect", body);
    }

    public Map<String, Object> inventoryOptimalOrder(Map<String, Object> body) {
        return post("/inventory-optimal-order", body);
    }

    @SuppressWarnings("unchecked")
    private Map<String, Object> post(String path, Map<String, Object> body) {
        HttpEntity<Map<String, Object>> entity = new HttpEntity<>(body, buildHeaders());
        try {
            ResponseEntity<Map> response = restTemplate.exchange(
                    supplyChainBaseUrl + path,
                    HttpMethod.POST,
                    entity,
                    Map.class
            );
            return response.getBody();
        } catch (Exception e) {
            log.warn("Supply chain call to {} failed: {}", path, e.getMessage());
            return Map.of("error", "Supply chain service unavailable: " + e.getMessage());
        }
    }
}