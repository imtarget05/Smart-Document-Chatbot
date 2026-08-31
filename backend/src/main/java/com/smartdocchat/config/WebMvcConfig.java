package com.smartdocchat.config;

import lombok.RequiredArgsConstructor;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.servlet.config.annotation.InterceptorRegistry;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;

@Configuration
@RequiredArgsConstructor
public class WebMvcConfig implements WebMvcConfigurer {

    private final RateLimitInterceptor rateLimitInterceptor;

    @Override
    public void addInterceptors(InterceptorRegistry registry) {
        // NOTE: interceptor patterns are matched against the path *inside* the
        // servlet context (server.servlet.context-path=/api), so "/api/**"
        // never matched and rate limiting was silently dead. Use "/**" and let
        // the interceptor itself decide which paths to limit.
        registry.addInterceptor(rateLimitInterceptor).addPathPatterns("/**");
    }
}
