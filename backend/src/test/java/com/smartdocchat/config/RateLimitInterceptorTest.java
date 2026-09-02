package com.smartdocchat.config;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.mock.web.MockHttpServletRequest;
import org.springframework.mock.web.MockHttpServletResponse;

import java.time.Duration;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyInt;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.lenient;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class RateLimitInterceptorTest {

    @Mock
    private RateLimitStore rateLimitStore;

    private RateLimitInterceptor interceptor;

    @BeforeEach
    void setUp() throws Exception {
        // Default: Redis allows everything; individual tests override per key.
        lenient().when(rateLimitStore.isAllowed(anyString(), anyInt(), any(Duration.class))).thenReturn(true);
        lenient().when(rateLimitStore.getRemaining(anyString(), anyInt(), any(Duration.class))).thenReturn(99L);
        interceptor = new RateLimitInterceptor(rateLimitStore);
        setField("enabled", true);
        setField("chatPerMinute", 2);
        setField("uploadPerMinute", 1);
        setField("authPerMinute", 1);
        setField("windowSeconds", 60);
    }

    private void setField(String name, Object value) throws Exception {
        var field = RateLimitInterceptor.class.getDeclaredField(name);
        field.setAccessible(true);
        field.set(interceptor, value);
    }

    private MockHttpServletRequest request(String method, String path, String remoteAddr) {
        MockHttpServletRequest req = new MockHttpServletRequest(method, path);
        req.setRequestURI(path);
        req.setRemoteAddr(remoteAddr);
        return req;
    }

    private MockHttpServletResponse response() {
        return new MockHttpServletResponse();
    }

    @Test
    void allowsTrafficBelowTheLimitAndBlocksAboveIt() throws Exception {
        when(rateLimitStore.isAllowed(eq("chat:u:1.2.3.4"), eq(2), any(Duration.class)))
                .thenReturn(true, true, false);

        assertTrue(interceptor.preHandle(request("POST", "/api/chat/ask", "1.2.3.4"), response(), new Object()));
        assertTrue(interceptor.preHandle(request("POST", "/api/chat/ask", "1.2.3.4"), response(), new Object()));

        MockHttpServletResponse blocked = response();
        assertFalse(interceptor.preHandle(request("POST", "/api/chat/ask", "1.2.3.4"), blocked, new Object()));
        assertEquals(429, blocked.getStatus());
        long retryAfter = Long.parseLong(blocked.getHeader(RateLimitInterceptor.RETRY_AFTER_HEADER));
        assertTrue(retryAfter >= 1 && retryAfter <= 60, "retry-after should be a sane second count");
    }

    @Test
    void exposesRemainingHeaderOnAllowedRequests() throws Exception {
        when(rateLimitStore.getRemaining(eq("chat:u:1.2.3.4"), eq(2), any(Duration.class))).thenReturn(1L);

        MockHttpServletResponse resp = response();
        assertTrue(interceptor.preHandle(request("POST", "/api/chat/ask", "1.2.3.4"), resp, new Object()));
        assertEquals("1", resp.getHeader(RateLimitInterceptor.REMAINING_HEADER));
    }

    @Test
    void unauthenticatedChatIsLimitedPerIp() throws Exception {
        when(rateLimitStore.isAllowed(eq("chat:u:9.9.9.9"), eq(2), any(Duration.class)))
                .thenReturn(true, true, false);

        assertTrue(interceptor.preHandle(request("POST", "/api/chat/ask", "9.9.9.9"), response(), new Object()));
        assertTrue(interceptor.preHandle(request("POST", "/api/chat/ask", "9.9.9.9"), response(), new Object()));
        assertFalse(interceptor.preHandle(request("POST", "/api/chat/ask", "9.9.9.9"),
                new MockHttpServletResponse(), new Object()));
    }

    @Test
    void authEndpointsAreKeyedByForwardedIp() throws Exception {
        when(rateLimitStore.isAllowed(eq("auth:ip:203.0.113.7"), eq(1), any(Duration.class)))
                .thenReturn(true, false);

        MockHttpServletRequest first = request("POST", "/api/auth/login", "10.0.0.1");
        first.addHeader("X-Forwarded-For", "203.0.113.7, 70.41.3.18");
        assertTrue(interceptor.preHandle(first, response(), new Object()));

        // Same forwarded client, second attempt -> blocked.
        MockHttpServletRequest second = request("POST", "/api/auth/register", "10.0.0.1");
        second.addHeader("X-Forwarded-For", "203.0.113.7");
        MockHttpServletResponse blocked = response();
        assertFalse(interceptor.preHandle(second, blocked, new Object()));
        assertEquals(429, blocked.getStatus());

        // A different client IP is unaffected.
        MockHttpServletRequest other = request("POST", "/api/auth/login", "10.0.0.2");
        other.addHeader("X-Forwarded-For", "198.51.100.2");
        assertTrue(interceptor.preHandle(other, response(), new Object()));
    }

    @Test
    void unrelatedPathsAreNotRateLimited() throws Exception {
        for (int i = 0; i < 5; i++) {
            assertTrue(interceptor.preHandle(request("GET", "/api/csrf", "2.2.2.2"), response(), new Object()));
        }
    }

    @Test
    void disabledInterceptorLetsEverythingThrough() throws Exception {
        setField("enabled", false);
        for (int i = 0; i < 5; i++) {
            assertTrue(interceptor.preHandle(request("POST", "/api/auth/login", "3.3.3.3"), response(), new Object()));
        }
        MockHttpServletResponse resp = response();
        assertNull(resp.getHeader(RateLimitInterceptor.RETRY_AFTER_HEADER));
    }

    @Test
    void usesInMemoryFallbackWhenRedisIsUnavailable() throws Exception {
        // When Redis is absent (rateLimitStore == null) the interceptor installs
        // an in-memory store instead of failing closed, so throttled paths keep
        // working (per-instance budget) rather than rejecting with 503.
        RateLimitInterceptor noStore = new RateLimitInterceptor(null);
        setField("enabled", true, noStore);
        setField("chatPerMinute", 2, noStore);
        setField("windowSeconds", 30, noStore);

        // First two chat requests are allowed by the in-memory budget (capacity 2)...
        assertTrue(noStore.preHandle(request("POST", "/api/chat/ask", "1.2.3.4"), response(), new Object()));
        assertTrue(noStore.preHandle(request("POST", "/api/chat/ask", "1.2.3.4"), response(), new Object()));

        // ...third is rate limited (429), not a 503 outage.
        MockHttpServletResponse blocked = response();
        assertFalse(noStore.preHandle(request("POST", "/api/chat/ask", "1.2.3.4"), blocked, new Object()));
        assertEquals(429, blocked.getStatus());
        assertEquals("30", blocked.getHeader(RateLimitInterceptor.RETRY_AFTER_HEADER));
    }

    private void setField(String name, Object value, RateLimitInterceptor target) throws Exception {
        var field = RateLimitInterceptor.class.getDeclaredField(name);
        field.setAccessible(true);
        field.set(target, value);
    }
}
