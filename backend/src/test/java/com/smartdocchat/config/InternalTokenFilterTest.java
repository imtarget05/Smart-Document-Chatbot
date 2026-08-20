package com.smartdocchat.config;

import jakarta.servlet.FilterChain;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.junit.jupiter.api.Test;
import org.springframework.mock.web.MockHttpServletRequest;
import org.springframework.mock.web.MockHttpServletResponse;
import org.springframework.web.util.ContentCachingResponseWrapper;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;

class InternalTokenFilterTest {

    private InternalTokenFilter newFilter(String configuredToken) {
        return new InternalTokenFilter(configuredToken);
    }

    @Test
    void rejectsActuatorRequestsWithoutToken() throws Exception {
        InternalTokenFilter filter = newFilter("abc123");
        MockHttpServletRequest request = new MockHttpServletRequest("GET", "/api/actuator/prometheus");
        request.setContextPath("/api");
        MockHttpServletResponse response = new MockHttpServletResponse();
        FilterChain chain = mock(FilterChain.class);

        filter.doFilter(request, response, chain);

        verify(chain, never()).doFilter(request, response);
        assertEquals(401, response.getStatus());
    }

    @Test
    void allowsActuatorRequestsWithMatchingToken() throws Exception {
        InternalTokenFilter filter = newFilter("abc123");
        MockHttpServletRequest request = new MockHttpServletRequest("GET", "/api/actuator/prometheus");
        request.setContextPath("/api");
        request.addHeader("X-Internal-Token", "abc123");
        MockHttpServletResponse response = new MockHttpServletResponse();
        FilterChain chain = mock(FilterChain.class);

        filter.doFilter(request, response, chain);

        verify(chain).doFilter(request, response);
    }

    @Test
    void nonActuatorRequestsPassThroughWithoutToken() throws Exception {
        InternalTokenFilter filter = newFilter("abc123");
        MockHttpServletRequest request = new MockHttpServletRequest("GET", "/api/chat/ask");
        request.setContextPath("/api");
        MockHttpServletResponse response = new MockHttpServletResponse();
        FilterChain chain = mock(FilterChain.class);

        filter.doFilter(request, response, chain);

        verify(chain).doFilter(request, response);
    }

    @Test
    void emptyConfiguredTokenFailsClosedWith401() throws Exception {
        InternalTokenFilter filter = newFilter("");
        MockHttpServletRequest request = new MockHttpServletRequest("GET", "/actuator/prometheus");
        MockHttpServletResponse response = new MockHttpServletResponse();
        FilterChain chain = mock(FilterChain.class);

        filter.doFilter(request, response, chain);

        verify(chain, never()).doFilter(request, response);
        assertEquals(401, response.getStatus());
    }
}