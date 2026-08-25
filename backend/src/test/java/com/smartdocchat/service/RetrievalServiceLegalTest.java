package com.smartdocchat.service;

import com.smartdocchat.entity.Document;
import com.smartdocchat.entity.LegalChunk;
import com.smartdocchat.repository.LegalChunkRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.ArgumentMatchers.anyLong;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.lenient;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

/**
 * Decision 13: retrieval over addressable legal evidence units, legacy
 * fallback behaviour and owner isolation.
 */
@ExtendWith(MockitoExtension.class)
class RetrievalServiceLegalTest {

    @Mock private DocumentService documentService;
    @Mock private LegalChunkRepository legalChunkRepository;

    private RetrievalService retrievalService;

    @BeforeEach
    void setUp() {
        retrievalService = new RetrievalService(documentService, legalChunkRepository, new com.smartdocchat.util.LegalQueryNormalizer());
    }

    private LegalChunk chunk(long id, int ordinal, String article, String clause,
                             String point, String content) {
        return LegalChunk.builder()
                .id(id).documentId(1L).ordinal(ordinal)
                .articleNumber(article).clauseNumber(clause).pointLabel(point)
                .content(content).build();
    }

    @Test
    void returnsStructuredMetadataForLegalDocuments() {
        when(documentService.getDocumentById(1L, "alice")).thenReturn(new Document());
        when(legalChunkRepository.findByDocumentIdOrderByOrdinalAsc(1L)).thenReturn(List.of(
                chunk(10L, 0, "1", null, null, "Điều 1 quy định phạm vi điều chỉnh của văn bản này."),
                chunk(11L, 1, "2", "1", "a", "Điểm a khoản 1 điều 2 nêu quyền của người kiểm thử.")));

        List<RetrievalService.RetrievalResult> results =
                retrievalService.retrieve("alice", 1L, "phạm vi điều chỉnh văn bản", 5);

        // Only the genuinely relevant unit passes the evidence threshold
        // (Decision 15); the unrelated clause-2 unit is correctly filtered.
        assertEquals(1, results.size());
        assertEquals(10L, results.get(0).chunkId());
        assertEquals("1", results.get(0).article());
        assertNull(results.get(0).clause());
        assertTrue(results.get(0).score() > 0.3);
    }

    @Test
    void fallsBackToLegacyChunksWhenNoLegalStructure() {
        when(documentService.getDocumentById(2L, "alice")).thenReturn(new Document());
        when(legalChunkRepository.findByDocumentIdOrderByOrdinalAsc(2L)).thenReturn(List.of());
        when(documentService.getDocumentChunks(2L, "alice"))
                .thenReturn(List.of("plain generic chunk about insurance renewal"));

        List<RetrievalService.RetrievalResult> results =
                retrievalService.retrieve("alice", 2L, "insurance renewal", 3);

        assertEquals(1, results.size());
        assertNull(results.get(0).chunkId());   // no fabricated metadata
        assertNull(results.get(0).article());
    }

    @Test
    void enforcesOwnerIsolationBeforeReadingChunks() {
        when(documentService.getDocumentById(3L, "bob"))
                .thenThrow(new RuntimeException("Document not found with id: 3"));

        assertThrows(RuntimeException.class,
                () -> retrievalService.retrieve("bob", 3L, "anything at all", 5));
        // Chunks must never be read for a non-owner.
        verify(legalChunkRepository, never()).findByDocumentIdOrderByOrdinalAsc(anyLong());
        verify(documentService, never()).getDocumentChunks(anyLong(), anyString());
    }

    @Test
    void legalMetadataNeverFabricatedForUnlabelledUnits() {
        when(documentService.getDocumentById(4L, "alice")).thenReturn(new Document());
        when(legalChunkRepository.findByDocumentIdOrderByOrdinalAsc(4L)).thenReturn(List.of(
                chunk(20L, 0, null, null, null, "Preamble text without any legal labels here.")));

        List<RetrievalService.RetrievalResult> results =
                retrievalService.retrieve("alice", 4L, "preamble text labels", 5);

        assertEquals(1, results.size());
        assertNull(results.get(0).article());
        assertNull(results.get(0).clause());
        assertNull(results.get(0).point());
    }
}