package com.smartdocchat.service;

import com.smartdocchat.config.CragConfig;
import com.smartdocchat.dto.ChatRequest;
import com.smartdocchat.dto.ChatResponse;
import com.smartdocchat.entity.ChatMessage;
import com.smartdocchat.entity.Document;
import com.smartdocchat.entity.SourceType;
import com.smartdocchat.security.PromptInjectionDetector;
import com.smartdocchat.util.LegalQueryNormalizer;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.mockito.ArgumentMatchers.anyInt;
import static org.mockito.Mockito.lenient;
import static org.mockito.Mockito.when;

/**
 * Decision 13: structured citation metadata in API responses.
 */
@ExtendWith(MockitoExtension.class)
class ChatServiceCitationTest {

    @Mock private MessageHandler messageHandler;
    @Mock private HistoryService historyService;
    @Mock private RetrievalService retrievalService;
    @Mock private QueryReformulator queryReformulator;
    @Mock private WebSearchService webSearchService;
    @Mock private PromptInjectionDetector promptInjectionDetector;
    @Mock private DocumentService documentService;
    @Mock private AgentClient agentClient;
    private LegalQueryNormalizer normalizer = new LegalQueryNormalizer();

    private CragConfig cragConfig;
    private ChatService chatService;

    @BeforeEach
    void setUp() {
        cragConfig = new CragConfig();
        chatService = new ChatService(messageHandler, historyService, cragConfig, retrievalService,
                queryReformulator, webSearchService,
                promptInjectionDetector,
                new com.smartdocchat.config.PromptInjectionProperties(),
                new com.smartdocchat.metrics.RagMetrics(new io.micrometer.core.instrument.simple.SimpleMeterRegistry()),
                documentService, new com.smartdocchat.observability.LangfuseService(), agentClient,
                normalizer);
        lenient().when(promptInjectionDetector.analyze(org.mockito.ArgumentMatchers.anyString()))
                .thenReturn(PromptInjectionDetector.Severity.NONE);
        lenient().when(historyService.save(org.mockito.ArgumentMatchers.any(ChatMessage.class)))
                .thenAnswer(inv -> inv.getArgument(0));
    }

    @Test
    void responseSourcesCarryStructuredCitationMetadata() {
        Document doc = Document.builder()
                .title("Bộ luật Test")
                .documentNumber("01/2026/TEST")
                .sourceType(SourceType.USER)
                .build();
        when(documentService.getDocumentById(7L, "alice")).thenReturn(doc);
        when(retrievalService.retrieve(org.mockito.ArgumentMatchers.eq("alice"),
                org.mockito.ArgumentMatchers.eq(7L), org.mockito.ArgumentMatchers.anyString(), anyInt()))
                .thenReturn(List.of(new RetrievalService.RetrievalResult(
                        "Điều 2. Quyền và nghĩa vụ. Người kiểm thử có quyền chạy bộ kiểm thử.", 0.9, 42L, "2", "1", "a")));

        ChatResponse resp = chatService.processQuery("alice",
                ChatRequest.builder().message("quyền của người kiểm thử là gì").documentId(7L).build());

        assertEquals(1, resp.getSources().size());
        var s = resp.getSources().get(0);
        assertEquals("2", s.get("article"));
        assertEquals("1", s.get("clause"));
        assertEquals("a", s.get("point"));
        assertEquals(42L, s.get("chunkId"));
        assertEquals("Bộ luật Test", s.get("documentTitle"));
        assertEquals("01/2026/TEST", s.get("documentNumber"));
        assertEquals("USER", s.get("sourceType"));
    }

    @Test
    void legacyChunksStillProduceSourcesWithoutLegalMetadata() {
        when(documentService.getDocumentById(8L, "alice")).thenReturn(Document.builder().build());
        when(retrievalService.retrieve(org.mockito.ArgumentMatchers.eq("alice"),
                org.mockito.ArgumentMatchers.eq(8L), org.mockito.ArgumentMatchers.anyString(), anyInt()))
                .thenReturn(List.of(new RetrievalService.RetrievalResult("generic chunk text", 0.99)));
        lenient().when(queryReformulator.reformulate(org.mockito.ArgumentMatchers.anyString(), anyInt()))
                .thenReturn(List.of());

        ChatResponse resp = chatService.processQuery("alice",
                ChatRequest.builder().message("generic question").documentId(8L).build());

        var s = resp.getSources().get(0);
        assertEquals(null, s.get("article"));   // null, never fabricated
        assertEquals(null, s.get("clause"));
        assertEquals(null, s.get("chunkId"));
    }
}
