package com.smartdocchat.service;

import com.smartdocchat.entity.ChatMessage;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import java.io.IOException;
import java.util.*;
import java.util.concurrent.CompletableFuture;

@Service
@RequiredArgsConstructor
@Slf4j
public class ChatService {

    private final DocumentService documentService;
    private final MessageHandler messageHandler;
    private final HistoryService historyService;

    public ChatMessage processQuery(
            String ownerUsername, String sessionId, Long documentId, String userMessage
    ) {
        // Retrieve relevant chunks from the document
        List<String> relevantChunks = retrieveRelevantChunks(ownerUsername, documentId, userMessage);

        // Build prompt & call LLM
        String prompt = messageHandler.buildPrompt(userMessage, relevantChunks);
        String aiResponse = messageHandler.callLLM(prompt);

        // Build source chunks string for display
        String sourceChunks = relevantChunks.isEmpty() ? null : String.join("\n---\n", relevantChunks);

        // Persist
        ChatMessage chatMessage = ChatMessage.builder()
                .sessionId(sessionId)
                .ownerUsername(ownerUsername)
                .documentId(documentId)
                .userMessage(userMessage)
                .aiResponse(aiResponse)
                .sourceChunks(sourceChunks)
                .build();

        return historyService.save(chatMessage);
    }

    public SseEmitter processQueryStream(
            String ownerUsername, String sessionId, Long documentId, String userMessage
    ) {
        SseEmitter emitter = new SseEmitter(180_000L);

        CompletableFuture.runAsync(() -> {
            try {
                // Retrieve relevant chunks
                List<String> relevantChunks = retrieveRelevantChunks(ownerUsername, documentId, userMessage);
                String sourceChunks = relevantChunks.isEmpty() ? null : String.join("\n---\n", relevantChunks);

                // Build prompt
                String prompt = messageHandler.buildPrompt(userMessage, relevantChunks);

                // Send metadata event
                Map<String, Object> metaEvent = new HashMap<>();
                metaEvent.put("sourceChunks", sourceChunks);
                metaEvent.put("documentId", documentId);
                emitter.send(SseEmitter.event().name("metadata").data(metaEvent));

                // Stream LLM tokens
                StringBuilder aiResponseBuilder = new StringBuilder();
                messageHandler.streamLLM(prompt, token -> {
                    aiResponseBuilder.append(token);
                    try {
                        emitter.send(SseEmitter.event().name("chunk").data(token));
                    } catch (IOException e) {
                        throw new IllegalStateException("SSE client disconnected during stream", e);
                    }
                });

                String fullResponse = aiResponseBuilder.toString();

                // Persist
                ChatMessage chatMessage = ChatMessage.builder()
                        .sessionId(sessionId)
                        .ownerUsername(ownerUsername)
                        .documentId(documentId)
                        .userMessage(userMessage)
                        .aiResponse(fullResponse)
                        .sourceChunks(sourceChunks)
                        .build();
                ChatMessage saved = historyService.save(chatMessage);

                // Final complete event
                emitter.send(SseEmitter.event().name("complete").data(saved));
                emitter.complete();

            } catch (Exception e) {
                log.error("Error in streaming task: {}", e.getMessage(), e);
                try {
                    emitter.send(SseEmitter.event().name("error").data(e.getMessage()));
                    emitter.completeWithError(e);
                } catch (Exception ex) {
                    // Ignored
                }
            }
        });

        return emitter;
    }

    public List<ChatMessage> getChatHistory(String ownerUsername, String sessionId) {
        return historyService.getChatHistory(ownerUsername, sessionId);
    }

    public List<ChatMessage> getChatHistory(String ownerUsername, String sessionId, Long documentId) {
        return historyService.getChatHistory(ownerUsername, sessionId, documentId);
    }

    public void clearChatHistory(String ownerUsername, String sessionId) {
        historyService.clearChatHistory(ownerUsername, sessionId);
    }

    public List<Map<String, Object>> getUniqueSessions(String ownerUsername) {
        return historyService.getUniqueSessions(ownerUsername);
    }

    private List<String> retrieveRelevantChunks(String ownerUsername, Long documentId, String query) {
        if (documentId == null) {
            return Collections.emptyList();
        }

        List<String> allChunks = documentService.getDocumentChunks(documentId, ownerUsername);
        if (allChunks.isEmpty()) {
            return Collections.emptyList();
        }

        // Simple keyword-based retrieval: score chunks by keyword overlap
        String[] queryWords = query.toLowerCase().split("\\W+");
        List<Map.Entry<String, Integer>> scored = new ArrayList<>();

        for (String chunk : allChunks) {
            String lower = chunk.toLowerCase();
            int score = 0;
            for (String word : queryWords) {
                if (word.length() < 3) continue;
                int idx = 0;
                while ((idx = lower.indexOf(word, idx)) >= 0) {
                    score++;
                    idx += word.length();
                }
            }
            scored.add(Map.entry(chunk, score));
        }

        scored.sort((a, b) -> b.getValue().compareTo(a.getValue()));

        int topK = Math.min(3, scored.size());
        List<String> result = new ArrayList<>();
        for (int i = 0; i < topK; i++) {
            if (scored.get(i).getValue() > 0) {
                result.add(scored.get(i).getKey());
            }
        }

        // If no keyword matches, return first 2 chunks as fallback
        if (result.isEmpty() && !allChunks.isEmpty()) {
            result.add(allChunks.get(0));
            if (allChunks.size() > 1) {
                result.add(allChunks.get(1));
            }
        }

        return result;
    }
}