package com.smartdocchat.controller;

import org.junit.jupiter.api.Test;
import org.springframework.mock.web.MockHttpServletRequest;
import org.springframework.security.web.csrf.CsrfToken;
import org.springframework.security.web.csrf.DefaultCsrfToken;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;

class CsrfControllerTest {

    private CsrfController controller = new CsrfController();

    @Test
    void returnsTokenFromPrimaryRequestAttribute() {
        MockHttpServletRequest request = new MockHttpServletRequest();
        DefaultCsrfToken token = new DefaultCsrfToken("X-XSRF-TOKEN", "_csrf", "abc-123");
        request.setAttribute(CsrfToken.class.getName(), token);

        CsrfToken result = controller.csrf(request);

        assertEquals("abc-123", result.getToken());
        assertEquals("X-XSRF-TOKEN", result.getHeaderName());
    }

    @Test
    void fallsBackToUnderscoreCsrfAttribute() {
        MockHttpServletRequest request = new MockHttpServletRequest();
        DefaultCsrfToken token = new DefaultCsrfToken("X-XSRF-TOKEN", "_csrf", "fallback-token");
        request.setAttribute("_csrf", token);

        assertEquals("fallback-token", controller.csrf(request).getToken());
    }

    @Test
    void returnsNullWhenNoTokenPresent() {
        MockHttpServletRequest request = new MockHttpServletRequest();
        assertNull(controller.csrf(request));
    }
}