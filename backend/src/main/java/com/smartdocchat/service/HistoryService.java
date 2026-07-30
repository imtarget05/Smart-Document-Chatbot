package com.smartdocchat.service;

import com.smartdocchat.dto.ChatResponse;
import com.smartdocchat.entity.ChatMessage;
import com.smartdocchat.repository.ChatMessageRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.util.*;

@Service
@RequiredArgsConstructor
@Slf4j
public class HistoryService {

    private final ChatMessageRepository chatMessageRepository;

    public List<ChatMessage> getChatHistory(String ownerUsername, String sessionId) {
        return chatMessageRepository
                .findByOwnerUsernameAndSessionIdOrderByCreatedAtAsc(ownerUsername, sessionId);
    }

    public List<ChatMessage> getChatHistory(String ownerUsername, String sessionId, Long documentId) {
        return chatMessageRepository
                .findByOwnerUsernameAndSessionIdAndDocumentIdOrderByCreatedAtAsc(
                        ownerUsername, sessionId, documentId);
    }

    public List<Map<String, Object>> getUniqueSessions(String ownerUsername) {
        List<Object[]> rows = chatMessageRepository.findUniqueSessionsByOwner(ownerUsername);
        List<Map<String, Object>> sessions = new ArrayList<>();
        for (Object[] row : rows) {
            Map<String, Object> session = new HashMap<>();
            session.put("sessionId", row[0]);
            session.put("lastMessage", row[1]);
            session.put("createdAt", row[2]);
            sessions.add(session);
        }
        sessions.sort((a, b) ->
                ((java.util.Date) b.get("createdAt")).compareTo((java.util.Date) a.get("createdAt")));
        return sessions;
    }

    public ChatMessage save(ChatMessage chatMessage) {
        return chatMessageRepository.save(chatMessage);
    }

    public void clearChatHistory(String ownerUsername, String sessionId) {
        List<ChatMessage> messages = getChatHistory(ownerUsername, sessionId);
        chatMessageRepository.deleteAll(messages);
    }

    public ChatResponse convertToResponse(ChatMessage message) {
        return ChatResponse.builder()
                .id(message.getId())
                .sessionId(message.getSessionId())
                .userMessage(message.getUserMessage())
                .aiResponse(message.getAiResponse())
                .sourceChunks(message.getSourceChunks())
                .documentId(message.getDocumentId())
                .build();
    }
}