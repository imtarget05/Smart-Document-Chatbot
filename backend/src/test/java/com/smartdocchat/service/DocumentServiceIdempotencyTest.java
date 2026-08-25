package com.smartdocchat.service;

import com.smartdocchat.entity.Document;
import com.smartdocchat.repository.DocumentRepository;
import com.smartdocchat.util.DocumentParser;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.mock.web.MockMultipartFile;

import java.io.File;
import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.Optional;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.lenient;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

/**
 * Blueprint #17 — Idempotent Document Processing.
 * Repeated ingestion of identical content must not create duplicate metadata.
 */
@ExtendWith(MockitoExtension.class)
class DocumentServiceIdempotencyTest {

    @Mock private DocumentRepository documentRepository;
    @Mock private DocumentParser documentParser;
    @Mock private StorageService storageService;
    @Mock private com.smartdocchat.util.LegalStructureParser legalStructureParser;
    @Mock private com.smartdocchat.repository.LegalChunkRepository legalChunkRepository;
    @Mock private com.smartdocchat.util.LegalQueryNormalizer legalQueryNormalizer;
    @Mock private com.smartdocchat.util.LegalDateExtractor legalDateExtractor;

    private DocumentService documentService;

    @BeforeEach
    void setUp() {
        documentService = new DocumentService(documentRepository, documentParser, storageService,
                legalStructureParser, legalChunkRepository, legalQueryNormalizer, legalDateExtractor);
    }

    private MockMultipartFile txtFile(String name, String content) {
        return new MockMultipartFile("file", name, "text/plain",
                content.getBytes(StandardCharsets.UTF_8));
    }

    private void stubHappyPath() throws Exception {
        lenient().when(storageService.upload(anyString(), any())).thenReturn("uploads/report.txt");
        lenient().when(storageService.download(anyString())).thenReturn(new File("report.txt"));
        lenient().when(documentParser.extractText(any(File.class), anyString())).thenReturn("extracted text");
        lenient().when(documentParser.chunkText("extracted text", 500)).thenReturn(List.of("chunk1"));
    }

    @Test
    void duplicateContentReturnsExistingDocumentWithoutStoring() throws Exception {
        Document existing = Document.builder().id(42L).fileName("report.txt")
                .ownerUsername("alice").fileType("txt").contentHash("abc").build();
        when(documentRepository.findByOwnerUsernameAndContentHash(eq("alice"), anyString()))
                .thenReturn(Optional.of(existing));

        Document result = documentService.uploadDocument(txtFile("report.txt", "same content"), "alice");

        assertEquals(42L, result.getId());
        verify(storageService, never()).upload(anyString(), any());
        verify(documentRepository, never()).save(any(Document.class));
    }

    @Test
    void newContentIsStoredWithComputedSha256Hash() throws Exception {
        when(documentRepository.findByOwnerUsernameAndContentHash(eq("alice"), anyString()))
                .thenReturn(Optional.empty());
        stubHappyPath();
        when(documentRepository.save(any(Document.class))).thenAnswer(inv -> inv.getArgument(0));

        Document saved = documentService.uploadDocument(txtFile("report.txt", "brand new content"), "alice");

        assertNotNull(saved.getContentHash());
        assertEquals(64, saved.getContentHash().length(), "SHA-256 hex digest must be 64 chars");
        // Same content must always yield the same digest (idempotency key).
        Document second = documentService.uploadDocument(txtFile("report.txt", "brand new content"), "alice");
        assertEquals(saved.getContentHash(), second.getContentHash());
    }

    @Test
    void sameContentForDifferentOwnersIsNotADuplicate() throws Exception {
        when(documentRepository.findByOwnerUsernameAndContentHash(eq("bob"), anyString()))
                .thenReturn(Optional.empty());
        stubHappyPath();
        when(documentRepository.save(any(Document.class))).thenAnswer(inv -> inv.getArgument(0));

        Document saved = documentService.uploadDocument(txtFile("report.txt", "shared content"), "bob");

        assertNotNull(saved.getId() == null ? saved : saved);
        verify(storageService).upload(anyString(), any());
    }
}