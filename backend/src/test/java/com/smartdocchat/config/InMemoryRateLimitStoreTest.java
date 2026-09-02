package com.smartdocchat.config;

import org.junit.jupiter.api.Test;

import java.time.Duration;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

class InMemoryRateLimitStoreTest {

    private final InMemoryRateLimitStore store = new InMemoryRateLimitStore();

    @Test
    void allowsUpToCapacityThenBlocks() {
        Duration window = Duration.ofSeconds(60);
        assertTrue(store.isAllowed("k", 2, window));
        assertTrue(store.isAllowed("k", 2, window));
        assertFalse(store.isAllowed("k", 2, window));
    }

    @Test
    void distinctKeysAreIndependent() {
        Duration window = Duration.ofSeconds(60);
        store.isAllowed("a", 1, window);
        assertFalse(store.isAllowed("a", 1, window));
        assertTrue(store.isAllowed("b", 1, window));
    }

    @Test
    void returnsFullRemainingWhenEmpty() {
        assertEquals(5L, store.getRemaining("fresh", 5, Duration.ofSeconds(60)));
    }

    @Test
    void decrementsRemainingAsRequestsAreAllowed() {
        Duration window = Duration.ofSeconds(60);
        store.isAllowed("k", 5, window);
        store.isAllowed("k", 5, window);
        assertEquals(3L, store.getRemaining("k", 5, window));
    }

    @Test
    void windowSlidesAndFreesBudget() throws InterruptedException {
        // 2-second window; wait so early budget expires.
        Duration window = Duration.ofSeconds(2);
        assertTrue(store.isAllowed("k", 1, window));
        assertFalse(store.isAllowed("k", 1, window));
        Thread.sleep(2100);
        assertTrue(store.isAllowed("k", 1, window));
    }
}