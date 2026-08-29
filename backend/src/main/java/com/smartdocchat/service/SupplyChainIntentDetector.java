package com.smartdocchat.service;

import java.util.Set;

/**
 * Detect supply chain intent từ user message.
 *
 * Chain cho #4: backend → agent integration.
 * Khi message chứa supply chain keywords, agent handle thay vì CRAG.
 */
public class SupplyChainIntentDetector {

    private static final Set<String> SUPPLY_CHAIN_KEYWORDS = Set.of(
            // Vietnamese
            "dự báo", "dự báo nhu cầu", "forecast", "dự đoán",
            "tuyến", "tuyến giao hàng", "route", "optimal route", "vrp",
            "rủi ro", "supplier", "nhà cung cấp", "nhà cung cấp rủi ro",
            "tồn kho", "inventory", "eoq", "safety stock", "reorder",
            "đạo đột", "anomaly", "phát hiện bất thường",
            "đặt hàng", "order", "po", "purchase order",
            "invoice", "hóa đơn",
            "demand", "xuất nhập khẩu", "supply chain",
            "warehouse", "kho", "slotting",
            "lead time", "thời gian dẫn", "defect", "lỗi",
            "on-time", "đúng hạn", "delivery", "giao hàng",
            // English
            "demand forecast", "supply", "optimization", "shipping",
            "logistics", "procurement", "supplier risk", "anomaly detection"
    );

    /**
     * True khi message chứa supply chain intent.
     * Chỉ check keywords — không dùng LLM để avoid latency.
     */
    public static boolean isSupplyChainIntent(String message) {
        if (message == null || message.isBlank()) {
            return false;
        }
        String lower = message.toLowerCase();
        for (String keyword : SUPPLY_CHAIN_KEYWORDS) {
            if (lower.contains(keyword.toLowerCase())) {
                return true;
            }
        }
        return false;
    }
}
