package com.smartdocchat.controller;

import com.smartdocchat.service.SupplyChainService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

/**
 * Proxies frontend requests to the FastAPI Supply Chain module.
 * All endpoints require authentication; the backend injects the internal token.
 */
@RestController
@RequestMapping("/api/supply-chain")
@RequiredArgsConstructor
public class SupplyChainController {

    private final SupplyChainService supplyChainService;

    @PostMapping("/forecast")
    @PreAuthorize("isAuthenticated()")
    public ResponseEntity<Map<String, Object>> forecast(@RequestBody Map<String, Object> body) {
        return ResponseEntity.ok(supplyChainService.forecast(body));
    }

    @PostMapping("/optimize-route")
    @PreAuthorize("isAuthenticated()")
    public ResponseEntity<Map<String, Object>> optimizeRoute(@RequestBody Map<String, Object> body) {
        return ResponseEntity.ok(supplyChainService.optimizeRoute(body));
    }

    @PostMapping("/supplier-risk")
    @PreAuthorize("isAuthenticated()")
    public ResponseEntity<Map<String, Object>> supplierRisk(@RequestBody Map<String, Object> body) {
        return ResponseEntity.ok(supplyChainService.supplierRisk(body));
    }

    @PostMapping("/anomaly-detect")
    @PreAuthorize("isAuthenticated()")
    public ResponseEntity<Map<String, Object>> anomalyDetect(@RequestBody Map<String, Object> body) {
        return ResponseEntity.ok(supplyChainService.anomalyDetect(body));
    }

    @PostMapping("/inventory-optimal-order")
    @PreAuthorize("isAuthenticated()")
    public ResponseEntity<Map<String, Object>> inventoryOptimalOrder(@RequestBody Map<String, Object> body) {
        return ResponseEntity.ok(supplyChainService.inventoryOptimalOrder(body));
    }
}