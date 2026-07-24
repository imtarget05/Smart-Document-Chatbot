package com.smartdoc.agent.resilience;

import com.smartdoc.agent.service.ResilientLlmService;
import io.github.resilience4j.circuitbreaker.CircuitBreaker;
import io.github.resilience4j.circuitbreaker.CircuitBreakerRegistry;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;

import java.util.concurrent.atomic.AtomicInteger;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Test cho Day 1: Circuit Breaker + Time Limiter.
 *
 * Test 3 kịch bản:
 * 1. LLM thành công → trả response
 * 2. LLM fail liên tục → circuit mở → trả fallback
 * 3. LLM chậm quá 5s → timeout → trả fallback
 */
@SpringBootTest
class ResilientLlmServiceTest {

    @Autowired
    private ResilientLlmService resilientLlmService;

    @Autowired
    private CircuitBreakerRegistry registry;

    @Test
    void testSuccessfulCall() {
        AtomicInteger counter = new AtomicInteger(0);
        // Reset circuit breaker về CLOSED trước mỗi test
        registry.circuitBreaker("llmService").reset();

        String result = resilientLlmService.callLlmWithResilience(
                () -> { counter.incrementAndGet(); return "OK"; },
                () -> "FALLBACK"
        );

        assertEquals("OK", result);
        assertEquals(1, counter.get());
        assertEquals(CircuitBreaker.State.CLOSED,
                resilientLlmService.getCircuitState());
    }

    @Test
    void testFallbackWhenCircuitOpen() {
        registry.circuitBreaker("llmService").reset();

        // Gây fail 10 lần liên tiếp để circuit mở
        for (int i = 0; i < 10; i++) {
            resilientLlmService.callLlmWithResilience(
                    () -> { throw new RuntimeException("LLM down"); },
                    () -> "FALLBACK"
            );
        }

        // Circuit phải OPEN
        assertEquals(CircuitBreaker.State.OPEN,
                resilientLlmService.getCircuitState());

        // Call tiếp theo phải trả FALLBACK ngay, không gọi LLM
        AtomicInteger callCount = new AtomicInteger(0);
        String result = resilientLlmService.callLlmWithResilience(
                () -> { callCount.incrementAndGet(); return "LLM_OK"; },
                () -> "FALLBACK"
        );

        assertEquals("FALLBACK", result);
        assertEquals(0, callCount.get(), "LLM must not be called when circuit OPEN");
    }

    @Test
    void testTimeoutFallback() {
        registry.circuitBreaker("llmService").reset();

        // Call mất 10s (vượt timeout 5s)
        String result = resilientLlmService.callLlmWithResilience(
                () -> { Thread.sleep(10_000); return "TOO_SLOW"; },
                () -> "TIMEOUT_FALLBACK"
        );

        // Phải trả fallback vì timeout
        assertEquals("TIMEOUT_FALLBACK", result);
    }
}
