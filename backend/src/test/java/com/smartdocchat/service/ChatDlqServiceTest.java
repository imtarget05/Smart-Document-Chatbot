package com.smartdocchat.service;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;

class ChatDlqServiceTest {

    private ChatDlqService dlqService;

    @BeforeEach
    void setUp() {
        dlqService = new ChatDlqService();
    }

    @Test
    void recordAddsEntryToDlq() {
        dlqService.recordDlq("alice", "sess-1", "test query", "LLM timeout");

        Map<String, String> snapshot = dlqService.getDlqSnapshot();
        assertEquals(1, snapshot.size());
        assertTrue(snapshot.values().iterator().next().contains("alice|test query|LLM timeout"));
    }

    @Test
    void getDlqSnapshotReturnsUnmodifiableMap() {
        dlqService.record("alice", "sess-1", "query", "err");
        Map<String, String> snapshot = dlqService.getDlqSnapshot();

        assertThrows(UnsupportedOperationException.class, () -> snapshot.put("newKey", "val"));
    }

    @Test
    void dlqEnforcesCapacityLimit() {
        for (int i = 0; i < 1050; i++) {
            dlqService.record("alice", "sess-" + i, "query " + i, "err " + i);
        }

        assertTrue(dlqService.size() <= 1000, "DLQ size must be capped at 1000");
    }

    @Test
    void clearEmptiesDlq() {
        dlqService.record("alice", "sess-1", "q", "err");
        assertTrue(dlqService.size() > 0);

        dlqService.clear();
        assertEquals(0, dlqService.size());
    }
}
