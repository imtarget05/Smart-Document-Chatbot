package com.smartdocchat.controller;

import com.smartdocchat.service.SupplyChainService;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.http.ResponseEntity;

import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.when;

/**
 * Unit tests for SupplyChainController delegating to SupplyChainService.
 */
@ExtendWith(MockitoExtension.class)
class SupplyChainControllerTest {

    @Mock private SupplyChainService supplyChainService;
    private SupplyChainController controller;

    @BeforeEach
    void setUp() {
        controller = new SupplyChainController(supplyChainService);
    }

    @Test
    void forecast_delegatesToService() {
        Map<String, Object> body = Map.of("history", java.util.List.of(1, 2, 3));
        Map<String, Object> expected = Map.of("forecast", java.util.List.of(10.0));
        when(supplyChainService.forecast(eq(body))).thenReturn(expected);

        ResponseEntity<Map<String, Object>> res = controller.forecast(body);

        assertEquals(200, res.getStatusCodeValue());
        assertNotNull(res.getBody());
        assertEquals(expected, res.getBody());
    }

    @Test
    void optimizeRoute_delegatesToService() {
        Map<String, Object> body = Map.of("distance_matrix", java.util.List.of());
        Map<String, Object> expected = Map.of("total_distance", 99.9);
        when(supplyChainService.optimizeRoute(any())).thenReturn(expected);

        ResponseEntity<Map<String, Object>> res = controller.optimizeRoute(body);

        assertEquals(expected, res.getBody());
    }

    @Test
    void supplierRisk_delegatesToService() {
        Map<String, Object> body = Map.of("lead_time_std", 1);
        Map<String, Object> expected = Map.of("risk_score", 42);
        when(supplyChainService.supplierRisk(any())).thenReturn(expected);

        assertEquals(expected, controller.supplierRisk(body).getBody());
    }

    @Test
    void anomalyDetect_delegatesToService() {
        Map<String, Object> body = Map.of("values", java.util.List.of(1, 2, 3, 4, 5, 99));
        Map<String, Object> expected = Map.of("count", 1);
        when(supplyChainService.anomalyDetect(any())).thenReturn(expected);

        assertEquals(expected, controller.anomalyDetect(body).getBody());
    }

    @Test
    void inventoryOptimalOrder_delegatesToService() {
        Map<String, Object> body = Map.of("annual_demand", 1000);
        Map<String, Object> expected = Map.of("eoq", 200.0);
        when(supplyChainService.inventoryOptimalOrder(any())).thenReturn(expected);

        assertEquals(expected, controller.inventoryOptimalOrder(body).getBody());
    }
}
