package com.smartdocchat.service;

import com.smartdocchat.dto.DocumentDTO;
import com.smartdocchat.entity.Document;
import com.smartdocchat.entity.LegalChunk;
import com.smartdocchat.entity.SourceType;
import com.smartdocchat.repository.DocumentRepository;
import com.smartdocchat.repository.LegalChunkRepository;
import com.smartdocchat.util.DocumentParser;
import com.smartdocchat.util.LegalDateExtractor;
import com.smartdocchat.util.LegalStructureParser;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;

import java.io.File;
import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.CharsetDecoder;
import java.nio.charset.StandardCharsets;
import java.util.*;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

@Service
@RequiredArgsConstructor
@Slf4j
public class DocumentService {
    private final DocumentRepository documentRepository;
    private final DocumentParser documentParser;
    private final StorageService storageService;
    private final LegalStructureParser legalStructureParser;
    private final LegalChunkRepository legalChunkRepository;
    private final com.smartdocchat.util.LegalQueryNormalizer legalQueryNormalizer;
    private final com.smartdocchat.util.LegalDateExtractor legalDateExtractor;
    private final DocumentWorkflowClient documentWorkflowClient;

    /** Matches an explicit "Số: NN/YYYY/AAA" document-number line only. */
    private static final Pattern DOCUMENT_NUMBER =
            Pattern.compile("(?im)^\\s*Số\\s*:\\s*(\\S+/\\d{4}/\\S+)");

    private static final Set<String> ALLOWED_EXTENSIONS = Set.of("pdf", "docx", "txt");

    public Document uploadDocument(MultipartFile file, String ownerUsername) throws IOException {
        String originalFileName = sanitizeFileName(file.getOriginalFilename());
        String fileExtension = getFileExtension(originalFileName);
        validateUpload(file, fileExtension);

        // Idempotent ingestion (Blueprint #17): identical content uploaded
        // twice by the same owner must not create duplicate metadata.
        String contentHash = sha256Hex(file.getBytes());
        Optional<Document> existing =
                documentRepository.findByOwnerUsernameAndContentHash(ownerUsername, contentHash);
        if (existing.isPresent()) {
            log.info("Duplicate upload '{}' ignored for {} — existing document id {} returned",
                    originalFileName, ownerUsername, existing.get().getId());
            return existing.get();
        }

        String fileName = UUID.randomUUID() + "." + fileExtension;

        // Store file on disk
        String storagePath = storageService.upload(fileName, file);

        // Parse and chunk locally
        File savedFile = storageService.download(storagePath);
        String extractedText = documentParser.extractText(savedFile, fileExtension);
        List<String> chunks = documentParser.chunkText(extractedText, 500);

        log.info("Document '{}' extracted with {} chunks", originalFileName, chunks.size());

        // Serialize chunks as JSON
        String chunksJson = new com.fasterxml.jackson.databind.ObjectMapper()
                .writeValueAsString(chunks);

        // Save document metadata + chunks to database.
        // Provenance defaults to USER — never silently OFFICIAL.
        Document document = Document.builder()
                .fileName(originalFileName)
                .filePath(storagePath)
                .ownerUsername(ownerUsername)
                .fileType(fileExtension)
                .fileSize(file.getSize())
                .chunkCount(chunks.size())
                .chunks(chunksJson)
                .sourceType(SourceType.USER)
                .contentHash(contentHash)
                .build();

        // Legal structure detection: when article markers exist, persist
        // addressable evidence units alongside the generic chunks (which are
        // kept for backward compatibility with the legacy retrieval path).
        List<LegalStructureParser.StructuredUnit> legalUnits =
                legalStructureParser.parse(extractedText);
        if (!legalUnits.isEmpty()) {
            Matcher numberMatch = DOCUMENT_NUMBER.matcher(extractedText);
            if (numberMatch.find()) {
                document.setDocumentNumber(numberMatch.group(1));
            }
            // Legal dates (Decision 16A): only explicit labelled lines; never
            // inferred from arbitrary body text; missing stays null.
            LegalDateExtractor.LegalDateMetadata dates = legalDateExtractor.extract(extractedText);
            document.setIssueDate(dates.issueDate());
            document.setEffectiveDate(dates.effectiveDate());
        }
        Document saved = documentRepository.save(document);

        // Phase 2 wiring (#7): fire document workflow (classify → extract → map → match)
        // to llm-router asynchronously. Không block upload response; nếu lỗi, upload
        // vẫn thành công và workflowResult giữ null (graceful degradation).
        try {
            String workflowResult = documentWorkflowClient.runWorkflow(extractedText, originalFileName);
            if (workflowResult != null) {
                saved.setWorkflowResult(workflowResult);
                saved = documentRepository.save(saved);
                log.info("Document {} workflow completed", saved.getId());
            }
        } catch (Exception e) {
            log.warn("Document workflow post-processing skipped for {}: {}", saved.getId(), e.getMessage());
        }

        if (!legalUnits.isEmpty()) {
            int ordinal = 0;
            for (LegalStructureParser.StructuredUnit unit : legalUnits) {
                legalChunkRepository.save(LegalChunk.builder()
                        .documentId(saved.getId())
                        .ordinal(ordinal++)
                        .content(unit.text())
                        .chapterNumber(unit.chapter())
                        .articleNumber(unit.article())
                        .clauseNumber(unit.clause())
                        .pointLabel(unit.point())
                        .build());
            }
            log.info("Document '{}' ingested as structured legal text: {} evidence units",
                    originalFileName, legalUnits.size());
        }

        return saved;
    }

