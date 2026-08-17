package com.smartdocchat.service;

import com.smartdocchat.config.CragConfig;
import com.smartdocchat.dto.ChatRequest;
import com.smartdocchat.dto.ChatResponse;
import com.smartdocchat.entity.ChatMessage;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import java.io.IOException;
import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.concurrent.CompletableFuture;

@Service
@RequiredArgsConstructor
@Slf4j
public class ChatService {

    private final MessageHandler messageHandler;
    private final HistoryService historyService;
    private final CragConfig cragConfig;
    private final RetrievalService retrievalService;
    private final QueryReformulator queryReformulator;
    private final WebSearchService webSearchService;

    /** Outcome of a Corrective RAG pass over the classic chat endpoints. */
    private record CragResult(
            List<RetrievalService.RetrievalResult> results,
            List<String> webSnippets,
            double confidenceScore,
            String strategy
    ) {
        CragResult() {
            this(Collections.emptyList(), Collections.emptyList(), 0.0, "direct");
        }

        /** Context fed to the prompt: chunks for retrieval, snippets for web search. */
        List<String> contextChunks() {
            return "web_search".equals(strategy)
                    ? webSnippets
                    : results.stream().map(RetrievalService.RetrievalResult::chunk).toList();
        }
    }

    // ------------------------------------------------------------------
    // Classic (sync) chat
    // ------------------------------------------------------------------

    public ChatResponse processQuery(String ownerUsername, ChatRequest request) {
        String userMessage = request.getMessage();
        CragResult crag = runCrag(ownerUsername, request.getDocumentId(), userMessage, request.isWebSearch());

        String aiResponse = strategyPrefix(crag) + messageHandler.callLLM(buildPromptForStrategy(userMessage, crag));
        ChatMessage saved = historyService.save(ChatMessage.builder()
                .sessionId(request.getSessionId())
                .ownerUsername(ownerUsername)
                .documentId(request.getDocumentId())
                .userMessage(userMessage)
                .aiResponse(aiResponse)
                .sourceChunks(buildSourceChunks(crag))
                .build());
        return toResponse(saved, crag);
    }

