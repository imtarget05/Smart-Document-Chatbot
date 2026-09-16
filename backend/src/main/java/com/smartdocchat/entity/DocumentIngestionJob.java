package com.smartdocchat.entity;

import jakarta.persistence.*;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

/**
 * Durable ingestion job (ADR-004): one row per asynchronous document-processing
 * unit of work (currently the llm-router document workflow). The poller claims
 * PENDING rows, runs the work outside the claim transaction and transitions the
 * row through PENDING → RUNNING → COMPLETED, retrying with exponential backoff
 * before the row ends up DEAD (the durable dead-letter state, replayable).
 */
@Entity
@Table(name = "document_ingestion_jobs")
@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class DocumentIngestionJob {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "document_id", nullable = false)
    private Long documentId;

    @Column(nullable = false)
    @Builder.Default
    private String jobType = "WORKFLOW";

    /** PENDING → RUNNING → COMPLETED | DEAD. Failed attempts return to PENDING with a delayed next_run_at. */
    @Enumerated(EnumType.STRING)
    @Column(nullable = false)
    @Builder.Default
    private JobStatus status = JobStatus.PENDING;

    @Column(nullable = false)
    @Builder.Default
    private int attempts = 0;

    @Column(name = "max_attempts", nullable = false)
    @Builder.Default
    private int maxAttempts = 3;

    /** Earliest time the poller may claim this job (backoff base for retries). */
    @Column(name = "next_run_at", nullable = false)
    private LocalDateTime nextRunAt;

    @Column(name = "last_error")
    private String lastError;

    /** Small opaque context (e.g. original filename) — the durable source of truth is the Document row. */
    @Column
    private String payload;

    @Column(name = "created_at", nullable = false, updatable = false)
    private LocalDateTime createdAt;

    @Column(name = "updated_at")
    private LocalDateTime updatedAt;

    public enum JobStatus {
        PENDING, RUNNING, COMPLETED, DEAD
    }

    @PrePersist
    void onCreate() {
        LocalDateTime now = LocalDateTime.now();
        if (createdAt == null) createdAt = now;
        if (nextRunAt == null) nextRunAt = now;
        updatedAt = now;
    }

    @PreUpdate
    void onUpdate() {
        updatedAt = LocalDateTime.now();
    }
}