    public List<Document> getAllDocuments(String ownerUsername) {
        return documentRepository.findByOwnerUsernameOrderByCreatedAtDesc(ownerUsername);
    }

    private List<Document> getDocumentsByOwner(String ownerUsername) {
        return documentRepository.findByOwnerUsernameOrderByCreatedAtDesc(ownerUsername);
    }

    public Document getDocumentById(Long id, String ownerUsername) {
        return documentRepository.findByIdAndOwnerUsername(id, ownerUsername).orElseThrow(
                () -> new RuntimeException("Document not found with id: " + id)
        );
    }

    public void deleteDocument(Long id, String ownerUsername) {
        Document document = getDocumentById(id, ownerUsername);
        storageService.delete(document.getFilePath());
        legalChunkRepository.deleteByDocumentId(id);
        documentRepository.delete(document);
    }

    @SuppressWarnings("unchecked")
    public List<String> getDocumentChunks(Long documentId, String ownerUsername) {
        Document doc = getDocumentById(documentId, ownerUsername);
        if (doc.getChunks() == null || doc.getChunks().isBlank()) {
            return Collections.emptyList();
        }
        try {
            return new com.fasterxml.jackson.databind.ObjectMapper()
                    .readValue(doc.getChunks(), List.class);
        } catch (Exception e) {
            log.error("Error parsing chunks for document {}", documentId, e);
            return Collections.emptyList();
        }
    }

    /**
     * Returns the structured legal evidence units for a document, enforcing
     * owner isolation. Empty when the document was ingested without legal
     * structure (legacy/generic chunking only).
     */
    public List<LegalChunk> getLegalChunks(Long documentId, String ownerUsername) {
        getDocumentById(documentId, ownerUsername); // owner isolation check
        return legalChunkRepository.findByDocumentIdOrderByOrdinalAsc(documentId);
    }

    /**
     * Legal document search (Decision 15): matches the query against file
     * name, legal title and document number using Vietnamese-aware
     * normalisation (case-fold + diacritic-fold + abbreviation expansion).
     * Only the requesting owner's documents are ever considered.
     */
    public List<DocumentDTO> searchDocuments(String ownerUsername, String query) {
        Set<String> terms = legalQueryNormalizer.matchTerms(query);
        String foldedQuery = legalQueryNormalizer.foldContent(query);
        String rawNumber = extractDocumentNumber(query);

        return getDocumentsByOwner(ownerUsername).stream()
                .map(doc -> {
                    String haystack = legalQueryNormalizer.foldContent(
                            nullSafe(doc.getFileName()) + " " + nullSafe(doc.getTitle()) + " "
                                    + nullSafe(doc.getDocumentNumber()));
                    boolean match = false;
                    if (!rawNumber.isEmpty() && doc.getDocumentNumber() != null
                            && legalQueryNormalizer.foldContent(doc.getDocumentNumber()).contains(rawNumber)) {
                        match = true;
                    }
                    if (!match && !terms.isEmpty()) {
                        long hits = terms.stream().filter(haystack::contains).count();
                        match = hits >= Math.min(terms.size(), 1);
                    }
                    if (!match && haystack.contains(foldedQuery) && !foldedQuery.isBlank()) {
                        match = true;
                    }
                    return match ? toDTO(doc) : null;
                })
                .filter(Objects::nonNull)
                .toList();
    }

