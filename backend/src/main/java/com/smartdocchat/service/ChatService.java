package com.smartdocchat.service;

import com.smartdocchat.dto.ChatResponse;
import com.smartdocchat.dto.SourceCitation;
import com.smartdocchat.entity.ChatMessage;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import java.io.IOException;
import java.util.*;
import java.util.concurrent.CompletableFuture;

/**
 * ChatService (ChatOrchestrator) — coordinates the RAG/Agentic chat flow by
 * delegating to specialised services.
 *
 * <p>CRAG retrieval logic has been extracted to {@link AgenticRetrievalService}
 * to eliminate the previous code duplication between the sync and streaming
 * paths. Both paths now call the same {@code AgenticRetrievalService.retrieve()}
 * method and only diverge in how the LLM response is delivered (blocking vs. SSE).
 */
@Service
@RequiredArgsConstructor
@Slf4j
public class ChatService {

    private final AgenticRetrievalService agenticRetrievalService;
    private final MessageHandler messageHandler;
    private final HistoryService historyService;
    private final MlflowTracker mlflowTracker;
    private final RagMetrics ragMetrics;

    // -----------------------------------------------------------------------
    // Synchronous path
    // -----------------------------------------------------------------------

    public ChatMessage processQuery(
            String ownerUsername, String sessionId,
            Long documentId, List<Long> documentIds,
            String userMessage, boolean forceDeepThinking, boolean forceWebSearch
    ) {
        ragMetrics.request("sync");
        List<Long> finalDocIds = resolveDocIds(documentId, documentIds);

        // ── Retrieval (shared CRAG logic) ────────────────────────────────────
        AgenticRetrievalService.RetrievalResult retrieval =
                agenticRetrievalService.retrieve(
                        ownerUsername, finalDocIds, userMessage, forceWebSearch, forceDeepThinking);

        ragMetrics.confidence(retrieval.maxScore());
        if (retrieval.usedAgenticLoop()) {
            ragMetrics.fallback(retrieval.strategy().equals("direct") ? "corrective_retrieval" : retrieval.strategy());
        }

        // ── Build context & prompt ───────────────────────────────────────────
        String sourceChunks;
        String aiResponse;
        long startTime = System.currentTimeMillis();

        if (!retrieval.chunks().isEmpty()) {
            List<String> contextList = agenticRetrievalService.buildContextList(
                    retrieval.chunks(), retrieval.chunkFileNames());
            sourceChunks = String.join("\n---\n", contextList);
            String prompt = decoratePrompt(messageHandler.buildPrompt(userMessage, contextList), forceDeepThinking, "");
            aiResponse = messageHandler.callLLM(prompt);
        } else if ("web_search".equals(retrieval.strategy())) {
            List<String> webContexts = messageHandler.searchWeb(userMessage);
            if (!webContexts.isEmpty()) {
                ragMetrics.fallback("web_search");
                sourceChunks = String.join("\n---\n", webContexts);
                String prompt = decoratePrompt(messageHandler.buildPrompt(userMessage, webContexts), forceDeepThinking, "");
                aiResponse = "🌐 [Web Research Mode Activated]\n\n" + messageHandler.callLLM(prompt);
            } else {
                ragMetrics.fallback("general_knowledge");
                aiResponse = "⚠️ [General Knowledge Mode]\n\n" + messageHandler.callLLM(
                        (forceDeepThinking ? "DIRECTIVE: Perform DEEP THINKING. " : "")
                                + "Use internal knowledge.\n\nUser Question: " + userMessage);
                sourceChunks = "";
            }
        } else {
            // general_knowledge
            ragMetrics.fallback("general_knowledge");
            aiResponse = "⚠️ [General Knowledge Mode]\n\n" + messageHandler.callLLM(
                    (forceDeepThinking ? "DIRECTIVE: Perform DEEP THINKING. " : "")
                            + "Use internal knowledge.\n\nUser Question: " + userMessage);
            sourceChunks = "";
        }

        mlflowTracker.logChatExchange(userMessage, aiResponse, System.currentTimeMillis() - startTime);

        // ── Persist ──────────────────────────────────────────────────────────
        ChatMessage chatMessage = ChatMessage.builder()
                .sessionId(sessionId)
                .ownerUsername(ownerUsername)
                .documentId(documentId != null ? documentId : (finalDocIds.isEmpty() ? null : finalDocIds.get(0)))
                .documentIds(joinIds(finalDocIds))
                .userMessage(userMessage)
                .aiResponse(aiResponse)
                .sourceChunks(sourceChunks.isEmpty() ? null : sourceChunks)
                .build();

        return historyService.save(chatMessage);
    }

