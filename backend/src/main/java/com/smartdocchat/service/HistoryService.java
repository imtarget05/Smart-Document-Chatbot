package com.smartdocchat.service;

import com.smartdocchat.dto.ChatResponse;
import com.smartdocchat.dto.SourceCitation;
import com.smartdocchat.dto.RetrievedChunk;
import com.smartdocchat.entity.ChatMessage;
import com.smartdocchat.repository.ChatMessageRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.util.*;

/**
 * HistoryService — Single Responsibility: all read/write operations on the
 * conversation history (ChatMessage entity) and response conversion.
 *
 * No LLM calls, no RAG logic, no external HTTP calls.
 */
@Service
@RequiredArgsConstructor
@Slf4j
public class HistoryService {

    private final ChatMessageRepository chatMessageRepository;

    // -----------------------------------------------------------------------
    // Read
    // -----------------------------------------------------------------------

    public List<ChatMessage> getChatHistory(String ownerUsername, String sessionId) {
        return chatMessageRepository
                .findByOwnerUsernameAndSessionIdOrderByCreatedAtAsc(ownerUsername, sessionId);
    }

    public List<ChatMessage> getChatHistory(String ownerUsername, String sessionId, Long documentId) {
        return chatMessageRepository
                .findByOwnerUsernameAndSessionIdAndDocumentIdOrderByCreatedAtAsc(
                        ownerUsername, sessionId, documentId);
    }

    /**
     * Return all unique sessions for a user, most-recent first.
     */
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

    // -----------------------------------------------------------------------
    // Write / Delete
    // -----------------------------------------------------------------------

    public ChatMessage save(ChatMessage chatMessage) {
        return chatMessageRepository.save(chatMessage);
    }

    public void clearChatHistory(String ownerUsername, String sessionId) {
        List<ChatMessage> messages = getChatHistory(ownerUsername, sessionId);
        chatMessageRepository.deleteAll(messages);
    }

    // -----------------------------------------------------------------------
    // Response conversion (presentation mapping)
    // -----------------------------------------------------------------------

    /**
     * Minimal converter — no RAG metadata; used by the sync path and the
     * controller's own {@code convertToResponse}.
     */
    public ChatResponse convertToResponse(ChatMessage message) {
        return convertToResponse(message, null, 0.0, null, null, null);
    }

    /**
     * Enriched converter that populates structured AI-Engineer output fields.
     */
    public ChatResponse convertToResponse(ChatMessage message, String ragStrategy,
                                          double confidenceScore, Long latencyMs,
                                          String model, List<SourceCitation> sources) {
        List<Long> docIds = parseDocumentIds(message.getDocumentIds());
        return ChatResponse.builder()
                .id(message.getId())
                .sessionId(message.getSessionId())
                .userMessage(message.getUserMessage())
                .aiResponse(message.getAiResponse())
                .sourceChunks(message.getSourceChunks())
                .documentId(message.getDocumentId())
                .documentIds(docIds.isEmpty() ? null : docIds)
                .confidence(classifyConfidence(confidenceScore))
                .confidenceScore(confidenceScore)
                .latencyMs(latencyMs)
                .model(model)
                .ragStrategy(ragStrategy)
                .sources(sources)
                .build();
    }

    // -----------------------------------------------------------------------
    // Citation helpers
    // -----------------------------------------------------------------------

    /**
     * Convert raw retrieved chunks into structured {@link SourceCitation} DTOs.
     */
    public List<SourceCitation> buildCitations(List<RetrievedChunk> chunks,
                                               Map<RetrievedChunk, String> chunkFileMap,
                                               Map<RetrievedChunk, Long> chunkDocIdMap) {
        List<SourceCitation> citations = new ArrayList<>();
        for (RetrievedChunk chunk : chunks) {
            citations.add(SourceCitation.builder()
                    .document(chunkFileMap.getOrDefault(chunk, "unknown"))
                    .documentId(chunkDocIdMap.getOrDefault(chunk, null))
                    .content(chunk.getText())
                    .score(chunk.getScore())
                    .build());
        }
        return citations;
    }

    // -----------------------------------------------------------------------
    // Private helpers
    // -----------------------------------------------------------------------

    /** Map a numeric confidence score to a human-readable label. */
    public String classifyConfidence(double score) {
        if (score >= 0.70) return "high";
        if (score >= 0.45) return "medium";
        return "low";
    }

    private List<Long> parseDocumentIds(String documentIds) {
        List<Long> docIds = new ArrayList<>();
        if (documentIds != null && !documentIds.isBlank()) {
            for (String s : documentIds.split(",")) {
                try {
                    docIds.add(Long.parseLong(s.trim()));
                } catch (NumberFormatException e) {
                    // Ignore malformed ID
                }
            }
        }
        return docIds;
    }
}
