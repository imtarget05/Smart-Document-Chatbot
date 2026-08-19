package com.smartdocchat.service;

import com.smartdocchat.dto.ChatResponse;
import com.smartdocchat.entity.ChatMessage;
import com.smartdocchat.repository.ChatMessageRepository;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.util.Date;
import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class HistoryServiceTest {

    @Mock private ChatMessageRepository chatMessageRepository;

    private HistoryService historyService = new HistoryService(null);

    private ChatMessage message(long id, String session, String user, String ai) {
        return ChatMessage.builder()
                .id(id)
                .sessionId(session)
                .userMessage(user)
                .aiResponse(ai)
                .documentId(1L)
                .sourceChunks("[chunk]")
                .build();
    }

    @Test
    void getChatHistoryDelegatesByOwnerAndSession() {
        historyService = new HistoryService(chatMessageRepository);
        when(chatMessageRepository.findByOwnerUsernameAndSessionIdOrderByCreatedAtAsc("alice", "s1"))
                .thenReturn(List.of(message(1L, "s1", "q", "a")));
        when(chatMessageRepository.findByOwnerUsernameAndSessionIdAndDocumentIdOrderByCreatedAtAsc("alice", "s1", 1L))
                .thenReturn(List.of(message(1L, "s1", "q", "a")));

        assertEquals(1, historyService.getChatHistory("alice", "s1").size());
        assertEquals(1, historyService.getChatHistory("alice", "s1", 1L).size());
        verify(chatMessageRepository).findByOwnerUsernameAndSessionIdAndDocumentIdOrderByCreatedAtAsc("alice", "s1", 1L);
    }

    @Test
    void getUniqueSessionsMapsRowsAndSortsByCreatedAtDesc() {
        historyService = new HistoryService(chatMessageRepository);
        Date newer = new Date(2000L);
        Date older = new Date(1000L);
        when(chatMessageRepository.findUniqueSessionsByOwner("alice"))
                .thenReturn(List.of(new Object[]{"s-old", "old msg", older}, new Object[]{"s-new", "new msg", newer}));

        List<Map<String, Object>> sessions = historyService.getUniqueSessions("alice");

        assertEquals(2, sessions.size());
        assertEquals("s-new", sessions.get(0).get("sessionId"));
        assertEquals("old msg", sessions.get(1).get("lastMessage"));
        assertEquals(older, sessions.get(1).get("createdAt"));
    }

    @Test
    void saveDelegatesToRepository() {
        historyService = new HistoryService(chatMessageRepository);
        ChatMessage msg = message(7L, "s1", "q", "a");
        when(chatMessageRepository.save(msg)).thenReturn(msg);

        assertEquals(msg, historyService.save(msg));
    }

    @Test
    void clearChatHistoryDeletesAllMessagesOfSession() {
        historyService = new HistoryService(chatMessageRepository);
        ChatMessage msg = message(1L, "s1", "q", "a");
        when(chatMessageRepository.findByOwnerUsernameAndSessionIdOrderByCreatedAtAsc("alice", "s1"))
                .thenReturn(List.of(msg));

        historyService.clearChatHistory("alice", "s1");

        verify(chatMessageRepository).deleteAll(List.of(msg));
    }

    @Test
    void convertToResponseMapsAllFields() {
        ChatMessage msg = message(3L, "s1", "user q", "ai a");
        ChatResponse response = new HistoryService(chatMessageRepository).convertToResponse(msg);

        assertEquals(3L, response.getId());
        assertEquals("s1", response.getSessionId());
        assertEquals("user q", response.getUserMessage());
        assertEquals("ai a", response.getAiResponse());
        assertEquals("[chunk]", response.getSourceChunks());
        assertEquals(1L, response.getDocumentId());
    }

    @Test
    void getChatHistoryReturnsEmptyWithoutDocFilter() {
        historyService = new HistoryService(chatMessageRepository);
        when(chatMessageRepository.findByOwnerUsernameAndSessionIdOrderByCreatedAtAsc("alice", "s1"))
                .thenReturn(List.of());
        assertTrue(historyService.getChatHistory("alice", "s1").isEmpty());
    }
}