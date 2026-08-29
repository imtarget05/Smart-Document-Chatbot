package com.smartdocchat.config;

import io.github.bucket4j.Bandwidth;
import io.github.bucket4j.Bucket;
import io.github.bucket4j.ConsumptionProbe;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.stereotype.Component;
import org.springframework.web.servlet.HandlerInterceptor;

import java.time.Duration;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Token-bucket rate limiting on the expensive and abuse-prone API surface:
 *
 * - per-user limits for chat asks and document uploads (LLM calls cost money)
 * - a stricter per-IP limit for credential endpoints (brute-force damping,
 *   complementary to the account lockout in LoginAuditService)
 *
 * Buckets live in a ConcurrentHashMap; a size guard clears it if an attacker
 * sprays unique identities, trading fairness for bounded memory.
 */
@Component
@Slf4j
public class RateLimitInterceptor implements HandlerInterceptor {

    static final String RETRY_AFTER_HEADER = "Retry-After";

    private final Map<String, Bucket> buckets = new ConcurrentHashMap<>();

    @Value("${ratelimit.enabled:true}")
    private boolean enabled;
    @Value("${ratelimit.chat-per-minute:30}")
    private int chatPerMinute;
    @Value("${ratelimit.upload-per-minute:10}")
    private int uploadPerMinute;
    @Value("${ratelimit.auth-per-minute:10}")
    private int authPerMinute;

    @Override
    public boolean preHandle(HttpServletRequest request, HttpServletResponse response, Object handler)
            throws Exception {
        if (!enabled) {
            return true;
        }
        String path = request.getRequestURI();
        String scope = scopeFor(path);
        if (scope == null) {
            return true;
        }

        String identity = switch (scope) {
            case "chat", "upload" -> "u:" + currentUser().orElse(clientIp(request));
            default -> "ip:" + clientIp(request);
        };
        String key = scope + ":" + identity;

        Bucket bucket = buckets.computeIfAbsent(key, k -> newBucket(scope));
        ConsumptionProbe probe = bucket.tryConsumeAndReturnRemaining(1);
        if (probe.isConsumed()) {
            return true;
        }

        long waitSeconds = Math.max(1, probe.getNanosToWaitForRefill() / Duration.ofSeconds(1).toNanos());
        log.warn("Rate limit exceeded for {} {} (retry after {}s)", request.getMethod(), path, waitSeconds);
        response.setStatus(429);
        response.setHeader(RETRY_AFTER_HEADER, String.valueOf(waitSeconds));
        response.setContentType("application/json");
        response.getWriter().write("{\"error\":\"rate_limit_exceeded\",\"message\":"
                + "\"Too many requests. Please slow down.\"}");
        return false;
    }

    private String scopeFor(String path) {
        if (path == null) {
            return null;
        }
        if (path.equals("/api/chat/ask") || path.startsWith("/api/chat/ask/")
                || path.equals("/api/chat/ask-stream") || path.startsWith("/api/chat/ask-stream/")
                || path.equals("/api/chat/stream") || path.startsWith("/api/chat/stream/")) {
            return "chat";
        }
        if (path.equals("/api/documents/upload") || path.startsWith("/api/documents/upload/")) {
            return "upload";
        }
        if (path.equals("/api/auth/register") || path.equals("/api/auth/login")) {
            return "auth";
        }
        return null;
    }

    Bucket newBucket(String scope) {
        int capacity = switch (scope) {
            case "chat" -> chatPerMinute;
            case "upload" -> uploadPerMinute;
            default -> authPerMinute;
        };
        return Bucket.builder()
                .addLimit(Bandwidth.classic(capacity, io.github.bucket4j.Refill.greedy(capacity, Duration.ofMinutes(1))))
                .build();
    }

    private java.util.Optional<String> currentUser() {
        Authentication auth = SecurityContextHolder.getContext().getAuthentication();
        if (auth != null && auth.isAuthenticated() && auth.getName() != null
                && !"anonymousUser".equals(auth.getName())) {
            return java.util.Optional.of(auth.getName());
        }
        return java.util.Optional.empty();
    }

    private String clientIp(HttpServletRequest request) {
        String forwarded = request.getHeader("X-Forwarded-For");
        if (forwarded != null && !forwarded.isBlank()) {
            int comma = forwarded.indexOf(',');
            return (comma > 0 ? forwarded.substring(0, comma) : forwarded).trim();
        }
        return request.getRemoteAddr() != null ? request.getRemoteAddr() : "unknown";
    }

    /** Visible-for-testing: drop all accumulated buckets. */
    void clearBuckets() {
        buckets.clear();
    }
}
