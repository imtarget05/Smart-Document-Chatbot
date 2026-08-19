package com.smartdocchat.service;

import org.junit.jupiter.api.Test;

import java.lang.reflect.Field;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

class LoginAuditServiceTest {

    private LoginAuditService service = new LoginAuditService();

    @Test
    void recordsFailuresAndLocksAccountAfterThreshold() {
        assertFalse(service.isAccountLocked("alice"));

        for (int i = 0; i < 4; i++) {
            service.recordFailure("Alice", "10.0.0.1");
            assertFalse(service.isAccountLocked("Alice"), "not locked yet at attempt " + (i + 1));
        }
        service.recordFailure("Alice", "10.0.0.1");
        assertTrue(service.isAccountLocked("alice"));
    }

    @Test
    void successfulLoginClearsFailureCount() {
        service.recordFailure("bob", "10.0.0.2");
        service.recordSuccess("BOB", "10.0.0.2");
        assertFalse(service.isAccountLocked("bob"));
    }

    @Test
    void lockoutExpiresAfterDuration() throws Exception {
        service.recordFailure("carol", "10.0.0.3");
        service.recordFailure("carol", "10.0.0.3");
        service.recordFailure("carol", "10.0.0.3");
        service.recordFailure("carol", "10.0.0.3");
        service.recordFailure("carol", "10.0.0.3");
        assertTrue(service.isAccountLocked("carol"));

        Field attemptsField = LoginAuditService.class.getDeclaredField("attempts");
        attemptsField.setAccessible(true);
        Object record = ((java.util.Map<?, ?>) attemptsField.get(service)).get("carol");
        Field lastField = record.getClass().getDeclaredField("lastFailureTime");
        lastField.setAccessible(true);
        lastField.set(record, java.time.Instant.now().minusSeconds(16 * 60));

        assertFalse(service.isAccountLocked("carol"));
        assertFalse(service.isAccountLocked("carol"));
    }

    @Test
    void unknownUserIsNeverLocked() {
        assertFalse(service.isAccountLocked("nobody"));
    }
}