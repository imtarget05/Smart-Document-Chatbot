package com.smartdocchat.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.client.RestClientException;
import org.springframework.web.client.RestTemplate;

import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

class DocumentClassificationServiceTest {

    private RestTemplate restTemplate;
    private DocumentClassificationService service;

    @BeforeEach
    void setUp() throws Exception {
        restTemplate = mock(RestTemplate.class);
        service = new DocumentClassificationService(restTemplate, new ObjectMapper());
        var field = DocumentClassificationService.class
                .getDeclaredField("llmRouterBaseUrl");
        field.setAccessible(true);
        field.set(service, "http://localhost:8010");
    }

    @Test
    void classifiesViaLlmRouter() {
        when(restTemplate.postForEntity(anyString(), any(), eq(Map.class)))
                .thenReturn(new ResponseEntity<>(Map.of("document_type", "PO"), HttpStatus.OK));

        assertEquals("PO", service.classifyDocument("purchase order po #123", "doc.pdf"));
    }

    @Test
    void fallsBackToHeuristicWhenRouterFails() {
        when(restTemplate.postForEntity(anyString(), any(), eq(Map.class)))
                .thenThrow(new RestClientException("router down"));

        assertEquals("INVOICE", service.classifyDocument("hóa đơn số 001, thành tiền 500 USD", "x.pdf"));
    }

    @Test
    void heuristicReturnsOtherForUnknownText() {
        when(restTemplate.postForEntity(anyString(), any(), eq(Map.class)))
                .thenThrow(new RestClientException("router down"));

        assertEquals("OTHER", service.classifyDocument("random content here", "random.pdf"));
    }
}