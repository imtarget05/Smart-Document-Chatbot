package com.smartdocchat.security;

import com.smartdocchat.config.OidcProperties;
import com.smartdocchat.service.AuditLogService;
import com.smartdocchat.util.JwtTokenProvider;
import jakarta.servlet.http.Cookie;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.mock.web.MockHttpServletRequest;
import org.springframework.mock.web.MockHttpServletResponse;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.oauth2.core.oidc.user.DefaultOidcUser;
import org.springframework.security.oauth2.core.oidc.user.OidcUser;

import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.ArgumentMatchers.contains;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.lenient;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class OidcLoginSuccessHandlerTest {

    @Mock private JwtTokenProvider tokenProvider;
    @Mock private AuditLogService auditLogService;
    @Mock private Authentication authentication;

    private OidcLoginSuccessHandler handler;

    private static final OidcUser OIDC_USER = new DefaultOidcUser(
            List.of(new SimpleGrantedAuthority("ROLE_ENGINEER")),
            new org.springframework.security.oauth2.core.oidc.OidcIdToken("t",
                    java.time.Instant.now(), java.time.Instant.now().plusSeconds(60),
                    Map.of("sub", "tuan", "preferred_username", "tuan")),
            new org.springframework.security.oauth2.core.oidc.OidcUserInfo(
                    Map.of("preferred_username", "tuan")),
            "preferred_username");

    @BeforeEach
    void setUp() {
        OidcProperties properties = new OidcProperties(true, "https://idp", "cid", "secret",
                "http://localhost:3000", "");
        handler = new OidcLoginSuccessHandler(tokenProvider, properties, auditLogService);
        lenient().when(authentication.getPrincipal()).thenReturn(OIDC_USER);
        lenient().when(authentication.getAuthorities())
                .thenAnswer(inv -> List.of(new SimpleGrantedAuthority("ROLE_ENGINEER")));
        lenient().when(tokenProvider.generateToken("tuan", "ROLE_ENGINEER")).thenReturn("jwt-abc");
    }

    @Test
    void issuesJwtCookieAndRedirectsToApp() throws Exception {
        MockHttpServletRequest request = new MockHttpServletRequest("GET", "/login/oauth2/code/oidc");
        MockHttpServletResponse response = new MockHttpServletResponse();

        handler.onAuthenticationSuccess(request, response, authentication);

        assertEquals("http://localhost:3000", response.getRedirectedUrl());

        Cookie jwtCookie = response.getCookie("jwt_token");
        assertNotNull(jwtCookie, "jwt_token cookie must be set for the SPA");
        assertEquals("jwt-abc", jwtCookie.getValue());
        assertTrue(jwtCookie.isHttpOnly());
        assertEquals("/", jwtCookie.getPath());
        assertEquals("Lax", jwtCookie.getAttribute("SameSite"));
    }

    @Test
    void ssoLoginIsAudited() throws Exception {
        MockHttpServletRequest request = new MockHttpServletRequest("GET", "/login/oauth2/code/oidc");
        request.setRemoteAddr("10.1.2.3");
        MockHttpServletResponse response = new MockHttpServletResponse();

        handler.onAuthenticationSuccess(request, response, authentication);

        verify(auditLogService).record(eq("tuan"), eq("auth.login.sso"), eq("user"), eq("tuan"),
                eq("10.1.2.3"), contains("ROLE_ENGINEER"));
    }

    @Test
    void defaultsToViewerRoleWhenNoRoleAuthority() throws Exception {
        when(authentication.getAuthorities()).thenReturn(List.of());
        when(tokenProvider.generateToken("tuan", "ROLE_USER")).thenReturn("jwt-viewer");

        MockHttpServletRequest request = new MockHttpServletRequest("GET", "/login/oauth2/code/oidc");
        MockHttpServletResponse response = new MockHttpServletResponse();

        handler.onAuthenticationSuccess(request, response, authentication);

        assertEquals("jwt-viewer", response.getCookie("jwt_token").getValue());
    }
}
