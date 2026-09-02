package com.smartdocchat.config;

import java.time.Duration;

/**
 * Rate-limit backing store. Implementations provide a sliding-window ledger
 * for tokens so callers can enforce a capacity per window without caring
 * whether the backing store is Redis (shared) or in-memory (per-instance).
 */
public interface RateLimitStore {

    /**
     * @return true if the key still has capacity in the current window, false if
     *         it is over the limit. When allowed, a timestamp is recorded so the
     *         next call consumes the budget.
     */
    boolean isAllowed(String key, int capacity, Duration windowDuration);

    /** @return remaining budget for the key in the current window. */
    long getRemaining(String key, int capacity, Duration windowDuration);
}