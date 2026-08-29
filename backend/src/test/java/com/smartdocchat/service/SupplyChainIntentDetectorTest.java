package com.smartdocchat.service;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

class SupplyChainIntentDetectorTest {

    @Test
    void strongKeywordTriggersIntent() {
        assertTrue(SupplyChainIntentDetector.isSupplyChainIntent("Dự báo nhu cầu tháng tới bao nhiêu?"));
        assertTrue(SupplyChainIntentDetector.isSupplyChainIntent("Phân tích supplier risk cho nhà cung cấp A"));
        assertTrue(SupplyChainIntentDetector.isSupplyChainIntent("Tính EOQ cho sản phẩm X"));
        assertTrue(SupplyChainIntentDetector.isSupplyChainIntent("Tối ưu lead time giao hàng"));
        assertTrue(SupplyChainIntentDetector.isSupplyChainIntent("Chuỗi cung ứng bị gián đoạn thế nào?"));
    }

    @Test
    void negationPhrasesAreNotSupplyChain() {
        // "order" appears but inside an idiom → must NOT route to agent.
        assertFalse(SupplyChainIntentDetector.isSupplyChainIntent(
                "The result is larger by an order of magnitude."));
        assertFalse(SupplyChainIntentDetector.isSupplyChainIntent(
                "In order to finish, we need a plan."));
        assertFalse(SupplyChainIntentDetector.isSupplyChainIntent(
                "The printer is out of order."));
        assertFalse(SupplyChainIntentDetector.isSupplyChainIntent(
                "Sort the list in order of priority."));
    }

    @Test
    void weakKeywordAloneIsNotEnough() {
        // Single weak keyword ("order"/"delivery") without supply-chain context.
        assertFalse(SupplyChainIntentDetector.isSupplyChainIntent("Please order a coffee."));
        assertFalse(SupplyChainIntentDetector.isSupplyChainIntent("The delivery of the letter was late."));
    }

    @Test
    void multipleWeakKeywordsTriggerIntent() {
        // Two weak signals together suggest a real supply-chain question.
        assertTrue(SupplyChainIntentDetector.isSupplyChainIntent(
                "Tồn kho kho hiện tại có đủ để giao hàng không?"));
        assertTrue(SupplyChainIntentDetector.isSupplyChainIntent(
                "Kiểm tra invoice và purchase order của lô hàng."));
    }

    @Test
    void emptyOrNullIsNotSupplyChain() {
        assertFalse(SupplyChainIntentDetector.isSupplyChainIntent(""));
        assertFalse(SupplyChainIntentDetector.isSupplyChainIntent("   "));
        assertFalse(SupplyChainIntentDetector.isSupplyChainIntent(null));
    }

    @Test
    void detectExposesScore() {
        assertTrue(SupplyChainIntentDetector.detect("Dự báo nhu cầu").score() >= 3);
        assertFalse(SupplyChainIntentDetector.detect("order of magnitude").isSupplyChain());
    }
}
