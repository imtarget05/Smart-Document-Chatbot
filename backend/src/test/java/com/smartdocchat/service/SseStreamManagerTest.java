package com.smartdocchat.service;

import org.junit.jupiter.api.Test;

import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;

import static org.junit.jupiter.api.Assertions.*;

class SseStreamManagerTest {

    @Test
    void defaultConstructorInitializesPoolWithAtLeastFourThreads() {
        SseStreamManager manager = new SseStreamManager();
        try {
            assertTrue(manager.getConfiguredThreads() >= 4);
            assertNotNull(manager.getExecutor());
            assertFalse(manager.getExecutor().isShutdown());
        } finally {
            manager.shutdown();
        }
    }

    @Test
    void customThreadsConstructorInitializesPool() {
        SseStreamManager manager = new SseStreamManager(8);
        try {
            assertEquals(8, manager.getConfiguredThreads());
            assertNotNull(manager.getExecutor());
        } finally {
            manager.shutdown();
        }
    }

    @Test
    void executeRunsTaskAsynchronously() throws InterruptedException {
        SseStreamManager manager = new SseStreamManager(2);
        AtomicBoolean executed = new AtomicBoolean(false);
        CountDownLatch latch = new CountDownLatch(1);

        try {
            manager.execute(() -> {
                executed.set(true);
                latch.countDown();
            });

            boolean completed = latch.await(2, TimeUnit.SECONDS);
            assertTrue(completed, "Task should complete within timeout");
            assertTrue(executed.get(), "Task should set executed to true");
        } finally {
            manager.shutdown();
        }
    }

    @Test
    void shutdownGracefullyTerminatesExecutor() {
        SseStreamManager manager = new SseStreamManager(2);
        manager.shutdown();
        assertTrue(manager.getExecutor().isShutdown());
    }
}
