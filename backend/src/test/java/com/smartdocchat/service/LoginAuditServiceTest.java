package com.smartdocchat.service;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.data.redis.core.HashOperations;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.data.redis.core.ValueOperations;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
class LoginAuditServiceTest {

    @Mock
    private RedisTemplate<String, String> redisTemplate;

    @Mock
    private ValueOperations<String, String> valueOps;

    @Mock
    private HashOperations<String, String, String> hashOps;

    private LoginAuditService service;

    @BeforeEach
    void setUp() {
        lenient().doReturn(valueOps).when(redisTemplate).opsForValue();
        lenient().doReturn(hashOps).when(redisTemplate).opsForHash();
        service = new LoginAuditService(redisTemplate);
    }

    @Test
    void recordsFailuresAndLocksAccountAfterThreshold() {
        // Counter starts at 0; each recordFailure increments.
        java.util.concurrent.atomic.AtomicInteger count = new java.util.concurrent.atomic.AtomicInteger();
        when(valueOps.get("login:failures:alice")).thenAnswer(inv -> String.valueOf(count.get()));
        when(valueOps.increment("login:failures:alice")).thenAnswer(inv -> count.incrementAndGet());

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
        when(valueOps.increment("login:failures:bob")).thenReturn(1L);
        when(valueOps.get("login:failures:bob")).thenReturn("1");

        service.recordFailure("bob", "10.0.0.2");
        service.recordSuccess("BOB", "10.0.0.2");

        assertFalse(service.isAccountLocked("bob"));
        verify(redisTemplate).delete("login:failures:bob");
        verify(redisTemplate).delete("login:last_failure:bob");
    }

    @Test
    void accountLockedAfterMaxFailedAttempts() {
        when(valueOps.get("login:failures:carol")).thenReturn("5");

        assertTrue(service.isAccountLocked("carol"));
    }

    @Test
    void unknownUserIsNeverLocked() {
        when(valueOps.get("login:failures:nobody")).thenReturn(null);

        assertFalse(service.isAccountLocked("nobody"));
    }

    @Test
    void redisFailureFailsOpen() {
        when(valueOps.get(anyString())).thenThrow(new RuntimeException("Redis down"));

        assertFalse(service.isAccountLocked("dave"));
    }
}
