package com.smartdoc.agent.service;

import com.smartdoc.agent.resilience.AgentResilienceConfig;
import io.github.resilience4j.circuitbreaker.CallNotPermittedException;
import io.github.resilience4j.circuitbreaker.CircuitBreaker;
import io.github.resilience4j.timelimiter.TimeLimiter;
import io.github.resilience4j.timelimiter.TimeLimiterConfig;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.time.Duration;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeoutException;
import java.util.function.Supplier;

/**
 * Resilient LLM Service với Circuit Breaker + Time Limiter.
 *
 * Pattern sử dụng: Decorator + Fallback
 * - Bọc call LLM bằng circuit breaker
 * - Bọc call LLM bằng time limiter (timeout)
 * - Cung cấp fallback khi circuit OPEN hoặc timeout
 *
 * Đây là service mới, agent code cũ chưa dùng. Ngày 1 chỉ tạo skeleton
 * + fallback. Ngày sau sẽ wire vào AgentExecutor thật.
 */
@Service
public class ResilientLlmService {

    private static final Logger log = LoggerFactory.getLogger(ResilientLlmService.class);

    @Autowired
    private CircuitBreaker llmCircuitBreaker;

    @Autowired
    private TimeLimiter llmTimeLimiter;

    // Scheduled executor để implement timeout thủ công (vì TimeLimiter cần async)
    private final ScheduledExecutorService scheduler =
            Executors.newScheduledThreadPool(2);

    /**
     * Gọi LLM với circuit breaker + timeout + fallback.
     *
     * @param llmCall  Hàm gọi LLM thật (vd: callOpenAI, callOllama)
     * @param fallback Hàm fallback khi fail (vd: trả lời "service tạm thời không khả dụng")
     * @return Response từ LLM hoặc fallback
     */
    public String callLlmWithResilience(Supplier<String> llmCall, Supplier<String> fallback) {
        try {
            // Bước 1: Wrap bằng time limiter (timeout 5s)
            CompletableFuture<String> future = CompletableFuture.supplyAsync(llmCall);

            // Bước 2: Wrap bằng circuit breaker decorator
            Supplier<String> decorated = CircuitBreaker
                    .decorateSupplier(llmCircuitBreaker, () -> {
                        try {
                            return future.get(llmTimeLimiter.getTimeLimiterConfig()
                                    .getTimeoutDuration().toMillis(), java.util.concurrent.TimeUnit.MILLISECONDS);
                        } catch (TimeoutException e) {
                            future.cancel(true);
                            throw new RuntimeException("LLM call timeout", e);
                        } catch (Exception e) {
                            throw new RuntimeException("LLM call failed", e);
                        }
                    });

            return decorated.get();
        } catch (CallNotPermittedException e) {
            // Circuit breaker OPEN → trả fallback ngay
            log.warn("[ResilientLlm] Circuit OPEN, returning fallback. Reason: {}",
                    e.getMessage());
            return fallback.get();
        } catch (Exception e) {
            log.error("[ResilientLlm] LLM call failed: {}", e.getMessage());
            return fallback.get();
        }
    }

    /**
     * Lấy trạng thái hiện tại của circuit breaker (để hiển thị health check).
     */
    public CircuitBreaker.State getCircuitState() {
        return llmCircuitBreaker.getState();
    }

    /**
     * Lấy metrics của circuit breaker.
     */
    public CircuitBreaker.Metrics getMetrics() {
        return llmCircuitBreaker.getMetrics();
    }
}