    public SseEmitter processQueryStream(String ownerUsername, ChatRequest request) {
        SseEmitter emitter = new SseEmitter(180_000L);

        CompletableFuture.runAsync(() -> {
            try {
                CragResult crag = runCrag(ownerUsername, request.getDocumentId(), request.getMessage(), request.isWebSearch());

                // Send metadata (sources + strategy) up front, before the token stream.
                Map<String, Object> metaEvent = new LinkedHashMap<>();
                metaEvent.put("sourceChunks", buildSourceChunks(crag));
                metaEvent.put("documentId", request.getDocumentId());
                metaEvent.put("confidenceScore", round(crag.confidenceScore()));
                metaEvent.put("confidence", confidenceLabel(crag.confidenceScore()));
                metaEvent.put("ragStrategy", crag.strategy());
                emitter.send(SseEmitter.event().name("metadata").data(metaEvent));

                String prefix = strategyPrefix(crag);
                String prompt = buildPromptForStrategy(request.getMessage(), crag);
                StringBuilder aiResponseBuilder = new StringBuilder();

                if (!prefix.isEmpty()) {
                    aiResponseBuilder.append(prefix);
                    emitter.send(SseEmitter.event().name("chunk").data(prefix));
                }

                messageHandler.streamLLM(prompt, token -> {
                    aiResponseBuilder.append(token);
                    try {
                        emitter.send(SseEmitter.event().name("chunk").data(token));
                    } catch (IOException e) {
                        throw new IllegalStateException("SSE client disconnected during stream", e);
                    }
                });

                ChatMessage saved = historyService.save(ChatMessage.builder()
                        .sessionId(request.getSessionId())
                        .ownerUsername(ownerUsername)
                        .documentId(request.getDocumentId())
                        .userMessage(request.getMessage())
                        .aiResponse(aiResponseBuilder.toString())
                        .sourceChunks(buildSourceChunks(crag))
                        .build());

                emitter.send(SseEmitter.event().name("complete").data(toResponse(saved, crag)));
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

    // ------------------------------------------------------------------
    // Corrective RAG (CRAG) orchestration
    // ------------------------------------------------------------------

    private CragResult runCrag(String ownerUsername, Long documentId, String query, boolean webSearchRequested) {
        List<RetrievalService.RetrievalResult> results =
                retrievalService.retrieve(ownerUsername, documentId, query, cragConfig.getTopK());
        double confidence = results.isEmpty() ? 0.0 : results.get(0).score();
        String strategy = "direct";

        if (confidence >= cragConfig.getConfidenceThreshold()) {
            return new CragResult(results, List.of(), confidence, strategy);
        }

        // Corrective loop: reformulate (if possible) and re-retrieve.
        List<String> variants = queryReformulator.reformulate(query, cragConfig.getMaxReformulations());
        Map<String, RetrievalService.RetrievalResult> merged = new LinkedHashMap<>();
        results.forEach(r -> merged.put(r.chunk(), r));
        double bestScore = confidence;
        strategy = "corrective";

        for (String variant : variants) {
            List<RetrievalService.RetrievalResult> vResults =
                    retrievalService.retrieve(ownerUsername, documentId, variant, cragConfig.getTopK());
            for (RetrievalService.RetrievalResult r : vResults) {
                bestScore = Math.max(bestScore, r.score());
                merged.putIfAbsent(r.chunk(), r);
            }
        }
        confidence = bestScore;

        List<RetrievalService.RetrievalResult> topMerged = keepTopK(merged.values(), cragConfig.getTopK());
        if (confidence >= cragConfig.getConfidenceThreshold()) {
            return new CragResult(topMerged, List.of(), confidence, strategy);
        }

        // Still low -> web search (if configured/requested) else general knowledge.
        boolean useWeb = webSearchRequested
                || (webSearchService.isConfigured() && cragConfig.isWebSearchEnabled());
        if (useWeb) {
            Optional<List<String>> web = webSearchService.search(query);
            if (web.isPresent()) {
                return new CragResult(List.of(), web.get(), confidence, "web_search");
            }
        }
        return new CragResult(List.of(), List.of(), confidence, "general_knowledge");
    }

    private List<RetrievalService.RetrievalResult> keepTopK(
            java.util.Collection<RetrievalService.RetrievalResult> collection, int topK) {
        List<RetrievalService.RetrievalResult> sorted = new ArrayList<>(collection);
        sorted.sort((a, b) -> Double.compare(b.score(), a.score()));
        return sorted.size() > topK ? sorted.subList(0, topK) : sorted;
    }

    private String buildPromptForStrategy(String query, CragResult crag) {
        return switch (crag.strategy()) {
            case "web_search" -> messageHandler.buildWebSearchPrompt(query, crag.contextChunks());
            case "general_knowledge" -> messageHandler.buildGeneralKnowledgePrompt(query);
            default -> messageHandler.buildPrompt(query, crag.contextChunks());
        };
    }

    private String strategyPrefix(CragResult crag) {
        return switch (crag.strategy()) {
            case "web_search" -> "[Web Search]\n\n";
            case "general_knowledge" -> "[General Knowledge]\n\n";
            default -> "";
        };
    }

    private String buildSourceChunks(CragResult crag) {
        List<String> context = crag.contextChunks();
        return context.isEmpty() ? null : String.join("\n---\n", context);
    }

    // ------------------------------------------------------------------
    // Response mapping
    // ------------------------------------------------------------------

    private ChatResponse toResponse(ChatMessage message, CragResult crag) {
        return ChatResponse.builder()
                .id(message.getId())
                .sessionId(message.getSessionId())
                .userMessage(message.getUserMessage())
                .aiResponse(message.getAiResponse())
                .sourceChunks(message.getSourceChunks())
                .documentId(message.getDocumentId())
                .confidence(confidenceLabel(crag.confidenceScore()))
                .confidenceScore(round(crag.confidenceScore()))
                .ragStrategy(crag.strategy())
                .sources(buildSources(message.getDocumentId(), crag))
                .build();
    }

    private List<Map<String, Object>> buildSources(Long documentId, CragResult crag) {
        List<Map<String, Object>> sources = new ArrayList<>();
        for (RetrievalService.RetrievalResult r : crag.results()) {
            String content = r.chunk();
            if (content.length() > 300) {
                content = content.substring(0, 300);
            }
            Map<String, Object> s = new LinkedHashMap<>();
            s.put("documentId", documentId);
            s.put("content", content);
            s.put("score", round(r.score()));
            s.put("sourceType", "document");
            sources.add(s);
        }
        return sources;
    }

    private String confidenceLabel(double score) {
        if (score >= 0.70) {
            return "high";
        }
        if (score >= 0.6) {
            return "medium";
        }
        return "low";
    }

    private double round(double value) {
        return Math.round(value * 100.0) / 100.0;
    }
}