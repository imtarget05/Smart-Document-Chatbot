package com.smartdocchat.service;

import com.smartdocchat.entity.ChatMessage;
import com.smartdocchat.entity.Document;
import com.smartdocchat.repository.ChatMessageRepository;
import com.smartdocchat.repository.DocumentRepository;
import com.smartdocchat.util.OllamaConfig;
import com.smartdocchat.dto.RetrievedChunk;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpMethod;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.test.util.ReflectionTestUtils;
import org.springframework.web.client.RestTemplate;

import java.util.List;
import java.util.Map;
import java.util.Optional;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
public class ChatServiceTest {

    @Mock
    private ChatMessageRepository chatMessageRepository;

    @Mock
    private DocumentRepository documentRepository;

    @Mock
    private EmbeddingService embeddingService;

    @Mock
    private OllamaConfig ollamaConfig;

    @Mock
    private RestTemplate restTemplate;

    @Mock
    private RagMetrics ragMetrics;

    @InjectMocks
    private ChatService chatService;

    @BeforeEach
    public void setUp() {
        ReflectionTestUtils.setField(chatService, "tavilyApiKey", "test-tavily-key");
        ReflectionTestUtils.setField(chatService, "llmMaxAttempts", 1);
        ReflectionTestUtils.setField(chatService, "llmRetryBackoffMs", 0L);
    }

    @Test
    public void testProcessQuery_HighConfidence_Success() {
        // Arrange
        String sessionId = "session-123";
        Long docId = 1L;
        String userMsg = "How do I reset my password?";

        Document doc = Document.builder()
                .id(docId)
                .fileName("it_security.pdf")
                .ownerUsername("alice")
                .vectorCollectionId("vector-it-security")
                .status("READY")
                .build();

        RetrievedChunk chunk = RetrievedChunk.builder()
                .text("Go to profile settings and click reset password.")
                .parentText("Password reset policy: Go to profile settings and click reset password.")
                .score(0.85) // high score >= 0.45, triggers standard RAG
                .build();

        List<RetrievedChunk> chunks = List.of(chunk);

        when(documentRepository.findByIdAndOwnerUsername(docId, "alice")).thenReturn(Optional.of(doc));
        when(embeddingService.searchChunks(userMsg, "vector-it-security", 3)).thenReturn(chunks);
        
        when(ollamaConfig.getChatModel()).thenReturn("deepseek-r1:1.5b");
        when(ollamaConfig.getChatUrl()).thenReturn("http://ollama:11434/api/chat");
        when(ollamaConfig.getTemperature()).thenReturn(0.3);

        Map<String, Object> responseBody = Map.of("message", Map.of("content", "To reset your password, navigate to profile settings and click 'reset'."));
        ResponseEntity<Map> responseEntity = new ResponseEntity<>(responseBody, HttpStatus.OK);

        when(restTemplate.exchange(
                eq("http://ollama:11434/api/chat"),
                eq(HttpMethod.POST),
                any(HttpEntity.class),
                eq(Map.class)
        )).thenReturn(responseEntity);

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

        when(chatMessageRepository.save(any(ChatMessage.class))).thenReturn(savedMessage);

        // Act
        ChatMessage result = chatService.processQuery("alice", sessionId, docId, null, userMsg);

        // Assert
        assertNotNull(result);
        assertEquals(sessionId, result.getSessionId());
        assertEquals("To reset your password, navigate to profile settings and click 'reset'.", result.getAiResponse());
        verify(chatMessageRepository, times(1)).save(any(ChatMessage.class));
        verify(ragMetrics).confidence(0.85);
    }
}
