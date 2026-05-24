package com.smartdocchat.controller;

import com.smartdocchat.dto.DocumentDTO;
import com.smartdocchat.dto.UploadResponse;
import com.smartdocchat.entity.Document;
import com.smartdocchat.service.DocumentService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;
import java.util.List;
import java.util.stream.Collectors;

@RestController
@RequestMapping("/documents")
@RequiredArgsConstructor
@Slf4j
public class DocumentController {
    private final DocumentService documentService;

    @PostMapping("/upload")
    public ResponseEntity<UploadResponse> uploadDocument(@RequestParam("file") MultipartFile file) {
        try {
            if (file.isEmpty()) {
                return ResponseEntity.badRequest().body(
                        UploadResponse.builder()
                                .success(false)
                                .message("File is empty")
                                .build()
                );
            }

            Document document = documentService.uploadDocument(file);
            return ResponseEntity.ok(
                    UploadResponse.builder()
                            .success(true)
                            .message("Document uploaded successfully")
                            .documentId(document.getId())
                            .fileName(document.getFileName())
                            .build()
            );
        } catch (IOException e) {
            log.error("Error uploading document", e);
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).body(
                    UploadResponse.builder()
                            .success(false)
                            .message("Error uploading document: " + e.getMessage())
                            .build()
            );
        }
    }

    @GetMapping
    public ResponseEntity<List<DocumentDTO>> getAllDocuments() {
        List<Document> documents = documentService.getAllDocuments();
        List<DocumentDTO> dtos = documents.stream()
                .map(this::convertToDTO)
                .collect(Collectors.toList());
        return ResponseEntity.ok(dtos);
    }

    @GetMapping("/{id}")
    public ResponseEntity<DocumentDTO> getDocumentById(@PathVariable Long id) {
        try {
            Document document = documentService.getDocumentById(id);
            return ResponseEntity.ok(convertToDTO(document));
        } catch (RuntimeException e) {
            return ResponseEntity.notFound().build();
        }
    }

    @DeleteMapping("/{id}")
    public ResponseEntity<String> deleteDocument(@PathVariable Long id) {
        try {
            documentService.deleteDocument(id);
            return ResponseEntity.ok("Document deleted successfully");
        } catch (RuntimeException e) {
            return ResponseEntity.notFound().build();
        }
    }

    @PostMapping("/{id}/etl-complete")
    public ResponseEntity<String> completeEtl(
            @PathVariable Long id,
            @RequestBody java.util.Map<String, Object> payload) {
        try {
            String vectorCollectionId = (String) payload.get("vector_collection_id");
            int chunkCount = (Integer) payload.get("chunk_count");
            String summary = (String) payload.get("summary");

            String suggestedQuestions = null;
            if (payload.get("suggested_questions") != null) {
                suggestedQuestions = new com.fasterxml.jackson.databind.ObjectMapper()
                        .writeValueAsString(payload.get("suggested_questions"));
            }

            documentService.completeEtl(id, vectorCollectionId, chunkCount, summary, suggestedQuestions);
            return ResponseEntity.ok("ETL state updated to READY");
        } catch (Exception e) {
            log.error("Error completing ETL for document {}", id, e);
            return ResponseEntity.status(500).body(e.getMessage());
        }
    }

    @PostMapping("/{id}/etl-fail")
    public ResponseEntity<String> failEtl(@PathVariable Long id) {
        try {
            documentService.failEtl(id);
            return ResponseEntity.ok("ETL state updated to FAILED");
        } catch (Exception e) {
            return ResponseEntity.status(500).body(e.getMessage());
        }
    }

    @GetMapping("/{id}/mindmap")
    public ResponseEntity<String> getDocumentMindMap(@PathVariable Long id) {
        try {
            String mindMap = documentService.getOrGenerateMindMap(id);
            if (mindMap == null) {
                return ResponseEntity.status(500).body("Error generating mind map");
            }
            return ResponseEntity.ok()
                    .contentType(org.springframework.http.MediaType.APPLICATION_JSON)
                    .body(mindMap);
        } catch (Exception e) {
            log.error("Error fetching mind map for document {}", id, e);
            return ResponseEntity.status(500).build();
        }
    }

    private DocumentDTO convertToDTO(Document document) {
        return DocumentDTO.builder()
                .id(document.getId())
                .fileName(document.getFileName())
                .fileType(document.getFileType())
                .fileSize(document.getFileSize())
                .createdAt(document.getCreatedAt())
                .updatedAt(document.getUpdatedAt())
                .chunkCount(document.getChunkCount())
                .summary(document.getSummary())
                .suggestedQuestions(document.getSuggestedQuestions())
                .conceptMap(document.getConceptMap())
                .status(document.getStatus())
                .build();
    }
}
