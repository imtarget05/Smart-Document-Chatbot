package com.smartdocchat.service;

import com.smartdocchat.entity.VideoJob;
import com.smartdocchat.entity.VideoJob.JobStatus;
import com.smartdocchat.repository.VideoJobRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.data.domain.Sort;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.List;

/**
 * Durable video-job queue (MAIA video pipeline V1 — SDC side, ADR-004 pattern).
 *
 * <p>Java owns the durable state and the HTTP surface; the Python
 * {@code video-worker} owns execution (FFmpeg). This service therefore only:
 *
 * <ul>
 *   <li>{@link #enqueue} — idempotent: one active job per
 *       (owner, source hash, job type), enforced by the V19 partial unique index;</li>
 *   <li>{@link #listForOwner} / {@link #getForOwner} — scoped reads;</li>
 *   <li>{@link #listByStatus} / {@link #replayDeadJob} — admin/DLQ surface;</li>
 *   <li>{@link #recoverExpiredLeases} — crash recovery for worker-issued leases.</li>
 * </ul>
 */
@Service
@RequiredArgsConstructor
@Slf4j
public class VideoJobService {

    public static final String JOB_TYPE_TRANSCODE = "TRANSCODE";

    private static final int MAX_PAYLOAD_CHARS = 500;
    private static final int MAX_KEY_CHARS = 500;

    private final VideoJobRepository jobRepository;

    @Value("${video-jobs.batch-size:10}")
    private int batchSize;

    /**
     * Idempotent enqueue. Returns {@code null} when an active job already exists
     * for this (owner, source hash, job type) — the unique index is the final
     * guard, this check makes the common case cheap and explicit.
     */
    @Transactional
    public VideoJob enqueue(String ownerUsername, String sourceHash, String jobType,
                            String preset, String sourceKey, String payload) {
        String type = (jobType == null || jobType.isBlank()) ? JOB_TYPE_TRANSCODE : jobType.trim();
        boolean active = jobRepository.existsByOwnerUsernameAndSourceHashAndJobTypeAndStatusIn(
                ownerUsername, sourceHash, type, List.of(JobStatus.PENDING, JobStatus.RUNNING));
        if (active) {
            log.info("Video job already active for owner={} source={} type={} — enqueue skipped (idempotent)",
                    ownerUsername, sourceHash, type);
            return null;
        }
        VideoJob job = VideoJob.builder()
                .ownerUsername(ownerUsername)
                .sourceHash(sourceHash)
                .jobType(type)
                .preset(truncate(preset, 64))
                .sourceKey(truncate(sourceKey, MAX_KEY_CHARS))
                .payload(truncate(payload, MAX_PAYLOAD_CHARS))
                .status(JobStatus.PENDING)
                .nextRunAt(LocalDateTime.now())
                .build();
        VideoJob saved = jobRepository.save(job);
        log.info("Enqueued video job id={} owner={} type={}", saved.getId(), ownerUsername, type);
        return saved;
    }

    public VideoJob getForOwner(Long id, String ownerUsername) {
        return jobRepository.findByIdAndOwnerUsername(id, ownerUsername)
                .orElseThrow(() -> new IllegalArgumentException("Video job " + id + " not found"));
    }

    public Page<VideoJob> listForOwner(String ownerUsername, int page, int size) {
        return jobRepository.findByOwnerUsername(ownerUsername, pageable(page, size));
    }

    public Page<VideoJob> listByStatus(JobStatus status, int page, int size) {
        return jobRepository.findByStatus(status, pageable(page, size));
    }

    /**
     * Admin replay: DEAD → PENDING with attempts reset; the worker picks it up
     * on its next claim (durable DLQ replay).
     */
    @Transactional
    public VideoJob replayDeadJob(Long jobId) {
        VideoJob job = jobRepository.findById(jobId)
                .orElseThrow(() -> new IllegalArgumentException("Video job " + jobId + " not found"));
        if (job.getStatus() != JobStatus.DEAD) {
            throw new IllegalStateException(
                    "Only DEAD video jobs can be replayed (job " + jobId + " is " + job.getStatus() + ")");
        }
        job.setStatus(JobStatus.PENDING);
        job.setAttempts(0);
        job.setLeaseExpiresAt(null);
        job.setNextRunAt(LocalDateTime.now());
        log.info("Video job {} replayed by admin → PENDING", jobId);
        return job;
    }

    /**
     * Crash recovery tick: hand RUNNING rows with an expired worker lease back to
     * the queue. The worker renews its lease while an encode is alive, so this
     * never requeues an in-flight job.
     */
    @Scheduled(fixedDelayString = "${video-jobs.recovery-interval-ms:60000}",
            initialDelayString = "${video-jobs.initial-delay-ms:15000}")
    public void recoverExpiredLeases() {
        int recovered = jobRepository.requeueExpiredLeases();
        if (recovered > 0) {
            log.warn("Requeued {} video jobs with expired leases (worker crash recovery)", recovered);
        }
    }

    /** Exposed for tests/ops: how many rows a single worker tick may claim. */
    public int batchSize() {
        return batchSize;
    }

    private static Pageable pageable(int page, int size) {
        int safeSize = Math.min(Math.max(size, 1), 200);
        return PageRequest.of(Math.max(page, 0), safeSize,
                Sort.by(Sort.Direction.DESC, "updatedAt"));
    }

    private static String truncate(String value, int max) {
        if (value == null) {
            return null;
        }
        return value.length() > max ? value.substring(0, max) : value;
    }
}