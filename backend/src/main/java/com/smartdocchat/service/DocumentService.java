package com.smartdocchat.service;

import com.smartdocchat.entity.Document;
import com.smartdocchat.repository.DocumentRepository;
import com.smartdocchat.util.DocumentParser;
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

@Service
@RequiredArgsConstructor
@Slf4j
public class DocumentService {
    private final DocumentRepository documentRepository;
    private final DocumentParser documentParser;
    private final StorageService storageService;

    private static final Set<String> ALLOWED_EXTENSIONS = Set.of("pdf", "docx", "txt");

    public Document uploadDocument(MultipartFile file, String ownerUsername) throws IOException {
        String originalFileName = sanitizeFileName(file.getOriginalFilename());
        String fileExtension = getFileExtension(originalFileName);
        validateUpload(file, fileExtension);
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

        // Save document metadata + chunks to database
        Document document = Document.builder()
                .fileName(originalFileName)
                .filePath(storagePath)
                .ownerUsername(ownerUsername)
                .fileType(fileExtension)
                .fileSize(file.getSize())
                .chunkCount(chunks.size())
                .chunks(chunksJson)
                .build();

        return documentRepository.save(document);
    }

    public List<Document> getAllDocuments(String ownerUsername) {
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