    // -----------------------------------------------------------------------
    // Streaming path (SSE)
    // -----------------------------------------------------------------------

    public SseEmitter processQueryStream(
            String ownerUsername, String sessionId,
            Long documentId, List<Long> documentIds,
            String userMessage, boolean forceDeepThinking, boolean forceWebSearch
    ) {
        SseEmitter emitter = new SseEmitter(180_000L);
        ragMetrics.request("stream");

        CompletableFuture.runAsync(() -> {
            try {
                List<Long> finalDocIds = resolveDocIds(documentId, documentIds);

                // ── Retrieval (shared CRAG logic) ────────────────────────────
                AgenticRetrievalService.RetrievalResult retrieval =
                        agenticRetrievalService.retrieve(
                                ownerUsername, finalDocIds, userMessage, forceWebSearch, forceDeepThinking);

                ragMetrics.confidence(retrieval.maxScore());
                if (retrieval.usedAgenticLoop()) {
                    ragMetrics.fallback(retrieval.strategy().equals("direct") ? "corrective_retrieval" : retrieval.strategy());
                }

                // ── Build prompt & metadata ──────────────────────────────────
                String prompt;
                String sourceChunks;
                String prefix = "";

                if (!retrieval.chunks().isEmpty()) {
                    List<String> contextList = agenticRetrievalService.buildContextList(
                            retrieval.chunks(), retrieval.chunkFileNames());
                    sourceChunks = String.join("\n---\n", contextList);
                    prompt = decoratePrompt(messageHandler.buildPrompt(userMessage, contextList), forceDeepThinking, "");
                    if (retrieval.usedAgenticLoop()) {
                        prefix = (forceDeepThinking ? "🧠 [DeepThinking Mode]" : "🤖 [Agentic Optimization]") + "\n\n";
                    }
                } else if ("web_search".equals(retrieval.strategy())) {
                    log.info("Stream: performing web search fallback");
                    List<String> webContexts = messageHandler.searchWeb(userMessage);
                    if (!webContexts.isEmpty()) {
                        ragMetrics.fallback("web_search");
                        sourceChunks = String.join("\n---\n", webContexts);
                        prompt = decoratePrompt(messageHandler.buildPrompt(userMessage, webContexts), forceDeepThinking, "");
                        prefix = "🌐 [Web Research Mode Activated]\n\n";
                    } else {
                        ragMetrics.fallback("general_knowledge");
                        prompt = (forceDeepThinking ? "DIRECTIVE: DEEP THINKING. " : "")
                                + "Use internal knowledge.\n\nUser Question: " + userMessage;
                        prefix = "⚠️ [General Knowledge Mode]\n\n";
                        sourceChunks = "";
                    }
                } else {
                    ragMetrics.fallback("general_knowledge");
                    prompt = (forceDeepThinking ? "DIRECTIVE: DEEP THINKING. " : "")
                            + "Use internal knowledge.\n\nUser Question: " + userMessage;
                    prefix = "⚠️ [General Knowledge Mode]\n\n";
                    sourceChunks = "";
                }

                // ── Metadata SSE event ────────────────────────────────────────
                Map<String, Object> metaEvent = new HashMap<>();
                metaEvent.put("sourceChunks", sourceChunks.isEmpty() ? null : sourceChunks);
                metaEvent.put("prefix", prefix);
                metaEvent.put("documentId", documentId != null ? documentId : (finalDocIds.isEmpty() ? null : finalDocIds.get(0)));
                metaEvent.put("documentIds", finalDocIds);
                emitter.send(SseEmitter.event().name("metadata").data(metaEvent));

                if (!prefix.isEmpty()) {
                    emitter.send(SseEmitter.event().name("chunk").data(prefix));
                }

                // ── Stream LLM tokens ─────────────────────────────────────────
                StringBuilder aiResponseBuilder = new StringBuilder(prefix);
                final String finalPrompt = prompt;
                final String finalSourceChunks = sourceChunks;
                final long startTime = System.currentTimeMillis();

                messageHandler.streamLLM(finalPrompt, token -> {
                    aiResponseBuilder.append(token);
                    try {
                        emitter.send(SseEmitter.event().name("chunk").data(token));
                    } catch (IOException e) {
                        throw new IllegalStateException("SSE client disconnected during stream", e);
                    }
                });

                String fullResponse = aiResponseBuilder.toString();
                long latencyMs = System.currentTimeMillis() - startTime;
                mlflowTracker.logChatExchange(userMessage, fullResponse, latencyMs);

                // ── Persist ───────────────────────────────────────────────────
                ChatMessage chatMessage = ChatMessage.builder()
                        .sessionId(sessionId)
                        .ownerUsername(ownerUsername)
                        .documentId(documentId != null ? documentId : (finalDocIds.isEmpty() ? null : finalDocIds.get(0)))
                        .documentIds(joinIds(finalDocIds))
                        .userMessage(userMessage)
                        .aiResponse(fullResponse)
                        .sourceChunks(finalSourceChunks.isEmpty() ? null : finalSourceChunks)
                        .build();
                ChatMessage saved = historyService.save(chatMessage);

                // ── Final SSE complete event ───────────────────────────────────
                List<SourceCitation> citations = Collections.emptyList();
                ChatResponse responseDto = historyService.convertToResponse(
                        saved, retrieval.strategy(), retrieval.maxScore(), latencyMs, null, citations);
                emitter.send(SseEmitter.event().name("complete").data(responseDto));
                emitter.complete();

                mlflowTracker.logStructuredRequest(userMessage, retrieval.chunks().size(),
                        retrieval.maxScore(), retrieval.strategy(), latencyMs, "success");

            } catch (Exception e) {
                log.error("Error in streaming task: {}", e.getMessage(), e);
                ragMetrics.streamError();
                try {
                    emitter.send(SseEmitter.event().name("error").data(e.getMessage()));
                    emitter.completeWithError(e);
                } catch (Exception ex) {
                    // Ignored — client already disconnected
                }
            }
        });

        return emitter;
    }

    // -----------------------------------------------------------------------
    // History / Session API — delegated to HistoryService
    // -----------------------------------------------------------------------

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

    // -----------------------------------------------------------------------
    // Private helpers
    // -----------------------------------------------------------------------

    private List<Long> resolveDocIds(Long documentId, List<Long> documentIds) {
        List<Long> result = new ArrayList<>();
        if (documentIds != null && !documentIds.isEmpty()) {
            result.addAll(documentIds);
        } else if (documentId != null) {
            result.add(documentId);
        }
        return result;
    }

    /** Prepend a mode-specific directive to the prompt when deep-thinking is active. */
    private String decoratePrompt(String prompt, boolean forceDeepThinking, String prefix) {
        if (!forceDeepThinking) return prompt;
        return "DIRECTIVE: Analyze the context with extreme depth. Perform multi-step reasoning before answering.\n\n" + prompt;
    }

    private String joinIds(List<Long> ids) {
        if (ids == null || ids.isEmpty()) return null;
        List<String> parts = new ArrayList<>();
        for (Long id : ids) parts.add(id.toString());
        return String.join(",", parts);
    }
}
