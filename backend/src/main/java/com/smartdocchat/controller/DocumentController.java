package com.smartdocchat.controller;

import com.smartdocchat.dto.DocumentDTO;
import com.smartdocchat.dto.UploadResponse;
import com.smartdocchat.entity.Document;
import com.smartdocchat.entity.DocumentVersion;
import com.smartdocchat.entity.Role;
import com.smartdocchat.service.AuditLogService;
import com.smartdocchat.service.DocumentAccessService;
import com.smartdocchat.service.DocumentService;
import com.smartdocchat.service.DocumentVersionService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.GrantedAuthority;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;
import java.security.Principal;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

import org.slf4j.MDC;

@RestController
@RequestMapping("/documents")
@RequiredArgsConstructor
@Slf4j
public class DocumentController {
    private final DocumentService documentService;
    private final DocumentAccessService documentAccessService;
    private final AuditLogService auditLogService;
    private final DocumentVersionService documentVersionService;

    /** Resolve the caller's Role from the JWT authentication set up by JwtAuthenticationFilter. */
    private Role currentRole() {
        Authentication auth = SecurityContextHolder.getContext().getAuthentication();
        if (auth == null) {
            return Role.ROLE_USER;
        }
        return auth.getAuthorities().stream()
                .map(GrantedAuthority::getAuthority)
                .filter(a -> a.startsWith("ROLE_"))
                .findFirst()
                .map(Role::valueOf)
                .orElse(Role.ROLE_USER);
    }

    /** Persist one immutable audit trail entry (best-effort, never breaks the request). */
    private void audit(String action, String username, String resourceType, String resourceId, String detail) {
        auditLogService.record(username, action, resourceType, resourceId, null, detail);
    }

    /** Emit one structured audit line per document read (owner-scoped). */
    private void auditDocumentAccess(String action, Long id, String owner, boolean granted) {
        try {
            MDC.put("auditAction", action);
            MDC.put("documentId", String.valueOf(id));
            MDC.put("owner", owner != null ? owner : "anonymous");
            MDC.put("granted", String.valueOf(granted));
            log.info("document access");
        } finally {
            MDC.remove("auditAction");
            MDC.remove("documentId");
            MDC.remove("owner");
            MDC.remove("granted");
        }
    }
    /**
     * Structured legal evidence units for a document (Decision 14 navigation).
     * Owner isolation is enforced in DocumentService: another user's document
     * returns 404, never its chunks.
     */
    @GetMapping("/{id}/legal-chunks")
    public ResponseEntity<?> getLegalChunks(@PathVariable Long id, Principal principal) {
        try {
            Document document = documentService.getDocumentByIdForRole(id, principal.getName(), currentRole());
            List<com.smartdocchat.entity.LegalChunk> chunks =
                    documentService.getLegalChunksForRole(id, principal.getName(), currentRole());
            auditDocumentAccess("document.read", id, principal.getName(), true);
            Map<String, Object> body = new java.util.LinkedHashMap<>();
            body.put("documentId", id);
            body.put("fileName", document.getFileName());
            body.put("title", document.getTitle());
            body.put("documentNumber", document.getDocumentNumber());
            body.put("issuingBody", document.getIssuingBody());
            body.put("issueDate", document.getIssueDate());
            body.put("effectiveDate", document.getEffectiveDate());
            body.put("sourceType", document.getSourceType() != null
                    ? document.getSourceType().name() : "USER");
            body.put("chunks", chunks.stream().map(c -> {
                Map<String, Object> m = new java.util.LinkedHashMap<>();
                m.put("id", c.getId());
                m.put("ordinal", c.getOrdinal());
                m.put("article", c.getArticleNumber());
                m.put("clause", c.getClauseNumber());
                m.put("point", c.getPointLabel());
                m.put("content", c.getContent());
                return m;
            }).collect(Collectors.toList()));
            return ResponseEntity.ok(body);
        } catch (RuntimeException e) {
            // Not found OR not owned by the caller — indistinguishable by design.
            auditDocumentAccess("document.read", id, principal.getName(), false);
            return ResponseEntity.status(HttpStatus.NOT_FOUND)
                    .body(java.util.Map.of("message", "Document not found"));
        }
    }

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

            // Document RBAC (production requirement #3): only ADMIN/ENGINEER
            // may upload. ROLE_USER viewers get 403 (AccessDeniedException is
            // mapped to FORBIDDEN by GlobalExceptionHandler).
            documentAccessService.checkUpload(currentRole());

