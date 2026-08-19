package com.smartdocchat.service;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.smartdocchat.util.LlmConfig;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.http.HttpMethod;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.client.RestClientException;
import org.springframework.web.client.RestTemplate;

import java.io.ByteArrayInputStream;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.concurrent.atomic.AtomicInteger;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class MessageHandlerTest {

    @Mock private RestTemplate restTemplate;

    private LlmConfig llmConfig;
    private MessageHandler messageHandler;

    @BeforeEach
    void setUp() {
        llmConfig = new LlmConfig();
        llmConfig.setChatModel("llama3.2:3b");
        llmConfig.setBaseUrl("http://localhost:8001");
        llmConfig.setMaxAttempts(2);
        llmConfig.setRetryBackoffMs(1);
        messageHandler = new MessageHandler(llmConfig, restTemplate);
    }

    @Test
    void buildPromptIncludesContextAndQuestion() {
        String prompt = messageHandler.buildPrompt("What is X?", List.of("chunk one", "chunk two"));
        assertTrue(prompt.contains("[1] chunk one"));
        assertTrue(prompt.contains("[2] chunk two"));
        assertTrue(prompt.contains("User Question: What is X?"));
    }

    @Test
    void buildPromptHandlesEmptyContext() {
        String prompt = messageHandler.buildPrompt("What is X?", List.of());
        assertTrue(prompt.contains("No relevant context was found in the document."));
    }

    @Test
    void buildsFallbackPromptsAndAbstention() {
        assertTrue(messageHandler.buildGeneralKnowledgePrompt("Q").contains("Use your internal knowledge"));
        assertTrue(messageHandler.buildWebSearchPrompt("Q", List.of("snippet")).contains("[1] snippet"));
        assertTrue(messageHandler.buildAbstentionResponse().contains("sufficient evidence"));
        assertTrue(messageHandler.buildInjectionBlockedResponse().contains("override the assistant's behavior"));
    }

    @Test
    @SuppressWarnings("unchecked")
    void callLLMOnceExtractsContentFromOllamaResponse() {
        Map<String, Object> body = Map.of("message", Map.of("content", "hello world"));
        when(restTemplate.exchange(eq("http://localhost:8001/api/chat"), eq(HttpMethod.POST), any(), eq(Map.class)))
                .thenReturn(ResponseEntity.ok(body));

        assertEquals("hello world", messageHandler.callLLMOnce("sys", "user"));
        assertEquals("hello world", messageHandler.callLLMOnce("prompt"));
    }

    @Test
    @SuppressWarnings("unchecked")
    void callLLMOnceReturnsErrorPlaceholderOnUnexpectedStructure() {
        when(restTemplate.exchange(eq("http://localhost:8001/api/chat"), eq(HttpMethod.POST), any(), eq(Map.class)))
                .thenReturn(ResponseEntity.ok(Map.of()));
        String result = messageHandler.callLLMOnce("sys", "user");
        assertTrue(result.startsWith("Sorry, I could not generate a response."));
    }

    @Test
    @SuppressWarnings("unchecked")
    void callLLMOnceReturnsUnavailablePlaceholderOnException() {
        when(restTemplate.exchange(eq("http://localhost:8001/api/chat"), eq(HttpMethod.POST), any(), eq(Map.class)))
                .thenThrow(new RestClientException("connection refused"));
        String result = messageHandler.callLLMOnce("sys", "user");
        assertTrue(result.startsWith("Sorry, the language model is temporarily unavailable."));
    }

    @Test
    @SuppressWarnings("unchecked")
    void callLLMRetriesUntilSuccess() throws Exception {
        Map<String, Object> okBody = Map.of("message", Map.of("content", "final answer"));
        Map<String, Object> errBody = Map.of();
        when(restTemplate.exchange(eq("http://localhost:8001/api/chat"), eq(HttpMethod.POST), any(), eq(Map.class)))
                .thenReturn(ResponseEntity.ok(errBody), ResponseEntity.ok(okBody));

        assertEquals("final answer", messageHandler.callLLM("sys", "user"));
    }

    @Test
    @SuppressWarnings("unchecked")
    void callLLMReturnsLastErrorAfterExhaustingRetries() {
        Map<String, Object> errBody = Map.of();
        when(restTemplate.exchange(eq("http://localhost:8001/api/chat"), eq(HttpMethod.POST), any(), eq(Map.class)))
                .thenReturn(ResponseEntity.ok(errBody));

        String result = messageHandler.callLLM("sys", "user");
        assertTrue(result.startsWith("Sorry, I could not generate a response."));
    }

    @Test
    @SuppressWarnings("unchecked")
    void streamLLMDeliversTokensToConsumer() throws Exception {
        String ndjson = "{\"message\":{\"content\":\"Hel\"}}\n{\"message\":{\"content\":\"lo world\"}}\n";
        AtomicInteger calls = new AtomicInteger();
        when(restTemplate.execute(eq("http://localhost:8001/api/chat"), eq(HttpMethod.POST),
                any(org.springframework.web.client.RequestCallback.class),
                any(org.springframework.web.client.ResponseExtractor.class)))
                .thenAnswer(inv -> {
                    calls.incrementAndGet();
                    org.springframework.web.client.ResponseExtractor<Object> extractor = inv.getArgument(3);
                    org.springframework.http.client.ClientHttpResponse mockResponse =
                            mock(org.springframework.http.client.ClientHttpResponse.class);
                    when(mockResponse.getStatusCode()).thenReturn(HttpStatus.OK);
                    when(mockResponse.getBody()).thenReturn(
                            new ByteArrayInputStream(ndjson.getBytes(StandardCharsets.UTF_8)));
                    return extractor.extractData(mockResponse);
                });

        List<String> tokens = new ArrayList<>();
        messageHandler.streamLLM("sys", "user", tokens::add);

        assertEquals(List.of("Hel", "lo world"), tokens);
        assertEquals(1, calls.get());
    }

    @Test
    @SuppressWarnings("unchecked")
    void streamLLMPropagatesTransportErrors() {
        when(restTemplate.execute(eq("http://localhost:8001/api/chat"), eq(HttpMethod.POST),
                any(org.springframework.web.client.RequestCallback.class),
                any(org.springframework.web.client.ResponseExtractor.class)))
                .thenThrow(new IllegalStateException("Ollama stream request failed: 500"));

        assertThrows(IllegalStateException.class, () -> messageHandler.streamLLM("sys", "user", t -> {
        }));
    }

    private boolean callsNoOp() {
        return true;
    }
}