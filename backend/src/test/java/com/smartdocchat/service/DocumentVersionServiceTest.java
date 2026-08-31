package com.smartdocchat.service;

import com.smartdocchat.entity.Document;
import com.smartdocchat.entity.DocumentVersion;
import com.smartdocchat.repository.DocumentVersionRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.util.List;
import java.util.Optional;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class DocumentVersionServiceTest {

    @Mock private DocumentVersionRepository repository;

    private DocumentVersionService service;

    @BeforeEach
    void setUp() {
        service = new DocumentVersionService(repository);
    }

    private Document document() {
        return Document.builder()
                .id(7L)
                .fileName("old.txt")
                .filePath("uploads/old.txt")
                .fileType("txt")
                .contentHash("abc123")
                .fileSize(500L)
                .chunkCount(3)
                .build();
    }

    @Test
    void firstVersionStartsAtOne() {
        when(repository.findTopByDocumentIdOrderByVersionNumberDesc(7L)).thenReturn(Optional.empty());
        when(repository.save(any(DocumentVersion.class))).thenAnswer(inv -> inv.getArgument(0));

        DocumentVersion saved = service.createVersion(document(), "alice", "initial upload");

        assertEquals(1, saved.getVersionNumber());
        assertEquals("alice", saved.getChangedBy());
        assertEquals("initial upload", saved.getChangeSummary());
    }

    @Test
    void nextVersionIncrementsFromLatestStored() {
        when(repository.findTopByDocumentIdOrderByVersionNumberDesc(7L))
                .thenReturn(Optional.of(DocumentVersion.builder().versionNumber(3).build()));
        when(repository.save(any(DocumentVersion.class))).thenAnswer(inv -> inv.getArgument(0));

        DocumentVersion saved = service.createVersion(document(), "bob", "superseded by amended.txt");

        assertEquals(4, saved.getVersionNumber());

        ArgumentCaptor<DocumentVersion> captor = ArgumentCaptor.forClass(DocumentVersion.class);
        verify(repository).save(captor.capture());
        // Snapshot preserves the state of the superseded document.
        assertEquals("old.txt", captor.getValue().getFileName());
        assertEquals("abc123", captor.getValue().getContentHash());
        assertEquals(3, captor.getValue().getChunkCount());
        assertEquals("bob", captor.getValue().getChangedBy());
    }

    @Test
    void getVersionsReturnsNewestFirst() {
        List<DocumentVersion> versions = List.of(
                DocumentVersion.builder().versionNumber(3).build(),
                DocumentVersion.builder().versionNumber(2).build());
        when(repository.findByDocumentIdOrderByVersionNumberDesc(7L)).thenReturn(versions);

        List<DocumentVersion> result = service.getVersions(7L);

        assertEquals(2, result.size());
        assertEquals(3, result.get(0).getVersionNumber().intValue());
        assertEquals(2, result.get(1).getVersionNumber().intValue());
    }

    @Test
    void getVersionCountIsExposedForAdminViews() {
        when(repository.countByDocumentId(7L)).thenReturn(3L);
        assertEquals(3L, service.getVersionCount(7L));
    }
}
