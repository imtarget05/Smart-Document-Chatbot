package com.smartdoc.agent.resilience;

import io.github.resilience4j.circuitbreaker.CircuitBreaker;
import io.github.resilience4j.circuitbreaker.CircuitBreakerRegistry;
import io.github.resilience4j.timelimiter.TimeLimiter;
import io.github.resilience4j.timelimiter.TimeLimiterConfig;
import io.github.resilience4j.timelimiter.TimeLimiterRegistry;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

import java.time.Duration;

/**
 * Cấu hình Circuit Breaker + Time Limiter cho Agent service.
 *
 * Giải thích 3 trạng thái circuit breaker:
 * - CLOSED: bình thường, request đi qua. Nếu failure rate > 50% trong 10 request gần nhất
 *   thì chuyển sang OPEN.
 * - OPEN: từ chối tất cả request, trả lỗi ngay lập tức (không gọi service đang chết).
 *   Sau 30s chuyển sang HALF_OPEN.
 * - HALF_OPEN: cho phép 3 request test. Nếu thành công → CLOSED. Nếu fail → OPEN lại.
 *
 * Time Limiter: giới hạn thời gian tối đa cho 1 call. Nếu quá 5s sẽ cancel
 * để tránh treo cả request lifecycle.
 */
@Configuration
public class AgentResilienceConfig {

    public static final String LLM_CIRCUIT_BREAKER = "llmService";
    public static final String LLM_TIME_LIMITER = "llmService";

    /**
     * Bean: CircuitBreakerRegistry quản lý tất cả circuit breaker.
     * Có thể lấy bất kỳ circuit breaker nào qua tên: registry.circuitBreaker("llmService")
     */
    @Bean
    public CircuitBreakerRegistry circuitBreakerRegistry() {
        io.github.resilience4j.circuitbreaker.CircuitBreakerConfig config = io.github.resilience4j.circuitbreaker.CircuitBreakerConfig.custom()
                // Failure rate threshold: nếu > 50% request fail trong window → mở circuit
                .failureRateThreshold(50.0f)
                // Sliding window: đếm trong 10 request gần nhất
                .slidingWindowType(io.github.resilience4j.circuitbreaker.CircuitBreakerConfig.SlidingWindowType.COUNT_BASED)
                .slidingWindowSize(10)
                // Số request tối thiểu trước khi tính failure rate (tránh false alarm)
                .minimumNumberOfCalls(5)
                // Slow call threshold: nếu call > 3s coi như fail
                .slowCallRateThreshold(50.0f)
                .slowCallDurationThreshold(Duration.ofSeconds(3))
                // Sau khi OPEN, đợi 30s trước khi test lại
                .waitDurationInOpenState(Duration.ofSeconds(30))
                // Cho phép 3 call test trong HALF_OPEN
                .permittedNumberOfCallsInHalfOpenState(3)
                // Tự động chuyển từ OPEN → HALF_OPEN
                .automaticTransitionFromOpenToHalfOpenEnabled(true)
                // Ghi log mỗi state transition
                .recordExceptions(Exception.class)
                .build();

        CircuitBreakerRegistry registry = CircuitBreakerRegistry.of(config);

        // Đăng ký event listener để log khi circuit breaker thay đổi trạng thái
        registry.getEventPublisher().onEntryAdded(event ->
                event.getAddedEntry().getEventPublisher().onStateTransition(e ->
                        System.out.println("[CircuitBreaker] " + e.getStateTransition().getFromState()
                                + " → " + e.getStateTransition().getToState())));

        return registry;
    }

    /**
     * Bean: TimeLimiterRegistry giới hạn thời gian call.
     * 1 call LLM tối đa 5 giây, quá thời gian sẽ bị cancel.
     */
    @Bean
    public TimeLimiterRegistry timeLimiterRegistry() {
        TimeLimiterConfig config = TimeLimiterConfig.custom()
                .timeoutDuration(Duration.ofSeconds(5))
                .cancelRunningFuture(true)
                .build();

        return TimeLimiterRegistry.of(config);
    }

    /**
     * Bean: CircuitBreaker cho LLM service. Có thể inject vào service qua @Autowired.
     */
    @Bean
    public CircuitBreaker llmCircuitBreaker(CircuitBreakerRegistry registry) {
        return registry.circuitBreaker(LLM_CIRCUIT_BREAKER);
    }

    /**
     * Bean: TimeLimiter cho LLM service.
     */
    @Bean
    public TimeLimiter llmTimeLimiter(TimeLimiterRegistry registry) {
        return registry.timeLimiter(LLM_TIME_LIMITER);
    }
}
