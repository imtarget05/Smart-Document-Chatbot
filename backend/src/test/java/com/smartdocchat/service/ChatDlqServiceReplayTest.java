package com.smartdocchat.service;

import org.junit.jupiter.api.Test;

import java.util.concurrent.atomic.AtomicReference;

import static org.junit.jupiter.api.Assertions.*;

/**
 * RED: DLQ must be replayable/retryable — currently entries can only be
 * recorded, never replayed.
 */
class ChatDlqServiceReplayTest {

    @Test
    void replayRemovesEntryAndRetriesQuery() {
        ChatDlqService dlq = new ChatDlqService();
        dlq.recordDlq("alice", "sess-1", "hello", "boom");
        String key = dlq.getDlqSnapshot().keySet().iterator().next();

        AtomicReference<ChatDlqService.DlqEntry> retried = new AtomicReference<>();
        assertTrue(dlq.replay(key, retried::set), "replay of a recorded key must succeed");

        assertNotNull(retried.get());
        assertEquals("alice", retried.get().ownerUsername());
        assertEquals("sess-1", retried.get().sessionId());
        assertEquals("hello", retried.get().query());
        assertEquals(0, dlq.size(), "replayed entry must leave the DLQ");
    }

    @Test
    void replayUnknownKeyReturnsFalse() {
        ChatDlqService dlq = new ChatDlqService();
        assertFalse(dlq.replay("missing-key", e -> fail("handler must not run for unknown key")));
    }
}
