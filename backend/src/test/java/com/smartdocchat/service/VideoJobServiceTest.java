package com.smartdocchat.service;

import com.smartdocchat.entity.VideoJob;
import com.smartdocchat.entity.VideoJob.JobStatus;
import com.smartdocchat.repository.VideoJobRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.util.List;
import java.util.Optional;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyList;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

/**
 * V19 / ADR-004 — durable video queue: idempotent enqueue, tenant-scoped reads,
 * expired-lease recovery and admin replay of the durable dead-letter state.
 */
@ExtendWith(MockitoExtension.class)
class VideoJobServiceTest {

    @Mock private VideoJobRepository jobRepository;

    private VideoJobService service;

    @BeforeEach
    void setUp() {
        service = new VideoJobService(jobRepository);
        org.springframework.test.util.ReflectionTestUtils.setField(service, "batchSize", 10);
    }

    @Test
    void enqueueCreatesPendingJobForNewSource() {
        when(jobRepository.existsByOwnerUsernameAndSourceHashAndJobTypeAndStatusIn(
                eq("alice"), eq("sha-1"), eq("TRANSCODE"), anyList())).thenReturn(false);
        when(jobRepository.save(any(VideoJob.class))).thenAnswer(inv -> inv.getArgument(0));

        VideoJob job = service.enqueue("alice", "sha-1", "TRANSCODE", "720p", "video/in/a.mp4", "a.mp4");

        assertNotNull(job);
        assertEquals(JobStatus.PENDING, job.getStatus());
        assertEquals("alice", job.getOwnerUsername());
        assertEquals("sha-1", job.getSourceHash());
        assertEquals("TRANSCODE", job.getJobType());
        assertEquals("720p", job.getPreset());
        assertEquals("video/in/a.mp4", job.getSourceKey());
        assertEquals("a.mp4", job.getPayload());
        assertNotNull(job.getNextRunAt());
        assertNull(job.getLeaseExpiresAt());
    }

    @Test
    void enqueueIsIdempotentWhenActiveJobAlreadyExists() {
        when(jobRepository.existsByOwnerUsernameAndSourceHashAndJobTypeAndStatusIn(
                eq("alice"), eq("sha-1"), eq("TRANSCODE"), anyList())).thenReturn(true);

        assertNull(service.enqueue("alice", "sha-1", "TRANSCODE", "720p", "video/in/a.mp4", "a.mp4"));
        verify(jobRepository, never()).save(any(VideoJob.class));
    }

    @Test
    void enqueueDefaultsBlankJobTypeToTranscode() {
        when(jobRepository.existsByOwnerUsernameAndSourceHashAndJobTypeAndStatusIn(
                eq("alice"), eq("sha-1"), eq("TRANSCODE"), anyList())).thenReturn(false);
        when(jobRepository.save(any(VideoJob.class))).thenAnswer(inv -> inv.getArgument(0));

        VideoJob job = service.enqueue("alice", "sha-1", "  ", null, null, null);

        assertEquals("TRANSCODE", job.getJobType());
    }

    @Test
    void enqueueTruncatesOversizedPayload() {
        when(jobRepository.existsByOwnerUsernameAndSourceHashAndJobTypeAndStatusIn(
                eq("alice"), eq("sha-1"), eq("TRANSCODE"), anyList())).thenReturn(false);
        when(jobRepository.save(any(VideoJob.class))).thenAnswer(inv -> inv.getArgument(0));

        String longPayload = "x".repeat(900);
        VideoJob job = service.enqueue("alice", "sha-1", "TRANSCODE", null, null, longPayload);

        assertEquals(500, job.getPayload().length());
    }

    @Test
    void getForOwnerReturnsOwnJobAndRejectsUnknown() {
        VideoJob job = VideoJob.builder().id(3L).ownerUsername("alice").sourceHash("sha-1").build();
        when(jobRepository.findByIdAndOwnerUsername(3L, "alice")).thenReturn(Optional.of(job));
        assertEquals(3L, service.getForOwner(3L, "alice").getId());

        when(jobRepository.findByIdAndOwnerUsername(4L, "alice")).thenReturn(Optional.empty());
        assertThrows(IllegalArgumentException.class, () -> service.getForOwner(4L, "alice"));
    }

    @Test
    void replayDeadJobResetsToPendingWithAttemptsCleared() {
        VideoJob dead = VideoJob.builder()
                .id(3L).ownerUsername("alice").sourceHash("sha-1")
                .status(JobStatus.DEAD).attempts(3).maxAttempts(3).build();
        when(jobRepository.findById(3L)).thenReturn(Optional.of(dead));

        VideoJob replayed = service.replayDeadJob(3L);

        assertEquals(JobStatus.PENDING, replayed.getStatus());
        assertEquals(0, replayed.getAttempts());
        assertNull(replayed.getLeaseExpiresAt());
        assertNotNull(replayed.getNextRunAt());
    }

    @Test
    void replayRejectsJobsThatAreNotDead() {
        VideoJob pending = VideoJob.builder()
                .id(4L).ownerUsername("alice").sourceHash("sha-1")
                .status(JobStatus.PENDING).attempts(0).maxAttempts(3).build();
        when(jobRepository.findById(4L)).thenReturn(Optional.of(pending));

        assertThrows(IllegalStateException.class, () -> service.replayDeadJob(4L));
    }

    @Test
    void replayUnknownJobThrows() {
        when(jobRepository.findById(99L)).thenReturn(Optional.empty());

        assertThrows(IllegalArgumentException.class, () -> service.replayDeadJob(99L));
    }

    @Test
    void recoverExpiredLeasesDelegatesToRepository() {
        when(jobRepository.requeueExpiredLeases()).thenReturn(2);

        service.recoverExpiredLeases();

        verify(jobRepository).requeueExpiredLeases();
    }
}