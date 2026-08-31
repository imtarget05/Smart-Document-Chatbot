package com.smartdocchat.controller;

import com.smartdocchat.util.JwtTokenProvider;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.oauth2.core.oidc.user.OidcUser;
import org.springframework.web.bind.annotation.*;

import java.util.HashMap;
import java.util.Map;

/**
 * OAuth2/OIDC controller for corporate SSO integration.
 * Provides endpoints for login URL discovery, success/failure handling,
 * and token retrieval after OIDC redirect.
 */
@RestController
@RequestMapping("/auth/oauth2")
@RequiredArgsConstructor
@Slf4j
public class OAuth2Controller {

    private final JwtTokenProvider jwtTokenProvider;

    /**
     * Get OAuth2 login URL for frontend redirect.
     * Returns whether OAuth2 is configured and the login URL.
     */
    @GetMapping("/login-url")
    public ResponseEntity<Map<String, String>> getLoginUrl(
            @org.springframework.beans.factory.annotation.Value("${oauth2.client-id:}") String clientId,
            @org.springframework.beans.factory.annotation.Value("${oauth2.issuer-uri:}") String issuerUri) {
        Map<String, String> response = new HashMap<>();
        if (clientId.isBlank() || issuerUri.isBlank()) {
            response.put("enabled", "false");
            response.put("message", "OAuth2/OIDC not configured");
        } else {
            response.put("enabled", "true");
            response.put("loginUrl", "/api/oauth2/authorization/oidc");
            response.put("provider", "Corporate SSO");
        }
        return ResponseEntity.ok(response);
    }

    /**
     * Handle OAuth2 login success - return internal JWT.
     * Called by frontend after OAuth2 redirect completes.
     */
    @GetMapping("/success")
    public ResponseEntity<Map<String, Object>> oauth2Success(
            @AuthenticationPrincipal OidcUser principal) {

        if (principal == null) {
            return ResponseEntity.status(401).body(Map.of("error", "Not authenticated"));
        }

        // Get internal JWT from claims (set by OAuth2UserService)
        String internalJwt = (String) principal.getAttributes().get("internal_jwt");

        if (internalJwt == null) {
            // Fallback: generate token from principal attributes
            internalJwt = jwtTokenProvider.generateTokenFromPrincipal(principal);
        }

        Map<String, Object> response = new HashMap<>();
        response.put("token", internalJwt);
        response.put("username", principal.getEmail());
        response.put("fullName", principal.getFullName());
        response.put("email", principal.getEmail());
        response.put("authType", "OAUTH2");

        return ResponseEntity.ok(response);
    }

    /**
     * Handle OAuth2 login failure.
     */
    @GetMapping("/failure")
    public ResponseEntity<Map<String, String>> oauth2Failure(
            @RequestParam(required = false) String error) {
        return ResponseEntity.status(401)
                .body(Map.of("error", error != null ? error : "oauth2_authentication_failed"));
    }
}
