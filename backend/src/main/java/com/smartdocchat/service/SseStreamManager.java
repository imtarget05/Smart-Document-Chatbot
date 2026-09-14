package com.smartdocchat.service;

import jakarta.annotation.PreDestroy;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;

/**
 * Manages the dedicated thread pool for Server-Sent Events (SSE) streaming chat tasks.
 * Provides safe execution and graceful shutdown.
 */
@Component
@Slf4j
public class SseStreamManager {

    private final ExecutorService streamExecutor;
    private final int configuredThreads;

    public SseStreamManager(@Value("${chat.sse.threads:0}") int sseThreads) {
        this.configuredThreads = sseThreads > 0 ? sseThreads : Math.max(4, Runtime.getRuntime().availableProcessors());
        this.streamExecutor = Executors.newFixedThreadPool(this.configuredThreads);
        log.info("Initialized SseStreamManager thread pool with {} threads", this.configuredThreads);
    }

    public SseStreamManager() {
        this(0);
    }

    /**
     * Executes an SSE streaming task asynchronously.
     *
     * @param task task to run
     */
    public void execute(Runnable task) {
        streamExecutor.execute(task);
    }

    /**
     * Exposes the underlying ExecutorService if needed.
     */
    public ExecutorService getExecutor() {
        return streamExecutor;
    }

    public int getConfiguredThreads() {
        return configuredThreads;
    }

    @PreDestroy
    public void shutdown() {
        log.info("Shutting down SseStreamManager executor pool...");
        streamExecutor.shutdown();
        try {
            if (!streamExecutor.awaitTermination(5, TimeUnit.SECONDS)) {
                log.warn("SseStreamManager pool did not terminate gracefully within 5s, forcing shutdown");
                streamExecutor.shutdownNow();
            }
        } catch (InterruptedException e) {
            log.warn("SseStreamManager shutdown interrupted, forcing shutdownNow");
            streamExecutor.shutdownNow();
            Thread.currentThread().interrupt();
        }
    }
}
