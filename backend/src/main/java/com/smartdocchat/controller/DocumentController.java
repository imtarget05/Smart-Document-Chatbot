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
import java.security.Principal;
import java.util.List;
import java.util.stream.Collectors;

@RestController
@RequestMapping("/documents")
@RequiredArgsConstructor
@Slf4j
public class DocumentController {
    private final DocumentService documentService;

    @PostMapping("/upload")
    public ResponseEntity<UploadResponse> uploadDocument(
            @RequestParam("file") MultipartFile file, Principal principal) {
        try {
            if (file.isEmpty()) {
                return ResponseEntity.badRequest().body(
                        UploadResponse.builder()
                                .success(false)
                                .message("File is empty")
                                .build()
                );
            }

            Document document = documentService.uploadDocument(file, principal.getName());
            return ResponseEntity.ok(
                    UploadResponse.builder()
                            .success(true)
                            .message("Document uploaded successfully")
                            .documentId(document.getId())
                            .fileName(document.getFileName())
                            .build()
            );
        } catch (IllegalArgumentException e) {
            return ResponseEntity.badRequest().body(
                    UploadResponse.builder().success(false).message(e.getMessage()).build()
            );
        } catch (IOException e) {
            log.error("Error uploading document", e);
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).body(
                    UploadResponse.builder()
                            .success(false)
                            .message("Unable to process the uploaded document")
                            .build()
            );
        }
    }

    @GetMapping
    public ResponseEntity<List<DocumentDTO>> getAllDocuments(Principal principal) {
        List<Document> documents = documentService.getAllDocuments(principal.getName());
        List<DocumentDTO> dtos = documents.stream()
                .map(this::convertToDTO)
                .collect(Collectors.toList());
        return ResponseEntity.ok(dtos);
    }

    @GetMapping("/{id}")
    public ResponseEntity<DocumentDTO> getDocumentById(@PathVariable Long id, Principal principal) {
        try {
            Document document = documentService.getDocumentById(id, principal.getName());
            return ResponseEntity.ok(convertToDTO(document));
        } catch (RuntimeException e) {
            return ResponseEntity.notFound().build();
        }
    }

    @DeleteMapping("/{id}")
    public ResponseEntity<String> deleteDocument(@PathVariable Long id, Principal principal) {
        try {
            documentService.deleteDocument(id, principal.getName());
            return ResponseEntity.ok("Document deleted successfully");
        } catch (RuntimeException e) {
            return ResponseEntity.notFound().build();
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
                .build();
    }
}