package com.smartdocchat.config;

import com.smartdocchat.util.JwtTokenProvider;
import jakarta.servlet.FilterChain;
import jakarta.servlet.http.Cookie;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class JwtAuthenticationFilterTest {

    @Mock private JwtTokenProvider tokenProvider;
    @Mock private HttpServletRequest request;
    @Mock private HttpServletResponse response;
    @Mock private FilterChain filterChain;

    private JwtAuthenticationFilter filter;

    @AfterEach
    void tearDown() {
        SecurityContextHolder.clearContext();
    }

    @Test
    void authenticatesFromBearerHeader() throws Exception {
        filter = new JwtAuthenticationFilter(tokenProvider);
        when(request.getHeader("Authorization")).thenReturn("Bearer valid.token");
        when(tokenProvider.validateToken("valid.token")).thenReturn(true);
        when(tokenProvider.getUsernameFromToken("valid.token")).thenReturn("alice");
        when(tokenProvider.getRoleFromToken("valid.token")).thenReturn("ROLE_USER");

        filter.doFilterInternal(request, response, filterChain);

        Authentication auth = SecurityContextHolder.getContext().getAuthentication();
        assertEquals("alice", auth.getPrincipal());
        assertTrue(auth.getAuthorities().stream().anyMatch(a -> a.getAuthority().equals("ROLE_USER")));
        verify(request).setAttribute("username", "alice");
        verify(filterChain).doFilter(request, response);
    }

    @Test
    void fallsBackToCookieWhenNoHeader() throws Exception {
        filter = new JwtAuthenticationFilter(tokenProvider);
        when(request.getHeader("Authorization")).thenReturn(null);
        when(request.getCookies()).thenReturn(new Cookie[]{new Cookie("jwt_token", "cookie.token")});
        when(tokenProvider.validateToken("cookie.token")).thenReturn(true);
        when(tokenProvider.getUsernameFromToken("cookie.token")).thenReturn("bob");
        when(tokenProvider.getRoleFromToken("cookie.token")).thenReturn("ROLE_ADMIN");

        filter.doFilterInternal(request, response, filterChain);

        Authentication auth = SecurityContextHolder.getContext().getAuthentication();
        assertEquals("bob", auth.getPrincipal());
    }

    @Test
    void ignoresInvalidOrMissingTokens() throws Exception {
        filter = new JwtAuthenticationFilter(tokenProvider);
        when(request.getHeader("Authorization")).thenReturn(null);
        when(request.getCookies()).thenReturn(null);

        filter.doFilterInternal(request, response, filterChain);

        assertNull(SecurityContextHolder.getContext().getAuthentication());
    }

    @Test
    void swallowsProviderExceptionsAndContinuesChain() throws Exception {
        filter = new JwtAuthenticationFilter(tokenProvider);
        when(request.getHeader("Authorization")).thenReturn("Bearer bad.token");
        when(tokenProvider.validateToken("bad.token")).thenThrow(new RuntimeException("expired"));

        filter.doFilterInternal(request, response, filterChain);

        assertNull(SecurityContextHolder.getContext().getAuthentication());
        verify(filterChain).doFilter(request, response);
    }
}