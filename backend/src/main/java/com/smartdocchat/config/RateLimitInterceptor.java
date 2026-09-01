package com.smartdocchat.config;

import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.stereotype.Component;
import org.springframework.web.servlet.HandlerInterceptor;

import java.time.Duration;
import java.util.Optional;

@Component
@Slf4j
public class RateLimitInterceptor implements HandlerInterceptor {

    static final String RETRY_AFTER_HEADER = "Retry-After";
    static final String REMAINING_HEADER = "X-RateLimit-Remaining";

    private final RedisRateLimitStore rateLimitStore;

    @Value("${ratelimit.enabled:true}")
    private boolean enabled;
    @Value("${ratelimit.chat-per-minute:30}")
    private int chatPerMinute;
    @Value("${ratelimit.upload-per-minute:10}")
    private int uploadPerMinute;
    @Value("${ratelimit.auth-per-minute:10}")
    private int authPerMinute;
    @Value("${ratelimit.window-seconds:60}")
    private int windowSeconds;

    @Autowired
    public RateLimitInterceptor(@Autowired(required = false) RedisRateLimitStore rateLimitStore) {
        this.rateLimitStore = rateLimitStore;
        if (rateLimitStore == null) {
            log.warn("Redis not available — rate limiting disabled (all requests allowed)");
        }
    }

    @Override
    public boolean preHandle(HttpServletRequest request, HttpServletResponse response, Object handler)
            throws Exception {
        if (!enabled || rateLimitStore == null) return true;
        String path = request.getRequestURI();
        String scope = scopeFor(path);
        if (scope == null) return true;

        String identity = switch (scope) {
            case "chat", "upload" -> "u:" + currentUser().orElse(clientIp(request));
            default -> "ip:" + clientIp(request);
        };
        String key = scope + ":" + identity;
        int capacity = capacityFor(scope);
        Duration window = Duration.ofSeconds(windowSeconds);

        boolean allowed = rateLimitStore.isAllowed(key, capacity, window);
        long remaining = rateLimitStore.getRemaining(key, capacity, window);

        response.setHeader(REMAINING_HEADER, String.valueOf(remaining));

        if (allowed) return true;

        long waitSeconds = windowSeconds;
        log.warn("Rate limit exceeded for {} {} (retry after {}s)", request.getMethod(), path, waitSeconds);
        response.setStatus(429);
        response.setHeader(RETRY_AFTER_HEADER, String.valueOf(waitSeconds));
        response.setContentType("application/json");
        response.getWriter().write("{\"error\":\"rate_limit_exceeded\",\"message\":"
                + "\"Too many requests. Please slow down.\",\"retry_after\":" + waitSeconds + "}");
        return false;
    }

    private int capacityFor(String scope) {
        return switch (scope) {
            case "chat" -> chatPerMinute;
            case "upload" -> uploadPerMinute;
            default -> authPerMinute;
        };
    }

    private String scopeFor(String path) {
        if (path == null) return null;
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

    private Optional<String> currentUser() {
        Authentication auth = SecurityContextHolder.getContext().getAuthentication();
        if (auth != null && auth.isAuthenticated() && auth.getName() != null
                && !"anonymousUser".equals(auth.getName())) {
            return Optional.of(auth.getName());
        }
        return Optional.empty();
    }

    private String clientIp(HttpServletRequest request) {
        String forwarded = request.getHeader("X-Forwarded-For");
        if (forwarded != null && !forwarded.isBlank()) {
            int comma = forwarded.indexOf(',');
            return (comma > 0 ? forwarded.substring(0, comma) : forwarded).trim();
        }
        return request.getRemoteAddr() != null ? request.getRemoteAddr() : "unknown";
    }
}
