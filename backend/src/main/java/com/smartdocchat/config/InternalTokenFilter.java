package com.smartdocchat.config;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;

/**
 * Guards non-public actuator endpoints (e.g. /actuator/prometheus) with an
 * internal service token sent via {@code X-Internal-Token}. Fails closed: an
 * unconfigured or mismatched token yields 401.
 */
@Component
@Slf4j
public class InternalTokenFilter extends OncePerRequestFilter {

    private static final String PROTECTED_PATH = "/actuator/prometheus";

    private final String internalToken;

    public InternalTokenFilter(@Value("${security.internal-token:}") String internalToken) {
        this.internalToken = internalToken;
    }

    @Override
    protected boolean shouldNotFilter(HttpServletRequest request) {
        String path = request.getRequestURI().substring(request.getContextPath().length());
        return !path.equals(PROTECTED_PATH);
    }

    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response,
                                    FilterChain filterChain) throws ServletException, IOException {
        String provided = request.getHeader("X-Internal-Token");
        boolean valid = internalToken != null && !internalToken.isBlank()
                && internalToken.equals(provided);
        if (!valid) {
            log.warn("Rejected internal-token request to {}", request.getRequestURI());
            response.setStatus(HttpServletResponse.SC_UNAUTHORIZED);
            return;
        }
        filterChain.doFilter(request, response);
    }
}