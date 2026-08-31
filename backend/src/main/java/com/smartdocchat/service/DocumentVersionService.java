package com.smartdocchat.service;

import com.smartdocchat.entity.Document;
import com.smartdocchat.entity.DocumentVersion;
import com.smartdocchat.repository.DocumentVersionRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;

@Service
@RequiredArgsConstructor
@Slf4j
public class DocumentVersionService {

    private final DocumentVersionRepository versionRepository;

    /**
     * Create a new version record for a document.
     */
    @Transactional
    public DocumentVersion createVersion(Document document, String changedBy, String changeSummary) {
        DocumentVersion latestVersion = versionRepository
                .findTopByDocumentIdOrderByVersionNumberDesc(document.getId())
                .orElse(null);

        int nextVersion = (latestVersion != null) ? latestVersion.getVersionNumber() + 1 : 1;

        DocumentVersion version = DocumentVersion.builder()
                .documentId(document.getId())
                .versionNumber(nextVersion)
                .fileName(document.getFileName())
                .filePath(document.getFilePath())
                .fileType(document.getFileType())
                .fileSize(document.getFileSize())
                .contentHash(document.getContentHash())
                .chunkCount(document.getChunkCount())
                .changeSummary(changeSummary)
                .changedBy(changedBy)
                .build();

        DocumentVersion saved = versionRepository.save(version);
        log.info("Created version {} for document {} (id={})",
                nextVersion, document.getFileName(), document.getId());
        return saved;
    }

    /**
     * Get all versions of a document, newest first.
     */
    @Transactional(readOnly = true)
    public List<DocumentVersion> getVersions(Long documentId) {
        return versionRepository.findByDocumentIdOrderByVersionNumberDesc(documentId);
    }

    /**
     * Get a specific version.
     */
    @Transactional(readOnly = true)
    public DocumentVersion getVersion(Long documentId, Integer versionNumber) {
        return versionRepository.findByDocumentIdAndVersionNumber(documentId, versionNumber)
                .orElseThrow(() -> new RuntimeException(
                        "Version " + versionNumber + " not found for document " + documentId));
    }

    /**
     * Get the latest version of a document.
     */
    @Transactional(readOnly = true)
    public DocumentVersion getLatestVersion(Long documentId) {
        return versionRepository.findTopByDocumentIdOrderByVersionNumberDesc(documentId)
                .orElseThrow(() -> new RuntimeException(
                        "No versions found for document " + documentId));
    }

    /**
     * Get version count for a document.
     */
    @Transactional(readOnly = true)
    public Long getVersionCount(Long documentId) {
        return versionRepository.countByDocumentId(documentId);
    }
}
