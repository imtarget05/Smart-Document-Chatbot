package com.smartdocchat.security;

import com.smartdocchat.service.AuditLogService;
import com.smartdocchat.util.JwtTokenProvider;
import jakarta.servlet.http.Cookie;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.oauth2.core.oidc.user.OidcUser;
import org.springframework.security.web.authentication.AuthenticationSuccessHandler;
import org.springframework.stereotype.Component;

import java.io.IOException;
import java.util.Optional;

/**
 * Bridges a successful OIDC login into the existing JWT auth model: issues the
 * same httpOnly {@code jwt_token} cookie the local login issues and redirects
 * the browser back to the SPA. Frontend needs no changes — it reads the token
 * from the response body of /auth/login only for the local flow; for SSO the
 * cookie is authoritative and the redirect lands on the app root.
 */
@Component
@RequiredArgsConstructor
@Slf4j
public class OidcLoginSuccessHandler implements AuthenticationSuccessHandler {

    private static final String JWT_COOKIE_NAME = "jwt_token";
    private static final int JWT_COOKIE_MAX_AGE_SECONDS = 86400; // 24h

    private final JwtTokenProvider tokenProvider;
    private final com.smartdocchat.config.OidcProperties oidcProperties;
    private final AuditLogService auditLogService;

    @Override
    public void onAuthenticationSuccess(HttpServletRequest request, HttpServletResponse response,
                                        Authentication authentication) throws IOException {
        OidcUser oidcUser = (OidcUser) authentication.getPrincipal();
        String username = oidcUser.getName();
        String role = Optional.ofNullable(authentication.getAuthorities())
                .flatMap(auths -> auths.stream()
                        .map(a -> a.getAuthority())
                        .filter(a -> a.startsWith("ROLE_"))
                        .findFirst())
                .orElse("ROLE_USER");

        String token = tokenProvider.generateToken(username, role);

        Cookie jwtCookie = new Cookie(JWT_COOKIE_NAME, token);
        jwtCookie.setHttpOnly(true);
        jwtCookie.setPath("/");
        jwtCookie.setMaxAge(JWT_COOKIE_MAX_AGE_SECONDS);
        jwtCookie.setAttribute("SameSite", "Lax");
        jwtCookie.setSecure("https".equalsIgnoreCase(
                Optional.ofNullable(request.getHeader("X-Forwarded-Proto")).orElse("http")));
        response.addCookie(jwtCookie);

        auditLogService.record(username, "auth.login.sso", "user", username,
                request.getRemoteAddr(), "role=" + role);

        response.sendRedirect(oidcProperties.getPostLoginRedirect());
    }
}
