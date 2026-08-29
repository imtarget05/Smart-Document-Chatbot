package com.smartdocchat.controller;

import org.junit.jupiter.api.Test;
import org.springframework.security.web.csrf.CsrfToken;
import org.springframework.security.web.csrf.DefaultCsrfToken;

import static org.junit.jupiter.api.Assertions.assertEquals;

class CsrfControllerTest {

    private CsrfController controller = new CsrfController();

    @Test
    void returnsResolvedToken() {
        CsrfToken token = new DefaultCsrfToken("X-XSRF-TOKEN", "_csrf", "abc-123");

        CsrfToken result = controller.csrf(token);

        assertEquals("abc-123", result.getToken());
        assertEquals("X-XSRF-TOKEN", result.getHeaderName());
    }
}