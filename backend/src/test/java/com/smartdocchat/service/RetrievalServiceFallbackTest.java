package com.smartdocchat.service;

import com.smartdocchat.repository.LegalChunkRepository;
import com.smartdocchat.util.LegalQueryNormalizer;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.mockito.ArgumentMatchers.anyLong;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.lenient;
import static org.mockito.Mockito.when;

/**
 * Hardening: RetrievalService must NEVER throw to its callers. CRAG and
 * ChatService both assume an empty result means "no evidence → abstention".
 * If the repository or owner-isolation check throws, the classic chat path
 * crashes instead of degrading to safe abstention.
 */
@ExtendWith(MockitoExtension.class)
class RetrievalServiceFallbackTest {

    @Mock private DocumentService documentService;
    @Mock private LegalChunkRepository legalChunkRepository;
    private LegalQueryNormalizer normalizer = new LegalQueryNormalizer();
    private RetrievalService service;

    @BeforeEach
    void setUp() {
        service = new RetrievalService(documentService, legalChunkRepository, normalizer);
    }

    @Test
    void documentNotOwnedByUser_propagates_audit404() {
        // owner-isolation failure must throw so the controller can return 404 + audit
        when(documentService.getDocumentById(42L, "alice"))
                .thenThrow(new RuntimeException("not found"));
        org.junit.jupiter.api.Assertions.assertThrows(RuntimeException.class, () ->
                service.retrieve("alice", 42L, "Điều 14 bồi thường thiệt hại", 5));
    }

    @Test
    void repositoryThrows_returnsEmpty_gracefulDegradation() {
        // owner check passes, but repository / chunk source fails — degrade
        when(documentService.getDocumentById(anyLong(), anyString()))
                .thenReturn(null); // ownership ok (returns null when not present in this mock setup)
        when(legalChunkRepository.findByDocumentIdOrderByOrdinalAsc(anyLong()))
                .thenThrow(new RuntimeException("db down"));
        List<RetrievalService.RetrievalResult> result =
                service.retrieve("alice", 1L, "trách nhiệm bồi thường", 5);
        assertNotNull(result);
        assertEquals(0, result.size());
    }

    @Test
    void nullDocumentId_returnsEmpty() {
        List<RetrievalService.RetrievalResult> result =
                service.retrieve("alice", null, "anything", 5);
        assertEquals(0, result.size());
    }

    @Test
    void zeroTopK_returnsEmpty() {
        List<RetrievalService.RetrievalResult> result =
                service.retrieve("alice", 1L, "anything", 0);
        assertEquals(0, result.size());
    }
}
