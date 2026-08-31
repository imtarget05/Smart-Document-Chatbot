package com.smartdocchat.config;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.stereotype.Component;

import java.time.Duration;
import java.time.Instant;

@Component
@RequiredArgsConstructor
@Slf4j
public class RedisRateLimitStore {

    private final RedisTemplate<String, String> redisTemplate;

    /**
     * Check if request is allowed using sliding window rate limiting.
     * @param key unique identifier (scope:identity)
     * @param capacity max requests per window
     * @param windowDuration time window
     * @return true if request is allowed, false if rate limited
     */
    public boolean isAllowed(String key, int capacity, Duration windowDuration) {
        String redisKey = "ratelimit:" + key;
        long now = Instant.now().toEpochMilli();
        long windowStart = now - windowDuration.toMillis();

        try {
            // Remove old entries outside the window
            redisTemplate.opsForZSet().removeRangeByScore(redisKey, 0, windowStart);

            // Count current entries in window
            Long count = redisTemplate.opsForZSet().zCard(redisKey);

            if (count != null && count >= capacity) {
                return false;
            }

            // Add current request
            redisTemplate.opsForZSet().add(redisKey, String.valueOf(now), now);
            redisTemplate.expire(redisKey, windowDuration.plusSeconds(1));

            return true;
        } catch (Exception e) {
            log.warn("Redis rate limit check failed for key {}, allowing request (fail-open)", key, e);
            return true; // Fail open if Redis is unavailable
        }
    }

    /**
     * Get remaining capacity for a key.
     */
    public long getRemaining(String key, int capacity, Duration windowDuration) {
        String redisKey = "ratelimit:" + key;
        long windowStart = Instant.now().toEpochMilli() - windowDuration.toMillis();

        try {
            redisTemplate.opsForZSet().removeRangeByScore(redisKey, 0, windowStart);
            Long count = redisTemplate.opsForZSet().zCard(redisKey);
            return capacity - (count != null ? count : 0);
        } catch (Exception e) {
            return capacity; // Fail open
        }
    }
}
