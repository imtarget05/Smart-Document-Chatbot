package com.smartdocchat.controller;

import com.smartdocchat.entity.DocumentIngestionJob;
import com.smartdocchat.entity.DocumentIngestionJob.JobStatus;
import com.smartdocchat.service.DocumentJobService;
import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.Page;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.*;

import java.util.LinkedHashMap;
import java.util.Map;

/**
 * Admin API for the durable ingestion queue (ADR-004): inspect job states and
 * replay DEAD jobs (durable dead-letter queue). Requires ROLE_ADMIN — enforced
 * via method security, mirroring AuditLogController.
 */
@RestController
@RequestMapping("/admin/ingestion-jobs")
@RequiredArgsConstructor
public class IngestionJobAdminController {

    private final DocumentJobService documentJobService;

    @GetMapping
    @PreAuthorize("hasRole('ADMIN')")
    public ResponseEntity<Map<String, Object>> listJobs(
            @RequestParam(defaultValue = "PENDING") String status,
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "50") int size) {

        JobStatus parsed;
        try {
            parsed = JobStatus.valueOf(status.toUpperCase());
        } catch (IllegalArgumentException e) {
            return ResponseEntity.badRequest().body(Map.of(
                    "error", "Unknown status '" + status + "'. Valid: PENDING, RUNNING, COMPLETED, DEAD"));
        }

        Page<DocumentIngestionJob> result = documentJobService.listByStatus(parsed, page, size);
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("status", parsed.name());
        body.put("page", result.getNumber());
        body.put("size", result.getSize());
        body.put("totalElements", result.getTotalElements());
        body.put("totalPages", result.getTotalPages());
        body.put("jobs", result.getContent().stream().map(j -> {
            Map<String, Object> m = new LinkedHashMap<>();
            m.put("id", j.getId());
            m.put("documentId", j.getDocumentId());
            m.put("jobType", j.getJobType());
            m.put("status", j.getStatus().name());
            m.put("attempts", j.getAttempts());
            m.put("maxAttempts", j.getMaxAttempts());
            m.put("nextRunAt", j.getNextRunAt());
            m.put("lastError", j.getLastError());
            m.put("payload", j.getPayload());
            m.put("createdAt", j.getCreatedAt());
            m.put("updatedAt", j.getUpdatedAt());
            return m;
        }).toList());
        return ResponseEntity.ok(body);
    }

    /** Durable DLQ replay: reset a DEAD job to PENDING for the next poller tick. */
    @PostMapping("/{id}/replay")
    @PreAuthorize("hasRole('ADMIN')")
    public ResponseEntity<Map<String, Object>> replayJob(@PathVariable Long id) {
        try {
            DocumentIngestionJob job = documentJobService.replayDeadJob(id);
            return ResponseEntity.ok(Map.of(
                    "status", "requeued",
                    "jobId", job.getId(),
                    "documentId", job.getDocumentId()));
        } catch (IllegalArgumentException | IllegalStateException e) {
            return ResponseEntity.badRequest().body(Map.of("error", e.getMessage()));
        }
    }
}
