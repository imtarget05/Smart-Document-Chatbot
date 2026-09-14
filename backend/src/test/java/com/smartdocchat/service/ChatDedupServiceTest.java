package com.smartdocchat.service;

import com.smartdocchat.dto.ChatRequest;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

class ChatDedupServiceTest {

    private ChatDedupService dedupService;

    @BeforeEach
    void setUp() {
        dedupService = new ChatDedupService();
    }

    @Test
    void firstRequestIsNotDuplicate() {
        ChatRequest req = ChatRequest.builder()
                .sessionId("sess-1")
                .message("hello world")
                .build();

        assertFalse(dedupService.isDuplicateRequest("user1", req));
        assertEquals(1, dedupService.size());
    }

    @Test
    void immediateIdenticalRequestIsDuplicate() {
        ChatRequest req = ChatRequest.builder()
                .sessionId("sess-1")
                .message("hello world")
                .build();

        assertFalse(dedupService.isDuplicateRequest("user1", req));
        assertTrue(dedupService.isDuplicateRequest("user1", req));
    }

    @Test
    void differentMessageOrSessionIsNotDuplicate() {
        ChatRequest req1 = ChatRequest.builder()
                .sessionId("sess-1")
                .message("message 1")
                .build();
        ChatRequest req2 = ChatRequest.builder()
                .sessionId("sess-1")
                .message("message 2")
                .build();
        ChatRequest req3 = ChatRequest.builder()
                .sessionId("sess-2")
                .message("message 1")
                .build();

        assertFalse(dedupService.isDuplicateRequest("user1", req1));
        assertFalse(dedupService.isDuplicateRequest("user1", req2));
        assertFalse(dedupService.isDuplicateRequest("user1", req3));
        assertFalse(dedupService.isDuplicateRequest("user2", req1));
    }

    @Test
    void nullOrMissingMessageReturnsFalse() {
        assertFalse(dedupService.isDuplicateRequest("user1", null));
        assertFalse(dedupService.isDuplicateRequest("user1", ChatRequest.builder().build()));
    }

    @Test
    void clearEmptiesCache() {
        ChatRequest req = ChatRequest.builder()
                .sessionId("sess-1")
                .message("hello")
                .build();
        dedupService.isDuplicateRequest("user1", req);
        assertTrue(dedupService.size() > 0);

        dedupService.clear();
        assertEquals(0, dedupService.size());
    }
}
