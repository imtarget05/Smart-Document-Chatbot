package com.smartdocchat.repository;

import com.smartdocchat.entity.VideoJob;
import com.smartdocchat.entity.VideoJob.JobStatus;
import jakarta.persistence.LockModeType;
import jakarta.persistence.QueryHint;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Lock;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.jpa.repository.QueryHints;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;
import org.springframework.transaction.annotation.Transactional;

import java.util.Collection;
import java.util.List;
import java.util.Optional;

/**
 * Durable video queue (V19, ADR-004 pattern).
 *
 * <p>Claimability uses {@code PESSIMISTIC_WRITE} + Hibernate lock timeout -2
 * (mapped to {@code SKIP LOCKED}) so horizontally scaled workers can never
 * claim the same row. The Python video-worker uses the identical
 * {@code SELECT ... FOR UPDATE SKIP LOCKED} query directly on Neon.
 */
@Repository
public interface VideoJobRepository extends JpaRepository<VideoJob, Long> {

    /** Claimable jobs (PENDING and due), row-locked with SKIP LOCKED. */
    @Lock(LockModeType.PESSIMISTIC_WRITE)
    @QueryHints(@QueryHint(name = "jakarta.persistence.lock.timeout", value = "-2"))
    @Query("SELECT j FROM VideoJob j " +
            "WHERE j.status = 'PENDING' AND j.nextRunAt <= CURRENT_TIMESTAMP ORDER BY j.id")
    List<VideoJob> findClaimable(Pageable pageable);

    /** True when the owner already has an active (PENDING/RUNNING) job for this source+type. */
    boolean existsByOwnerUsernameAndSourceHashAndJobTypeAndStatusIn(
            String ownerUsername, String sourceHash, String jobType, Collection<JobStatus> statuses);

    Page<VideoJob> findByStatus(JobStatus status, Pageable pageable);

    Page<VideoJob> findByOwnerUsername(String ownerUsername, Pageable pageable);

    Optional<VideoJob> findByIdAndOwnerUsername(Long id, String ownerUsername);

    /**
     * Crash recovery: RUNNING rows whose worker-issued lease expired are handed
     * back to the queue, so no job is stuck in RUNNING forever but a live long
     * encode is never requeued (the worker keeps renewing its lease).
     */
    @Transactional
    @Modifying(clearAutomatically = true)
    @Query(value = "UPDATE video_jobs SET status = 'PENDING', lease_expires_at = NULL, updated_at = now() " +
            "WHERE status = 'RUNNING' AND lease_expires_at IS NOT NULL AND lease_expires_at < now()",
            nativeQuery = true)
    int requeueExpiredLeases();
}