package com.smartdocchat.service;

import java.util.List;
import java.util.Set;

/**
 * Phát hiện supply-chain intent từ user message (chain #4: backend → agent).
 *
 * Nâng cấp từ keyword-only đơn giản lên classifier nhẹ:
 * - Mỗi keyword có trọng số (STRONG / WEAK).
 * - Các cụm phủ định (negation/idiom) như "order of magnitude", "in order to",
 *   "out of order" không được tính là supply-chain intent.
 * - Chỉ trả true khi có ít nhất 1 STRONG keyword (hoặc tổng điểm vượt ngưỡng),
 *   tránh false-positive do từ "order"/"delivery" xuất hiện trong ngữ cảnh khác.
 *
 * Không dùng LLM để giữ latency thấp trên luồng chat chính.
 */
public class SupplyChainIntentDetector {

    /** Keyword rõ ràng, domain-specific — 1 hit là đủ kết luận intent. */
    private static final Set<String> STRONG_KEYWORDS = Set.of(
            "dự báo nhu cầu", "dự báo", "demand forecast", "forecast demand",
            "tuyến giao hàng", "optimal route", "vrp", "vehicle routing",
            "nhà cung cấp rủi ro", "supplier risk", "supplier risk analysis",
            "eoq", "economic order quantity", "safety stock", "reorder point",
            "phát hiện bất thường", "anomaly detection", "bất thường chuỗi cung",
            "lead time", "thời gian dẫn", "warehouse slotting", "slotting",
            "xuất nhập khẩu", "supply chain", "chuỗi cung ứng",
            "procurement", "tồn kho an toàn", "inventory optimization",
            "logistics optimization", "tối ưu chuỗi cung", "đặt hàng tự động"
    );

    /** Keyword yếu — dễ false-positive, chỉ cộng điểm, không tự kết luận. */
    private static final Set<String> WEAK_KEYWORDS = Set.of(
            "tồn kho", "inventory", "warehouse",
            "đặt hàng", "purchase order", "po ",
            "hóa đơn", "invoice", "giao hàng", "delivery",
            "đúng hạn", "on-time", "defect", "lỗi", "supplier", "nhà cung cấp",
            "forecast", "dự đoán", "tuyến", "route", "rủi ro", "risk",
            "anomaly", "đạo đột", "lead", "shipping", "logistics"
    );

    /** Cụm phủ định / idiom chứa từ yếu nhưng KHÔNG phải supply-chain. */
    private static final List<String> NEGATION_PHRASES = List.of(
            "order of magnitude",
            "in order to",
            "out of order",
            "on the order of",
            "order by",
            "made to order",
            "custom order"
    );

    private static final int WEAK_THRESHOLD = 2;

    /**
     * @return true nếu message mang supply-chain intent (dùng cho routing agent).
     */
    public static boolean isSupplyChainIntent(String message) {
        return detect(message).isSupplyChain();
    }

    /** Kết quả có điểm số — tiện mở rộng (logging, threshold động). */
    public static Result detect(String message) {
        if (message == null || message.isBlank()) {
            return new Result(false, 0);
        }
        String lower = message.toLowerCase();

        // Loại các cụm phủ định trước khi đếm từ yếu.
        String stripped = lower;
        for (String phrase : NEGATION_PHRASES) {
            stripped = stripped.replace(phrase, " ");
        }

        int score = 0;
        boolean hasStrong = false;

        for (String kw : STRONG_KEYWORDS) {
            if (lower.contains(kw)) {
                score += 3;
                hasStrong = true;
            }
        }
        for (String kw : WEAK_KEYWORDS) {
            if (stripped.contains(kw)) {
                score += 1;
            }
        }

        // STRONG ⇒ intent chắc chắn. Ngược lại cần đủ nhiều WEAK để kết luận.
        boolean isSupplyChain = hasStrong || score >= WEAK_THRESHOLD;
        return new Result(isSupplyChain, score);
    }

    public static final class Result {
        private final boolean supplyChain;
        private final int score;

        Result(boolean supplyChain, int score) {
            this.supplyChain = supplyChain;
            this.score = score;
        }

        public boolean isSupplyChain() {
            return supplyChain;
        }

        public int score() {
            return score;
        }
    }
}
