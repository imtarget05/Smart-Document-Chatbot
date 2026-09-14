package com.smartdocchat.service;

import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Service managing Dead Letter Queue (DLQ) for failed SSE streaming chat tasks.
 * Retains failed entries (up to 1000 items) for manual replay or debugging.
 */
@Service
@Slf4j
public class ChatDlqService {

    private static final int MAX_DLQ_SIZE = 1000;

    private final ConcurrentHashMap<String, String> dlq = new ConcurrentHashMap<>();

    /**
     * Record a failed chat task in the DLQ.
     *
     * @param ownerUsername username of the user
     * @param sessionId     session identifier
     * @param query         user query that failed
     * @param error         error message
     */
    public void recordDlq(String ownerUsername, String sessionId, String query, String error) {
        String key = sessionId + ":" + System.currentTimeMillis();
        dlq.put(key, ownerUsername + "|" + query + "|" + error);
        if (dlq.size() > MAX_DLQ_SIZE) {
            // drop oldest
            dlq.keySet().stream().sorted().limit(dlq.size() - MAX_DLQ_SIZE).forEach(dlq::remove);
        }
        log.warn("DLQ recorded key={} session={} err={}", key, sessionId, error);
    }

    /**
     * Record alias for convenience.
     */
    public void record(String ownerUsername, String sessionId, String query, String error) {
        recordDlq(ownerUsername, sessionId, query, error);
    }

    /**
     * Returns an unmodifiable snapshot copy of the current DLQ entries.
     */
    public Map<String, String> getDlqSnapshot() {
        return Map.copyOf(dlq);
    }

    /**
     * Alias for getDlqSnapshot().
     */
    public Map<String, String> getSnapshot() {
        return getDlqSnapshot();
    }

    public void clear() {
        dlq.clear();
    }

    public int size() {
        return dlq.size();
    }
}
