package com.smartdocchat.entity;

import jakarta.persistence.*;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

/**
 * Durable video job (MAIA video pipeline V1 — SDC side, ADR-004 pattern).
 *
 * <p>One row per asynchronous video unit of work (transcode / remux /
 * extract_audio / hls_vod). The Python {@code video-worker} claims PENDING rows
 * with {@code SELECT ... FOR UPDATE SKIP LOCKED}, runs FFmpeg outside the web
 * process and transitions the row PENDING → RUNNING → COMPLETED, retrying with
 * exponential backoff before the row ends up DEAD (durable dead-letter state,
 * replayable via {@code /admin/video-jobs/{id}/replay}).
 *
 * <p>{@code sourceHash} + {@code jobType} + {@code ownerUsername} are covered by
 * a partial unique index while the job is active, so duplicate enqueues are
 * rejected at the DB level (idempotency), mirroring {@code document_ingestion_jobs}.
 */
@Entity
@Table(name = "video_jobs")
@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class VideoJob {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "owner_username", nullable = false)
    private String ownerUsername;

    /** Content hash of the source object — idempotency key together with jobType. */
    @Column(name = "source_hash", nullable = false)
    private String sourceHash;

    @Column(name = "job_type", nullable = false)
    @Builder.Default
    private String jobType = "TRANSCODE";

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

    /** Earliest time the worker may claim this job (backoff base for retries). */
    @Column(name = "next_run_at", nullable = false)
    private LocalDateTime nextRunAt;

    /** Set by the worker when it claims the row; crash recovery requeues only expired leases. */
    @Column(name = "lease_expires_at")
    private LocalDateTime leaseExpiresAt;

    /** Identity of the worker currently holding the lease (V20). */
    @Column(name = "worker_id")
    private String workerId;

    /**
     * Opaque lease token minted on claim (V20). complete/fail updates are guarded
     * by this token so a stale worker cannot overwrite a newer owner's result.
     */
    @Column(name = "lease_token")
    private String leaseToken;

    @Column(name = "last_error")
    private String lastError;

    /** Storage key of the uploaded source object (R2/local). */
    @Column(name = "source_key")
    private String sourceKey;

    /** Storage key of the produced output object (set by the worker on success). */
    @Column(name = "output_key")
    private String outputKey;

    /** Requested encode preset (e.g. 720p, 480p, hls). */
    @Column
    private String preset;

    /** ffprobe metadata as JSON (duration/resolution/codec) written by the worker. */
    @Column(name = "metadata_json")
    private String metadataJson;

    /** Small opaque context (e.g. original filename) — bounded to fit the column. */
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