package com.smartdocchat.controller;

import org.springframework.security.web.csrf.CsrfToken;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class CsrfController {

    @GetMapping("/csrf")
    public CsrfToken csrf(CsrfToken token) {
        // Injecting CsrfToken as a method argument forces Spring Security 6's
        // deferred token to resolve, so the XSRF-TOKEN cookie gets written and
        // the token value is returned. Reading request attributes directly
        // (previous impl) returned null and broke the SPA login flow.
        return token;
    }
}