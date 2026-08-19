package com.smartdocchat.controller;

import jakarta.servlet.http.HttpServletRequest;
import org.springframework.security.web.csrf.CsrfToken;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class CsrfController {

    @GetMapping("/api/csrf")
    public CsrfToken csrf(HttpServletRequest request) {
        Object attr = request.getAttribute(CsrfToken.class.getName());
        if (attr == null) {
            attr = request.getAttribute("_csrf");
        }
        return (CsrfToken) attr;
    }
}