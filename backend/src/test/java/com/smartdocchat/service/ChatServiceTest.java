package com.smartdocchat.service;

import com.smartdocchat.dto.RetrievedChunk;
import com.smartdocchat.entity.ChatMessage;
import com.smartdocchat.repository.DocumentRepository;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.util.Collections;
import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
public class ChatServiceTest {

    // ── Collaborators of ChatService (post-refactor) ──────────────────────
    @Mock
    private AgenticRetrievalService agenticRetrievalService;

    @Mock
    private MessageHandler messageHandler;

    @Mock
    private HistoryService historyService;

    @Mock
    private MlflowTracker mlflowTracker;

    @Mock
    private DocumentRepository documentRepository;

    @Mock
    private RagMetrics ragMetrics;

    @InjectMocks
    private ChatService chatService;

    // ─────────────────────────────────────────────────────────────────────
    // Helpers
    // ─────────────────────────────────────────────────────────────────────

    /** Build a minimal high-confidence RetrievalResult for the direct-RAG path. */
    private AgenticRetrievalService.RetrievalResult highConfidenceResult(RetrievedChunk chunk) {
        return new AgenticRetrievalService.RetrievalResult(
                List.of(chunk),
                Map.of(chunk, "it_security.pdf"),
                Map.of(chunk, 1L),
                0.85,
                "direct",
                false
        );
    }

    // ─────────────────────────────────────────────────────────────────────
    // Tests
    // ─────────────────────────────────────────────────────────────────────

    @Test
    public void testProcessQuery_HighConfidence_Success() {
        // Arrange
        String sessionId = "session-123";
        Long docId = 1L;
        String userMsg = "How do I reset my password?";

        RetrievedChunk chunk = RetrievedChunk.builder()
                .text("Go to profile settings and click reset password.")
                .parentText("Password reset policy: Go to profile settings and click reset password.")
                .score(0.85)
                .build();

        // AgenticRetrievalService returns a high-confidence direct result
        when(agenticRetrievalService.retrieve(
                eq("alice"), anyList(), eq(userMsg), eq(false), eq(false))
        ).thenReturn(highConfidenceResult(chunk));

        // buildContextList delegates to the real implementation logic; stub it
        when(agenticRetrievalService.buildContextList(anyList(), anyMap()))
                .thenReturn(List.of("[it_security.pdf] Password reset policy: Go to profile settings and click reset password."));

        when(messageHandler.buildPrompt(eq(userMsg), anyList())).thenReturn("test prompt");
        when(messageHandler.callLLM("test prompt"))
                .thenReturn("To reset your password, navigate to profile settings and click 'reset'.");

        ChatMessage savedMessage = ChatMessage.builder()
                .id(1L)
                .sessionId(sessionId)
                .ownerUsername("alice")
                .documentId(docId)
                .documentIds(String.valueOf(docId))
                .userMessage(userMsg)
                .aiResponse("To reset your password, navigate to profile settings and click 'reset'.")
                .sourceChunks("[it_security.pdf] Password reset policy: Go to profile settings and click reset password.")
                .build();

        when(historyService.save(any(ChatMessage.class))).thenReturn(savedMessage);

        // Act
        ChatMessage result = chatService.processQuery("alice", sessionId, docId, null, userMsg, false, false);

        // Assert
        assertNotNull(result);
        assertEquals(sessionId, result.getSessionId());
        assertEquals("To reset your password, navigate to profile settings and click 'reset'.", result.getAiResponse());
        verify(historyService, times(1)).save(any(ChatMessage.class));
        verify(messageHandler).callLLM("test prompt");
        verify(ragMetrics).confidence(0.85);
    }

    @Test
    public void testProcessQuery_LowConfidence_FallsBackToGeneralKnowledge() {
        // Arrange
        String sessionId = "session-456";
        Long docId = 2L;
        String userMsg = "Tell me about quantum computing";

        // Agentic loop returns empty chunks with general_knowledge strategy
        AgenticRetrievalService.RetrievalResult lowConfResult =
                new AgenticRetrievalService.RetrievalResult(
                        Collections.emptyList(),
                        Collections.emptyMap(),
                        Collections.emptyMap(),
                        0.20,
                        "general_knowledge",
                        true
                );

        when(agenticRetrievalService.retrieve(
                eq("alice"), anyList(), eq(userMsg), eq(false), eq(false))
        ).thenReturn(lowConfResult);

        when(messageHandler.callLLM(anyString()))
                .thenReturn("Quantum computing uses qubits...");

        ChatMessage savedMessage = ChatMessage.builder()
                .id(2L)
                .sessionId(sessionId)
                .ownerUsername("alice")
                .documentId(docId)
                .userMessage(userMsg)
                .aiResponse("⚠️ [General Knowledge Mode]\n\nQuantum computing uses qubits...")
                .build();

        when(historyService.save(any(ChatMessage.class))).thenReturn(savedMessage);

        // Act
        ChatMessage result = chatService.processQuery("alice", sessionId, docId, null, userMsg, false, false);

        // Assert
        assertNotNull(result);
        verify(ragMetrics).fallback("general_knowledge");
        verify(historyService, times(1)).save(any(ChatMessage.class));
    }
}
