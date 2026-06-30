package com.smartdocchat.config;

import io.github.bucket4j.Bandwidth;
import io.github.bucket4j.Bucket;
import io.github.bucket4j.Refill;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.http.HttpStatus;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;
import java.time.Duration;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Tiered rate-limiting filter (Bucket4j token bucket, in-process).
 *
 * <p>Three tiers, applied only to the paths that matter:
 * <ol>
 *   <li><b>LLM tier</b> – {@code /chat/ask}, {@code /chat/ask-stream},
 *       {@code /agent/**}: 10 req/min per authenticated user (or IP as fallback).
 *       LLM calls are expensive — tight limit to protect cost and latency.</li>
 *   <li><b>Upload tier</b> – {@code /documents/upload}: 20 req/min per user/IP.
 *       OCR / embedding pipeline is also heavy; more generous than LLM.</li>
 *   <li><b>Auth tier</b> – {@code /auth/login}, {@code /auth/register}:
 *       5 req/min per IP. Brute-force / credential-stuffing protection.</li>
 * </ol>
 *
 * <p>Key design decisions:
 * <ul>
 *   <li>Authenticated users are keyed by username; anonymous by IP.
 *       This prevents a single bad actor from exhausting another user's quota.</li>
 *   <li>Buckets are stored in an unbounded {@link ConcurrentHashMap}. In a
 *       multi-replica deployment, replace with a Redis-backed Bucket4j
 *       {@code ProxyManager} to share state across instances.</li>
 * </ul>
 */
@Component
public class RateLimitingFilter extends OncePerRequestFilter {

    // Per-user/IP bucket maps (one map per tier)
    private final Map<String, Bucket> llmBuckets    = new ConcurrentHashMap<>();
    private final Map<String, Bucket> uploadBuckets = new ConcurrentHashMap<>();
    private final Map<String, Bucket> authBuckets   = new ConcurrentHashMap<>();

    // ── Bucket factories ──────────────────────────────────────────────────

    /** LLM tier: 10 requests / 60 s, refilling continuously. */
    private Bucket createLlmBucket() {
        return Bucket.builder()
                .addLimit(Bandwidth.classic(10, Refill.greedy(10, Duration.ofMinutes(1))))
                .build();
    }

    /** Upload tier: 20 requests / 60 s. */
    private Bucket createUploadBucket() {
        return Bucket.builder()
                .addLimit(Bandwidth.classic(20, Refill.greedy(20, Duration.ofMinutes(1))))
                .build();
    }

    /** Auth tier: 5 requests / 60 s (brute-force guard). */
    private Bucket createAuthBucket() {
        return Bucket.builder()
                .addLimit(Bandwidth.classic(5, Refill.greedy(5, Duration.ofMinutes(1))))
                .build();
    }

    // ── Filter logic ──────────────────────────────────────────────────────

    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response,
                                    FilterChain filterChain) throws ServletException, IOException {
        String path = request.getRequestURI();

        if (isLlmPath(path)) {
            String key = resolveKey(request);
            if (!llmBuckets.computeIfAbsent(key, k -> createLlmBucket()).tryConsume(1)) {
                rejectRateLimited(response, request.getRemoteAddr(), path, 10, "LLM");
                return;
            }
        } else if (isUploadPath(path)) {
            String key = resolveKey(request);
            if (!uploadBuckets.computeIfAbsent(key, k -> createUploadBucket()).tryConsume(1)) {
                rejectRateLimited(response, request.getRemoteAddr(), path, 20, "upload");
                return;
            }
        } else if (isAuthPath(path)) {
            // Auth always keyed by IP regardless of authentication state
            String ip = request.getRemoteAddr();
            if (!authBuckets.computeIfAbsent(ip, k -> createAuthBucket()).tryConsume(1)) {
                rejectRateLimited(response, ip, path, 5, "auth");
                return;
            }
        }

        filterChain.doFilter(request, response);
    }

    // ── Path predicates ───────────────────────────────────────────────────

    private boolean isLlmPath(String path) {
        return path.contains("/chat/ask")
                || path.contains("/chat/ask-stream")
                || path.contains("/agent/");
    }

    private boolean isUploadPath(String path) {
        return path.contains("/documents/upload");
    }

    private boolean isAuthPath(String path) {
        return path.contains("/auth/login") || path.contains("/auth/register");
    }

    // ── Key resolution ────────────────────────────────────────────────────

    /**
     * Return the authenticated username when available, otherwise the client IP.
     * Using username prevents one IP from exhausting another user's bucket.
     */
    private String resolveKey(HttpServletRequest request) {
        Authentication auth = SecurityContextHolder.getContext().getAuthentication();
        if (auth != null && auth.isAuthenticated() && auth.getPrincipal() instanceof String principal
                && !"anonymousUser".equals(principal)) {
            return "user:" + principal;
        }
        return "ip:" + request.getRemoteAddr();
    }

    // ── Response helper ───────────────────────────────────────────────────

    private void rejectRateLimited(HttpServletResponse response,
                                   String identifier, String path,
                                   int limit, String tier) throws IOException {
        logger.warn(String.format(
                "Rate limit exceeded [tier=%s limit=%d/min] identifier=%s path=%s",
                tier, limit, identifier, path));
        response.setStatus(HttpStatus.TOO_MANY_REQUESTS.value());
        response.setHeader("Retry-After", "60");
        response.setContentType("application/json");
        response.getWriter().write(
                String.format("{\"error\": \"Too many requests. You have exceeded the %s rate limit (%d/min). "
                        + "Please wait before retrying.\"}", tier, limit));
    }
}
