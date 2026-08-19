package com.smartdocchat.service;

import com.smartdocchat.config.CragConfig;
import com.smartdocchat.dto.ChatRequest;
import com.smartdocchat.dto.ChatResponse;
import com.smartdocchat.entity.ChatMessage;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyInt;
import static org.mockito.ArgumentMatchers.anyList;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.lenient;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class ChatServiceExtraTest {

    @Mock private MessageHandler messageHandler;
    @Mock private HistoryService historyService;
    @Mock private RetrievalService retrievalService;
    @Mock private QueryReformulator queryReformulator;
    @Mock private WebSearchService webSearchService;

    private CragConfig cragConfig;
    private ChatService chatService;

    @BeforeEach
    void setUp() {
        cragConfig = new CragConfig();
        chatService = new ChatService(messageHandler, historyService, cragConfig, retrievalService,
                queryReformulator, webSearchService);
        lenient().when(historyService.save(any(ChatMessage.class))).thenAnswer(inv -> inv.getArgument(0));
    }

    private ChatRequest request(String message, boolean webSearch) {
        return ChatRequest.builder()
                .sessionId("session-1")
                .documentId(1L)
                .message(message)
                .webSearch(webSearch)
                .build();
    }

    @Test
    void mediumConfidenceIsLabelledAndLongSourcesAreTruncated() {
        String longChunk = "x".repeat(350);
        when(retrievalService.retrieve(eq("alice"), eq(1L), anyString(), anyInt()))
                .thenReturn(List.of(new RetrievalService.RetrievalResult(longChunk, 0.65)));
        when(messageHandler.buildPrompt(anyString(), anyList())).thenReturn("prompt");
        when(messageHandler.callLLM("prompt")).thenReturn("answer");

        ChatResponse response = chatService.processQuery("alice", request("question?", false));

        assertEquals("medium", response.getConfidence());
        assertEquals(0.65, response.getConfidenceScore());
        assertEquals(350, response.getSourceChunks().length());
        assertEquals(300, response.getSources().get(0).get("content").toString().length());
        assertEquals("document", response.getSources().get(0).get("sourceType"));
    }

    @Test
    void correctiveLoopMergesReformulatedEvidence() {
        when(retrievalService.retrieve(eq("alice"), eq(1L), eq("original question"), anyInt()))
                .thenReturn(List.of(new RetrievalService.RetrievalResult("old chunk", 0.5)));
        when(queryReformulator.reformulate("original question", cragConfig.getMaxReformulations()))
                .thenReturn(List.of("variant one"));
        when(retrievalService.retrieve(eq("alice"), eq(1L), eq("variant one"), anyInt()))
                .thenReturn(List.of(
                        new RetrievalService.RetrievalResult("old chunk", 0.5),
                        new RetrievalService.RetrievalResult("new strong chunk", 0.9)));
        when(messageHandler.buildPrompt(anyString(), anyList())).thenReturn("corrective prompt");
        when(messageHandler.callLLM("corrective prompt")).thenReturn("corrected answer");

        ChatResponse response = chatService.processQuery("alice", request("original question", false));

        assertEquals("corrective", response.getRagStrategy());
        assertEquals(2, response.getSources().size());
        assertTrue(response.getAiResponse().startsWith("corrected answer"));
    }

    @Test
    void explicitWebSearchRequestWithEmptyResultsFallsBackToGeneralKnowledge() {
        when(retrievalService.retrieve(eq("alice"), eq(1L), anyString(), anyInt())).thenReturn(List.of());
        when(queryReformulator.reformulate(anyString(), anyInt())).thenReturn(List.of());
        when(webSearchService.search(anyString())).thenReturn(java.util.Optional.empty());
        when(messageHandler.buildGeneralKnowledgePrompt(anyString())).thenReturn("general prompt");
        when(messageHandler.callLLM("general prompt")).thenReturn("general answer");

        ChatResponse response = chatService.processQuery("alice", request("Who? maybe web?", true));

        assertEquals("general_knowledge", response.getRagStrategy());
        assertEquals("[General Knowledge]\n\ngeneral answer", response.getAiResponse());
    }

    @Test
    void generalKnowledgeFallbackPrefixesResponse() {
        when(retrievalService.retrieve(eq("alice"), eq(1L), anyString(), anyInt())).thenReturn(List.of());
        when(queryReformulator.reformulate(anyString(), anyInt())).thenReturn(List.of());
        when(messageHandler.buildGeneralKnowledgePrompt(anyString())).thenReturn("general prompt");
        when(messageHandler.callLLM("general prompt")).thenReturn("general answer");

        ChatResponse response = chatService.processQuery("alice", request("question?", false));

        assertEquals("general_knowledge", response.getRagStrategy());
        assertTrue(response.getAiResponse().startsWith("[General Knowledge]"));
    }

    @Test
    void webSearchStrategyPrefixesResponsesWithSources() {
        when(retrievalService.retrieve(eq("alice"), eq(1L), anyString(), anyInt())).thenReturn(List.of());
        when(queryReformulator.reformulate(anyString(), anyInt())).thenReturn(List.of());
        when(webSearchService.search(anyString()))
                .thenReturn(java.util.Optional.of(List.of("a sufficiently long web snippet for grounding the answer")));
        when(messageHandler.buildWebSearchPrompt(anyString(), anyList())).thenReturn("web prompt");
        when(messageHandler.callLLM("web prompt")).thenReturn("web answer");

        ChatResponse response = chatService.processQuery("alice", request("question?", true));

        assertEquals("web_search", response.getRagStrategy());
        assertTrue(response.getAiResponse().startsWith("[Web Search]"));
        assertTrue(response.getSourceChunks().contains("web snippet"));
    }

    @Test
    void sessionAccessorsDelegateToHistory() {
        ChatMessage msg = ChatMessage.builder().id(1L).sessionId("s1").build();
        when(historyService.getChatHistory("alice", "s1")).thenReturn(List.of(msg));
        when(historyService.getChatHistory("alice", "s1", 1L)).thenReturn(List.of(msg));
        when(historyService.getUniqueSessions("alice"))
                .thenReturn(List.of(Map.of("sessionId", "s1")));

        assertEquals(1, chatService.getChatHistory("alice", "s1").size());
        assertEquals(1, chatService.getChatHistory("alice", "s1", 1L).size());
        assertEquals(1, chatService.getUniqueSessions("alice").size());
        chatService.clearChatHistory("alice", "s1");
    }
}