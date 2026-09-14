package com.smartdocchat.service;

import com.smartdocchat.dto.ChatRequest;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.util.concurrent.ConcurrentHashMap;

/**
 * Service responsible for agent request deduplication with short-term sliding window.
 */
@Service
@Slf4j
public class ChatDedupService {

    private static final long DEDUP_WINDOW_MS = 5000L;
    private static final long EVICTION_TTL_MS = 30000L;

    private final ConcurrentHashMap<String, Long> dedupCache = new ConcurrentHashMap<>();

    /**
     * Checks if the incoming request is a duplicate of a recent request within the 5s window.
     * Also evicts stale entries older than 30s.
     *
     * @param ownerUsername username of the user making the request
     * @param request       chat request payload
     * @return true if this request is duplicate and should be suppressed, false otherwise
     */
    public boolean isDuplicateRequest(String ownerUsername, ChatRequest request) {
        if (request == null || request.getMessage() == null) {
            return false;
        }
        return isDuplicate(ownerUsername, request.getSessionId(), request.getMessage());
    }

    /**
     * Core deduplication check by owner, session, and message content hash.
     *
     * @param ownerUsername user identity
     * @param sessionId     session identifier
     * @param message       raw user message
     * @return true if duplicate within 5s, false otherwise
     */
    public boolean isDuplicate(String ownerUsername, String sessionId, String message) {
        String key = ownerUsername + ":" + sessionId + ":" + (message != null ? message.hashCode() : 0);
        long now = System.currentTimeMillis();
        Long prev = dedupCache.get(key);
        if (prev != null && (now - prev) < DEDUP_WINDOW_MS) {
            log.warn("Duplicate agent request suppressed key={}", key);
            return true;
        }
        dedupCache.put(key, now);
        // evict old entries >30s
        dedupCache.entrySet().removeIf(e -> (now - e.getValue()) > EVICTION_TTL_MS);
        return false;
    }

    public void clear() {
        dedupCache.clear();
    }

    public int size() {
        return dedupCache.size();
    }
}
