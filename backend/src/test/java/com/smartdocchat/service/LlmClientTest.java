package com.smartdocchat.service;

import com.smartdocchat.metrics.RagMetrics;
import com.smartdocchat.util.LlmConfig;
import io.github.resilience4j.circuitbreaker.CallNotPermittedException;
import io.github.resilience4j.circuitbreaker.CircuitBreaker;
import io.github.resilience4j.circuitbreaker.CircuitBreakerConfig;
import io.github.resilience4j.circuitbreaker.CircuitBreakerRegistry;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpMethod;
import org.springframework.http.ResponseEntity;
import org.springframework.test.util.ReflectionTestUtils;
import org.springframework.web.client.ResourceAccessException;
import org.springframework.web.client.RestTemplate;

import java.time.Duration;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertInstanceOf;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

/**
 * Exercises the circuit-breaker semantics of {@link LlmClient} against a real
 * resilience4j registry. The annotation aspect is bypassed on purpose: the
 * breaker is applied programmatically around the same method the aspect wraps,
 * which keeps this a fast unit test while asserting genuine CB transitions.
 */
@ExtendWith(MockitoExtension.class)
class LlmClientTest {

    @Mock private RestTemplate restTemplate;

    private LlmClient llmClient;
    private CircuitBreaker circuitBreaker;

    private static final String SYS = "sys";
    private static final String USER = "user";

    @BeforeEach
    void setUp() {
        LlmConfig llmConfig = new LlmConfig();
        llmConfig.setChatModel("test-model");
        llmConfig.setBaseUrl("http://localhost:8001");

        llmClient = new LlmClient(restTemplate, llmConfig,
                new RagMetrics(new io.micrometer.core.instrument.simple.SimpleMeterRegistry()));
        ReflectionTestUtils.setField(llmClient, "internalToken", "");

        CircuitBreakerConfig config = CircuitBreakerConfig.custom()
                .slidingWindowSize(10)
                .minimumNumberOfCalls(5)
                .failureRateThreshold(50)
                .waitDurationInOpenState(Duration.ofMillis(1))
                .permittedNumberOfCallsInHalfOpenState(3)
                .recordExceptions(ResourceAccessException.class)
                .build();
        circuitBreaker = CircuitBreakerRegistry.of(config).circuitBreaker("llmService");
    }

    private String guardedChat() {
        return circuitBreaker.executeSupplier(() -> llmClient.chat(SYS, USER));
    }

    @Test
    void chatReturnsContentOnSuccess() {
        when(restTemplate.exchange(eq("http://localhost:8001/api/chat"), eq(HttpMethod.POST),
                any(HttpEntity.class), eq(Map.class)))
                .thenReturn(ResponseEntity.ok(Map.of(
                        "message", Map.of("content", "answer"),
                        "eval_count", 42)));

        assertEquals("answer", guardedChat());
    }

    @Test
    void transportFailuresOpenTheCircuitAndSubsequentCallsFailFast() {
        when(restTemplate.exchange(eq("http://localhost:8001/api/chat"), eq(HttpMethod.POST),
                any(HttpEntity.class), eq(Map.class)))
                .thenThrow(new ResourceAccessException("connection refused"));

        for (int i = 0; i < 5; i++) {
            assertEquals(LlmClient.UNAVAILABLE_RESPONSE,
                    llmClient.chatFallback(SYS, USER, assertThrows(ResourceAccessException.class, this::guardedChat)));
        }
        assertEquals(CircuitBreaker.State.OPEN, circuitBreaker.getState());

        // Open circuit: the provider is no longer contacted at all.
        assertThrows(CallNotPermittedException.class, this::guardedChat);
        verify(restTemplate, times(5)).exchange(eq("http://localhost:8001/api/chat"),
                eq(HttpMethod.POST), any(HttpEntity.class), eq(Map.class));
    }

    @Test
    void clientErrorsDoNotTripTheCircuit() {
        when(restTemplate.exchange(eq("http://localhost:8001/api/chat"), eq(HttpMethod.POST),
                any(HttpEntity.class), eq(Map.class)))
                .thenReturn(ResponseEntity.ok(Map.of()));

        for (int i = 0; i < 8; i++) {
            assertEquals(LlmClient.NO_RESPONSE_PLACEHOLDER,
                    llmClient.chatFallback(SYS, USER,
                            assertThrows(LlmClient.UnexpectedResponseException.class, this::guardedChat)));
        }
        assertEquals(CircuitBreaker.State.CLOSED, circuitBreaker.getState());
    }

    @Test
    void halfOpenSuccessesCloseTheCircuitAgain() {
        java.util.concurrent.atomic.AtomicInteger attempts = new java.util.concurrent.atomic.AtomicInteger();
        when(restTemplate.exchange(eq("http://localhost:8001/api/chat"), eq(HttpMethod.POST),
                any(HttpEntity.class), eq(Map.class)))
                .thenAnswer(inv -> {
                    if (attempts.incrementAndGet() <= 5) {
                        throw new ResourceAccessException("down");
                    }
                    return ResponseEntity.ok(Map.of("message", Map.of("content", "back")));
                });

        // Trip the breaker (minimumNumberOfCalls=5).
        for (int i = 0; i < 5; i++) {
            try {
                guardedChat();
            } catch (ResourceAccessException | CallNotPermittedException expected) {
                // until the breaker opens / half-opens
            }
        }
        assertEquals(CircuitBreaker.State.OPEN, circuitBreaker.getState());

        // waitDurationInOpenState=1ms → after it elapses the next call moves
        // the breaker to HALF_OPEN; a successful trial lets traffic through.
        try {
            Thread.sleep(5);
        } catch (InterruptedException ignored) {
            Thread.currentThread().interrupt();
        }
        assertEquals("back", guardedChat());
        assertEquals("back", guardedChat());
    }

    @Test
    void fallbackMapsExceptionsToCallerFacingPlaceholders() {
        assertEquals(LlmClient.UNAVAILABLE_RESPONSE, llmClient.chatFallback(
                SYS, USER, new ResourceAccessException("timeout")));
        assertEquals(LlmClient.NO_RESPONSE_PLACEHOLDER, llmClient.chatFallback(
                SYS, USER, new LlmClient.UnexpectedResponseException("bad body")));
    }
}
