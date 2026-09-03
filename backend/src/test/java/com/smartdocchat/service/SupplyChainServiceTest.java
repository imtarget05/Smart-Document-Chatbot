package com.smartdocchat.service;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;
import org.springframework.test.util.ReflectionTestUtils;
import org.springframework.test.web.client.MockRestServiceServer;
import org.springframework.web.client.RestTemplate;

import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.springframework.test.web.client.ExpectedCount.once;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.*;
import static org.springframework.test.web.client.response.MockRestResponseCreators.withServerError;
import static org.springframework.test.web.client.response.MockRestResponseCreators.withSuccess;

/**
 * Unit tests for SupplyChainService covering the success path,
 * the internal-token header wiring, and the fallback (error) path.
 */
class SupplyChainServiceTest {

    private RestTemplate restTemplate;
    private MockRestServiceServer mockServer;
    private SupplyChainService service;

    @BeforeEach
    void setUp() {
        restTemplate = new RestTemplate();
        mockServer = MockRestServiceServer.bindTo(restTemplate).build();
        service = new SupplyChainService(restTemplate);
        ReflectionTestUtils.setField(service, "supplyChainBaseUrl", "http://sc-api.test");
    }

    @Test
    void forecast_returnsParsedBody_on2xx() {
        ReflectionTestUtils.setField(service, "internalToken", "secret");
        mockServer.expect(once(),
                requestTo("http://sc-api.test/forecast"))
                .andExpect(method(org.springframework.http.HttpMethod.POST))
                .andExpect(header("X-Internal-Token", "secret"))
                .andRespond(withSuccess("{\"forecast\":[10.0,20.0],\"method\":\"linear\"}", MediaType.APPLICATION_JSON));

        Map<String, Object> result = service.forecast(Map.of("history", java.util.List.of(1, 2, 3)));

        assertEquals(2, ((java.util.List<?>) result.get("forecast")).size());
        assertEquals("linear", result.get("method"));
    }

    @Test
    void post_returnsErrorMap_whenUpstreamFails() {
        mockServer.expect(requestTo("http://sc-api.test/supplier-risk"))
                .andRespond(withServerError());

        Map<String, Object> result = service.supplierRisk(Map.of("lead_time_std", 1));

        assertTrue(result.containsKey("error"));
                assertTrue(((String) result.get("error")).contains("unavailable"));
    }

    @Test
    void headers_excludeToken_whenNotConfigured() {
        ReflectionTestUtils.setField(service, "internalToken", "");
        mockServer.expect(requestTo("http://sc-api.test/anomaly-detect"))
                .andExpect(headerDoesNotExist("X-Internal-Token"))
                .andRespond(withSuccess("{\"count\":0}", MediaType.APPLICATION_JSON));

        service.anomalyDetect(Map.of("values", java.util.List.of(1, 2, 3, 4, 5)));
    }
}
