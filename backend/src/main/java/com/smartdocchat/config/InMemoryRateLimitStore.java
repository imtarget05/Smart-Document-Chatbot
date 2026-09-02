package com.smartdocchat.config;

import lombok.extern.slf4j.Slf4j;
import org.springframework.boot.autoconfigure.condition.ConditionalOnMissingBean;
import org.springframework.stereotype.Component;

import java.time.Duration;
import java.util.ArrayDeque;
import java.util.Deque;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Per-instance sliding-window rate-limit store used when Redis is absent.
 * Keeps the app running on single-instance/free tiers while still enforcing
 * limits — preventing the DoS hole a bare fail-open would open, without the
 * full-availability outage of fail-closed 503s.
 *
 * Budget is intentionally NOT shared across multiple instances; deploy behind
 * Redis when running more than one instance.
 */
@Component
@Slf4j
@ConditionalOnMissingBean(RedisRateLimitStore.class)
public class InMemoryRateLimitStore implements RateLimitStore {

    private final Map<String, Deque<Long>> buckets = new ConcurrentHashMap<>();

    @Override
    public boolean isAllowed(String key, int capacity, Duration windowDuration) {
        long now = System.currentTimeMillis();
        long windowStart = now - windowDuration.toMillis();

        Deque<Long> deque = buckets.computeIfAbsent(key, k -> new ArrayDeque<>());
        synchronized (deque) {
            while (!deque.isEmpty() && deque.peekFirst() < windowStart) {
                deque.pollFirst();
            }
            if (deque.size() >= capacity) {
                return false;
            }
            deque.addLast(now);
            return true;
        }
    }

    @Override
    public long getRemaining(String key, int capacity, Duration windowDuration) {
        long windowStart = System.currentTimeMillis() - windowDuration.toMillis();

        Deque<Long> deque = buckets.get(key);
        if (deque == null) {
            return capacity;
        }
        synchronized (deque) {
            while (!deque.isEmpty() && deque.peekFirst() < windowStart) {
                deque.pollFirst();
            }
            return Math.max(0, capacity - deque.size());
        }
    }
}