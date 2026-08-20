package com.smartdocchat.config;

import jakarta.servlet.FilterChain;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.slf4j.MDC;
import org.springframework.mock.web.MockHttpServletRequest;
import org.springframework.mock.web.MockHttpServletResponse;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.doAnswer;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;

class RequestIdFilterTest {

    @Test
    void propagatesUpstreamRequestIdAndSetsMdc() throws Exception {
        RequestIdFilter filter = new RequestIdFilter();
        MockHttpServletRequest request = new MockHttpServletRequest("POST", "/api/chat/ask");
        request.addHeader("X-Request-Id", "upstream-123");
        MockHttpServletResponse response = new MockHttpServletResponse();
        FilterChain chain = mock(FilterChain.class);
        doAnswer(inv -> {
            assertEquals("upstream-123", MDC.get("requestId"));
            assertEquals("POST", MDC.get("method"));
            assertEquals("/api/chat/ask", MDC.get("path"));
            response.setStatus(200);
            return null;
        }).when(chain).doFilter(any(HttpServletRequest.class), any(HttpServletResponse.class));

        filter.doFilter(request, response, chain);

        assertEquals("upstream-123", response.getHeader("X-Request-Id"));
        assertNull(MDC.get("requestId"));
        verify(chain).doFilter(any(HttpServletRequest.class), any(HttpServletResponse.class));
    }

    @Test
    void generatesRequestIdWhenMissing() throws Exception {
        RequestIdFilter filter = new RequestIdFilter();
        MockHttpServletRequest request = new MockHttpServletRequest("GET", "/api/documents");
        MockHttpServletResponse response = new MockHttpServletResponse();
        FilterChain chain = mock(FilterChain.class);

        filter.doFilter(request, response, chain);

        String requestId = response.getHeader("X-Request-Id");
        assertNotNull(requestId);
        assertTrue(requestId.length() > 8);
        assertNull(MDC.get("requestId"));
    }

    @Test
    void logsStructuredLineWithStatusAndDuration() throws Exception {
        RequestIdFilter filter = new RequestIdFilter();
        MockHttpServletRequest request = new MockHttpServletRequest("GET", "/api/health");
        MockHttpServletResponse response = new MockHttpServletResponse();
        response.setStatus(204);
        FilterChain chain = mock(FilterChain.class);
        ArgumentCaptor<HttpServletResponse> captor = ArgumentCaptor.forClass(HttpServletResponse.class);

        filter.doFilter(request, response, chain);

        verify(chain).doFilter(any(HttpServletRequest.class), captor.capture());
        assertEquals(204, captor.getValue().getStatus());
    }
}