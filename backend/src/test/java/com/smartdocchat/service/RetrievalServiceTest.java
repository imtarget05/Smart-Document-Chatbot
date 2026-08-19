package com.smartdocchat.service;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.ArgumentMatchers.anyLong;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class RetrievalServiceTest {

    @Mock private DocumentService documentService;

    private RetrievalService retrievalService;

    @BeforeEach
    void setUp() {
        retrievalService = new RetrievalService(documentService);
    }

    @Test
    void returnsEmptyForNullDocumentOrNonPositiveTopK() {
        assertTrue(retrievalService.retrieve("alice", null, "query", 5).isEmpty());
        assertTrue(retrievalService.retrieve("alice", 1L, "query", 0).isEmpty());
    }

    @Test
    void returnsEmptyWhenNoChunksOrQueryHasNoWords() {
        when(documentService.getDocumentChunks(1L, "alice")).thenReturn(List.of());
        assertTrue(retrievalService.retrieve("alice", 1L, "query", 5).isEmpty());

        when(documentService.getDocumentChunks(2L, "alice"))
                .thenReturn(List.of("some meaningful chunk here"));
        assertTrue(retrievalService.retrieve("alice", 2L, "hi", 5).isEmpty());
    }

    @Test
    void scoresChunksAndReturnsTopKAboveZero() {
        when(documentService.getDocumentChunks(1L, "alice"))
                .thenReturn(List.of("insurance policy renewal process described here",
                        "completely unrelated talk about weather today"));
        when(documentService.getDocumentChunks(2L, "alice")).thenReturn(
                java.util.Arrays.asList("alpha beta gamma delta", "alpha alpha alpha", null, "  "));

        List<RetrievalService.RetrievalResult> top =
                retrievalService.retrieve("alice", 1L, "insurance renewal", 3);

        assertEquals(1, top.size());
        assertTrue(top.get(0).score() > 0.0);
        assertTrue(top.get(0).chunk().contains("insurance policy renewal"));

        List<RetrievalService.RetrievalResult> top2 =
                retrievalService.retrieve("alice", 2L, "alpha beta gamma delta", 10);

        assertEquals(2, top2.size());
        assertTrue(top2.get(0).score() >= top2.get(1).score());
    }

    @Test
    void skipsNullAndBlankChunksWithoutFailing() {
        when(documentService.getDocumentChunks(1L, "alice"))
                .thenReturn(java.util.Arrays.asList("word one", null, " ", "word two"));
        assertEquals(2, retrievalService.retrieve("alice", 1L, "word one two", 10).size());
    }
}