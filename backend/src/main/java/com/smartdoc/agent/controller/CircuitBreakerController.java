package com.smartdoc.agent.controller;

import com.smartdoc.agent.service.ResilientLlmService;
import io.github.resilience4j.circuitbreaker.CircuitBreaker;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.HashMap;
import java.util.Map;

/**
 * Controller expose trạng thái Circuit Breaker cho monitoring/ops.
 * GET /api/v1/resilience/circuit-breaker
 */
@RestController
@RequestMapping("/api/v1/resilience")
public class CircuitBreakerController {

    @Autowired
    private ResilientLlmService resilientLlmService;

    @GetMapping("/circuit-breaker")
    public Map<String, Object> getCircuitBreakerStatus() {
        Map<String, Object> result = new HashMap<>();
        result.put("state", resilientLlmService.getCircuitState().toString());

        CircuitBreaker.Metrics m = resilientLlmService.getMetrics();
        result.put("failureRate", m.getFailureRate());
        result.put("slowCallRate", m.getSlowCallRate());
        result.put("numberOfBufferedCalls", m.getNumberOfBufferedCalls());
        result.put("numberOfFailedCalls", m.getNumberOfFailedCalls());
        result.put("numberOfSlowCalls", m.getNumberOfSlowCalls());
        result.put("numberOfSuccessfulCalls", m.getNumberOfSuccessfulCalls());

        return result;
    }
}
