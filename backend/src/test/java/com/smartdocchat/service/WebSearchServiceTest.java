package com.smartdocchat.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.smartdocchat.config.TavilyConfig;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.client.RestTemplate;

import java.util.List;
import java.util.Optional;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.lenient;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class WebSearchServiceTest {

    @Mock private TavilyConfig tavilyConfig;
    @Mock private RestTemplate restTemplate;

    private WebSearchService webSearchService;

    @Test
    void returnsEmptyWhenNotConfigured() {
        webSearchService = new WebSearchService(tavilyConfig, restTemplate);
        lenient().when(tavilyConfig.isConfigured()).thenReturn(false);

        assertTrue(webSearchService.search("query").isEmpty());
        assertTrue(webSearchService.search("query", 5).isEmpty());
    }

    @Test
    void parsesResultsAndFiltersShortContent() throws Exception {
        webSearchService = new WebSearchService(tavilyConfig, restTemplate);
        lenient().when(tavilyConfig.isConfigured()).thenReturn(true);
        lenient().when(tavilyConfig.getApiKey()).thenReturn("k");
        lenient().when(tavilyConfig.getUrl()).thenReturn("https://api.tavily.com/search");

        String json = """
                {"results":[
                  {"content":"This is a sufficiently long snippet from the web."},
                  {"content":"tiny"},
                  {"content":"Another long enough snippet to be returned as well."}
                ]}""";
        lenient().when(restTemplate.postForEntity(eq("https://api.tavily.com/search"), any(), eq(com.fasterxml.jackson.databind.JsonNode.class)))
                .thenReturn(ResponseEntity.ok(new ObjectMapper().readTree(json)));

        Optional<List<String>> result = webSearchService.search("latest news");

        assertTrue(result.isPresent());
        assertEquals(2, result.get().size());
    }

    @Test
    void returnsEmptyOnNon2xxStatus() {
        webSearchService = new WebSearchService(tavilyConfig, restTemplate);
        lenient().when(tavilyConfig.isConfigured()).thenReturn(true);
        lenient().when(restTemplate.postForEntity(eq("https://api.tavily.com/search"), any(), eq(com.fasterxml.jackson.databind.JsonNode.class)))
                .thenReturn(ResponseEntity.status(HttpStatus.BAD_GATEWAY).body(null));

        assertTrue(webSearchService.search("query").isEmpty());
    }

    @Test
    void returnsEmptyWhenNoSnippetsMeetLength() throws Exception {
        webSearchService = new WebSearchService(tavilyConfig, restTemplate);
        lenient().when(tavilyConfig.isConfigured()).thenReturn(true);
        String json = "{\"results\":[{\"content\":\"short\"},{\"content\":\"too short\"}]}";
        lenient().when(restTemplate.postForEntity(eq("https://api.tavily.com/search"), any(), eq(com.fasterxml.jackson.databind.JsonNode.class)))
                .thenReturn(ResponseEntity.ok(new ObjectMapper().readTree(json)));

        assertTrue(webSearchService.search("query").isEmpty());
    }

    @Test
    void returnsEmptyWhenRequestFails() {
        webSearchService = new WebSearchService(tavilyConfig, restTemplate);
        lenient().when(tavilyConfig.isConfigured()).thenReturn(true);
        lenient().when(restTemplate.postForEntity(eq("https://api.tavily.com/search"), any(), eq(com.fasterxml.jackson.databind.JsonNode.class)))
                .thenThrow(new RuntimeException("network down"));

        assertTrue(webSearchService.search("query").isEmpty());
    }
}