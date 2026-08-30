package com.smartdocchat.service;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * Hardening tests for SupplyChainIntentDetector — boundary and obfuscation cases
 * that a naive keyword matcher gets wrong. Covers the strong/weak/negation rules.
 */
class SupplyChainClassifierHardeningTest {

    private final SupplyChainIntentDetector detector = new SupplyChainIntentDetector();

    @Test
    void strongKeyword_vietnameseUppercase_triggers() {
        assertTrue(detector.isSupplyChainIntent("DỰ BÁO NHU CẦU TỒN KHO supplier risk"));
    }

    @Test
    void negation_phrase_notTriggered() {
        // "order of magnitude" must not trip the supply-chain path
        assertFalse(detector.isSupplyChainIntent(
                "The result differs by an order of magnitude, out of order, in order to proceed."));
    }

    @Test
    void twoWeakKeywords_triggers() {
        assertTrue(detector.isSupplyChainIntent("tồn kho giao hàng on-time delivery"));
    }

    @Test
    void singleWeakKeyword_doesNotTrigger() {
        assertFalse(detector.isSupplyChainIntent("tồn kho của cửa hàng rất lớn"));
    }

    @Test
    void purchaseOrderAlone_doesNotTrigger() {
        // "purchase order" is one weak hit; needs >=2 weak to conclude
        assertFalse(detector.isSupplyChainIntent("please create a purchase order for office supplies"));
    }

    @Test
    void poPlusInvoice_triggers() {
        assertTrue(detector.isSupplyChainIntent("PO-12345 and the invoice from supplier"));
    }

    @Test
    void eoqStrong_triggers() {
        assertTrue(detector.isSupplyChainIntent("Tính toán EOQ cho mô hình inventory"));
    }

    @Test
    void emptyAndNull_safe() {
        assertFalse(detector.isSupplyChainIntent(""));
        assertFalse(detector.isSupplyChainIntent(null));
        assertFalse(detector.isSupplyChainIntent("   "));
    }

    @Test
    void genericBusinessNotTriggered() {
        assertFalse(detector.isSupplyChainIntent("Tôi muốn lập báo cáo tài chính quý này"));
    }

    @Test
    void detectReturnsScoreAndFlag() {
        SupplyChainIntentDetector.Result r = detector.detect("dự báo nhu cầu kho supplier risk");
        assertTrue(r.isSupplyChain());
        assertTrue(r.score() > 0);
    }
}
