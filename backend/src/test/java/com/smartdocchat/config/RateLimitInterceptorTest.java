package com.smartdocchat.config;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.mock.web.MockHttpServletRequest;
import org.springframework.mock.web.MockHttpServletResponse;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

class RateLimitInterceptorTest {

    private RateLimitInterceptor interceptor;

    @BeforeEach
    void setUp() throws Exception {
        interceptor = new RateLimitInterceptor();
        setField("enabled", true);
        setField("chatPerMinute", 2);
        setField("uploadPerMinute", 1);
        setField("authPerMinute", 1);
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
        assertTrue(interceptor.preHandle(request("POST", "/api/chat/ask", "1.2.3.4"), response(), new Object()));
        assertTrue(interceptor.preHandle(request("POST", "/api/chat/ask", "1.2.3.4"), response(), new Object()));

        MockHttpServletResponse blocked = response();
        assertFalse(interceptor.preHandle(request("POST", "/api/chat/ask", "1.2.3.4"), blocked, new Object()));
        assertEquals(429, blocked.getStatus());
        long retryAfter = Long.parseLong(blocked.getHeader(RateLimitInterceptor.RETRY_AFTER_HEADER));
        assertTrue(retryAfter >= 1 && retryAfter <= 60, "retry-after should be a sane second count");
    }

    @Test
    void unauthenticatedChatIsLimitedPerIp() throws Exception {
        // chatPerMinute=2: two anonymous asks from one IP pass, the third is blocked.
        assertTrue(interceptor.preHandle(request("POST", "/api/chat/ask", "9.9.9.9"), response(), new Object()));
        assertTrue(interceptor.preHandle(request("POST", "/api/chat/ask", "9.9.9.9"), response(), new Object()));
        assertFalse(interceptor.preHandle(request("POST", "/api/chat/ask", "9.9.9.9"),
                new MockHttpServletResponse(), new Object()));
    }

    @Test
    void authEndpointsAreKeyedByForwardedIp() throws Exception {
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
}