            Document document = documentService.uploadDocument(file, principal.getName());
            audit("document.upload", principal.getName(), "document",
                    String.valueOf(document.getId()), "fileName=" + document.getFileName());
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
            audit("document.upload.failed", principal.getName(), "document", null, e.getMessage());
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
        List<Document> documents =
                documentService.getAllDocumentsForRole(principal.getName(), currentRole());
        List<DocumentDTO> dtos = documents.stream()
                .map(this::convertToDTO)
                .collect(Collectors.toList());
        return ResponseEntity.ok(dtos);
    }

    /** Legal document search (Decision 15). Owner-scoped; never exposes other users' documents. */
    @GetMapping("/search")
    public ResponseEntity<List<DocumentDTO>> searchDocuments(@RequestParam("q") String query, Principal principal) {
        return ResponseEntity.ok(documentService.searchDocuments(principal.getName(), query));
    }

    @GetMapping("/{id}")
    public ResponseEntity<DocumentDTO> getDocumentById(@PathVariable Long id, Principal principal) {
        try {
            Document document =
                    documentService.getDocumentByIdForRole(id, principal.getName(), currentRole());
            auditDocumentAccess("document.read", id, principal.getName(), true);
            audit("document.read", principal.getName(), "document", String.valueOf(id), "granted=true");
            return ResponseEntity.ok(convertToDTO(document));
        } catch (RuntimeException e) {
            auditDocumentAccess("document.read", id, principal.getName(), false);
            audit("document.read.denied", principal.getName(), "document", String.valueOf(id), "granted=false");
            return ResponseEntity.notFound().build();
        }
    }

    @DeleteMapping("/{id}")
    public ResponseEntity<String> deleteDocument(@PathVariable Long id, Principal principal) {
        try {
            Document document =
                    documentService.getDocumentByIdForRole(id, principal.getName(), currentRole());
            // Document RBAC (production requirement #3): ADMIN may delete any
            // document; others only their own. Viewers cannot delete at all.
            documentAccessService.checkDelete(currentRole(), document.getOwnerUsername(), principal.getName());
            documentService.deleteDocument(id, principal.getName());
            audit("document.delete", principal.getName(), "document", String.valueOf(id), "granted=true");
            return ResponseEntity.ok("Document deleted successfully");
        } catch (RuntimeException e) {
            audit("document.delete.denied", principal.getName(), "document", String.valueOf(id), "granted=false");
            return ResponseEntity.notFound().build();
        }
    }

    /**
     * Replace a document's content with a new file version (document
     * versioning, V10). The previous state is archived immutably and the live
     * row advances to the next version number.
     */
    @PutMapping("/{id}")
    public ResponseEntity<?> replaceDocument(@PathVariable Long id,
                                             @RequestParam("file") MultipartFile file,
                                             Principal principal) {
        try {
            Document document =
                    documentService.getDocumentByIdForRole(id, principal.getName(), currentRole());
            documentAccessService.checkReplace(currentRole(), document.getOwnerUsername(), principal.getName());
            Document replaced = documentService.replaceDocument(document, file, principal.getName());
            audit("document.replace", principal.getName(), "document", String.valueOf(id),
                    "version=" + replaced.getVersionNumber());
            return ResponseEntity.ok(convertToDTO(replaced));
        } catch (IllegalArgumentException e) {
            return ResponseEntity.badRequest().body(java.util.Map.of("message", e.getMessage()));
        } catch (IOException e) {
            log.error("Error replacing document", e);
            audit("document.replace.failed", principal.getName(), "document", String.valueOf(id), e.getMessage());
            return ResponseEntity.internalServerError()
                    .body(java.util.Map.of("message", "Unable to replace the document"));
        } catch (RuntimeException e) {
            audit("document.replace.denied", principal.getName(), "document", String.valueOf(id), "granted=false");
            return ResponseEntity.notFound().build();
        }
    }

    /** Amendment history of a legal document, newest first. */
    @GetMapping("/{id}/versions")
    public ResponseEntity<?> getDocumentVersions(@PathVariable Long id, Principal principal) {
        try {
            documentService.getDocumentByIdForRole(id, principal.getName(), currentRole());
            List<DocumentVersion> versions = documentVersionService.getVersions(id);
            return ResponseEntity.ok(versions);
        } catch (Exception e) {
            return ResponseEntity.status(HttpStatus.FORBIDDEN).body(Map.of("error", e.getMessage()));
        }
    }

    /** Get a specific version of a document. */
    @GetMapping("/{id}/versions/{versionNumber}")
    public ResponseEntity<?> getDocumentVersion(
            @PathVariable Long id,
            @PathVariable Integer versionNumber,
            Principal principal) {
        try {
            documentService.getDocumentByIdForRole(id, principal.getName(), currentRole());
            DocumentVersion version = documentVersionService.getVersion(id, versionNumber);
            return ResponseEntity.ok(version);
        } catch (Exception e) {
            return ResponseEntity.status(HttpStatus.NOT_FOUND).body(Map.of("error", e.getMessage()));
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
                .title(document.getTitle())
                .documentNumber(document.getDocumentNumber())
                .issuingBody(document.getIssuingBody())
                .issueDate(document.getIssueDate())
                .effectiveDate(document.getEffectiveDate())
                .sourceType(document.getSourceType() != null
                        ? document.getSourceType().name() : null)
                .versionNumber(document.getVersionNumber())
                .versionCount(documentVersionService.getVersionCount(document.getId()))
                .workflowResult(document.getWorkflowResult())
                .build();
    }
}