    private static final Pattern NUMBER_TOKEN = Pattern.compile("\\d{1,4}/\\d{4}/[A-Za-z\\-]+");

    private String extractDocumentNumber(String query) {
        Matcher m = NUMBER_TOKEN.matcher(query == null ? "" : query);
        return m.find() ? legalQueryNormalizer.foldContent(m.group()) : "";
    }

    private String nullSafe(String s) {
        return s == null ? "" : s;
    }

    private DocumentDTO toDTO(Document d) {
        return DocumentDTO.builder()
                .id(d.getId())
                .fileName(d.getFileName())
                .fileType(d.getFileType())
                .fileSize(d.getFileSize())
                .createdAt(d.getCreatedAt())
                .updatedAt(d.getUpdatedAt())
                .chunkCount(d.getChunkCount())
                .title(d.getTitle())
                .documentNumber(d.getDocumentNumber())
                .issuingBody(d.getIssuingBody())
                .issueDate(d.getIssueDate())
                .effectiveDate(d.getEffectiveDate())
                .sourceType(d.getSourceType() != null ? d.getSourceType().name() : null)
                .build();
    }

    /** SHA-256 hex digest used for idempotent ingestion (Blueprint #17). */
    private String sha256Hex(byte[] content) {
        try {
            java.security.MessageDigest digest = java.security.MessageDigest.getInstance("SHA-256");
            StringBuilder sb = new StringBuilder();
            for (byte b : digest.digest(content)) {
                sb.append(String.format("%02x", b));
            }
            return sb.toString();
        } catch (java.security.NoSuchAlgorithmException e) {
            // SHA-256 is mandatory on every supported JVM — unreachable.
            throw new IllegalStateException("SHA-256 algorithm unavailable", e);
        }
    }

    private String getFileExtension(String fileName) {
        if (fileName != null && fileName.contains(".")) {
            return fileName.substring(fileName.lastIndexOf(".") + 1).toLowerCase();
        }
        return "txt";
    }

    private String sanitizeFileName(String fileName) {
        if (fileName == null || fileName.isBlank()) {
            return "document.txt";
        }
        String name = fileName.replaceAll("[\\r\\n]", "_");
        int lastSlash = Math.max(name.lastIndexOf('/'), name.lastIndexOf('\\'));
        return lastSlash >= 0 ? name.substring(lastSlash + 1) : name;
    }

    private void validateUpload(MultipartFile file, String extension) throws IOException {
        if (!ALLOWED_EXTENSIONS.contains(extension)) {
            throw new IllegalArgumentException("Unsupported document type. Allowed types: PDF, DOCX, TXT");
        }

        byte[] header = new byte[8];
        try (InputStream in = file.getInputStream()) {
            int bytesRead = in.read(header);
            if (bytesRead < 4) {
                throw new IllegalArgumentException("File is too small to be a valid document.");
            }
        }

        switch (extension) {
            case "pdf" -> {
                if (header[0] != 0x25 || header[1] != 0x50 || header[2] != 0x44 || header[3] != 0x46) {
                    throw new IllegalArgumentException("File content does not match a valid PDF.");
                }
            }
            case "docx" -> {
                if (header[0] != 0x50 || header[1] != 0x4B || header[2] != 0x03 || header[3] != 0x04) {
                    throw new IllegalArgumentException("File content does not match a valid DOCX (ZIP) archive.");
                }
            }
            case "txt" -> {
                byte[] sample = file.getBytes();
                int sampleLen = Math.min(sample.length, 4096);
                try {
                    CharsetDecoder decoder = StandardCharsets.UTF_8.newDecoder();
                    decoder.decode(java.nio.ByteBuffer.wrap(sample, 0, sampleLen));
                } catch (java.nio.charset.CharacterCodingException e) {
                    throw new IllegalArgumentException("TXT file contains invalid UTF-8 characters.");
                }
            }
            default -> throw new IllegalArgumentException("Unsupported extension: " + extension);
        }
    }
}