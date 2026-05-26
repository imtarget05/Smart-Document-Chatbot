package com.smartdocchat.config;

import io.github.bucket4j.Bandwidth;
import io.github.bucket4j.Bucket;
import io.github.bucket4j.Refill;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;
import java.time.Duration;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

@Component
public class RateLimitingFilter extends OncePerRequestFilter {

    // Thread-safe map to store token buckets associated with client IP addresses
    private final Map<String, Bucket> cache = new ConcurrentHashMap<>();

    private Bucket createNewBucket() {
        // Allows up to 30 requests per minute, refilling 30 tokens every minute
        return Bucket.builder()
                .addLimit(Bandwidth.classic(30, Refill.intervally(30, Duration.ofMinutes(1))))
                .build();
    }

    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response, FilterChain filterChain)
            throws ServletException, IOException {
        
        String path = request.getRequestURI();
        
        // Rate-limit chat and document modification operations to prevent excessive resource utilization
        if (path.contains("/chat/ask") || path.contains("/chat/ask-stream")
                || path.contains("/documents/upload") || path.contains("/auth/login")
                || path.contains("/auth/register")) {
            String ip = request.getRemoteAddr();
            Bucket bucket = cache.computeIfAbsent(ip, k -> createNewBucket());

            if (!bucket.tryConsume(1)) {
                logWarnRateLimitExceeded(ip, path);
                response.setStatus(HttpStatus.TOO_MANY_REQUESTS.value());
                response.setContentType("application/json");
                response.getWriter().write("{\"error\": \"Too many requests. Please wait a moment before trying again.\"}");
                return;
            }
        }

        filterChain.doFilter(request, response);
    }

    private void logWarnRateLimitExceeded(String ip, String path) {
        // Custom simple warn logging
        logger.warn(String.format("Rate limit exceeded for IP: %s on path: %s", ip, path));
    }
}
