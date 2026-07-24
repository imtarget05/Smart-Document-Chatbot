package com.smartdocchat.service;

import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.time.Instant;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Login audit service with account lockout policy.
 * Tracks failed login attempts per username and locks accounts after threshold.
 * In production, back this with Redis for distributed deployments.
 */
@Slf4j
@Service
public class LoginAuditService {

    private static final int MAX_FAILED_ATTEMPTS = 5;
    private static final long LOCKOUT_DURATION_MINUTES = 15;

    // In-memory store; replace with Redis for multi-instance deployments
    private final Map<String, LoginAttemptRecord> attempts = new ConcurrentHashMap<>();

    public void recordFailure(String username, String ipAddress) {
        LoginAttemptRecord record = attempts.computeIfAbsent(username.toLowerCase(),
                k -> new LoginAttemptRecord());
        record.incrementFailure();
        log.warn("Failed login attempt {} for user {} from IP {}",
                record.getFailedAttempts(), username, ipAddress);
    }

    public void recordSuccess(String username, String ipAddress) {
        attempts.remove(username.toLowerCase());
        log.info("Successful login for user {} from IP {}", username, ipAddress);
    }

    public boolean isAccountLocked(String username) {
        LoginAttemptRecord record = attempts.get(username.toLowerCase());
        if (record == null) {
            return false;
        }
        if (record.getFailedAttempts() >= MAX_FAILED_ATTEMPTS) {
            if (record.isLockoutExpired(LOCKOUT_DURATION_MINUTES)) {
                attempts.remove(username.toLowerCase());
                return false;
            }
            return true;
        }
        return false;
    }

    private static class LoginAttemptRecord {
        private int failedAttempts = 0;
        private Instant lastFailureTime = Instant.now();

        synchronized void incrementFailure() {
            failedAttempts++;
            lastFailureTime = Instant.now();
        }

        int getFailedAttempts() {
            return failedAttempts;
        }

        boolean isLockoutExpired(long lockoutMinutes) {
            return Instant.now().isAfter(lastFailureTime.plusSeconds(lockoutMinutes * 60));
        }
    }
}
