package com.smartdocchat.service;

import com.smartdocchat.entity.AuditLog;
import com.smartdocchat.repository.AuditLogRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageImpl;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;

import java.time.LocalDateTime;
import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertDoesNotThrow;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class AuditLogServiceTest {

    @Mock private AuditLogRepository auditLogRepository;

    private AuditLogService auditLogService;

    @BeforeEach
    void setUp() {
        auditLogService = new AuditLogService(auditLogRepository);
    }

    @Test
    void recordPersistsAuditEntry() {
        auditLogService.record("alice", "document.read", "document", "1", "1.2.3.4", "granted=true");

        verify(auditLogRepository).save(org.mockito.ArgumentMatchers.argThat(log ->
                "alice".equals(log.getUsername())
                        && "document.read".equals(log.getAction())
                        && "document".equals(log.getResourceType())
                        && "1".equals(log.getResourceId())
                        && "1.2.3.4".equals(log.getIpAddress())
                        && "granted=true".equals(log.getDetail())));
    }

    @Test
    void recordNeverBreaksCallerWhenRepositoryFails() {
        when(auditLogRepository.save(any(AuditLog.class)))
                .thenThrow(new RuntimeException("db down"));

        // Fail-safe: the protected operation must continue even if audit fails.
        assertDoesNotThrow(() -> auditLogService.record("alice", "auth.login", "user", "alice", null, "success"));
        verify(auditLogRepository).save(any(AuditLog.class));
    }

    @Test
    void recordDefaultsAnonymousUsername() {
        auditLogService.record(null, "auth.login.failed", "user", "ghost", "10.0.0.1", "invalid credentials");

        verify(auditLogRepository).save(org.mockito.ArgumentMatchers.argThat(log ->
                "anonymous".equals(log.getUsername())));
    }

    @Test
    void queryWithoutFiltersReturnsEverything() {
        Pageable pageable = PageRequest.of(0, 50);
        AuditLog entry = AuditLog.builder().id(1L).username("alice").action("document.read").build();
        when(auditLogRepository.findAll(pageable)).thenReturn(new PageImpl<>(List.of(entry)));

        assertEquals(1, auditLogService.query(null, null, null, pageable).getTotalElements());
        verify(auditLogRepository).findAll(pageable);
    }

    @Test
    void queryFiltersByUserActionAndDate() {
        Pageable pageable = PageRequest.of(0, 50);
        LocalDateTime from = LocalDateTime.now().minusDays(1);

        when(auditLogRepository.findByUsername("alice", pageable)).thenReturn(Page.empty());
        when(auditLogRepository.findByAction("auth.login", pageable)).thenReturn(Page.empty());
        when(auditLogRepository.findByUsernameAndAction("alice", "auth.login", pageable)).thenReturn(Page.empty());
        when(auditLogRepository.findByUsernameAndActionAndCreatedAtAfter("alice", "auth.login", from, pageable))
                .thenReturn(Page.empty());
        when(auditLogRepository.findByUsernameAndCreatedAtAfter("alice", from, pageable)).thenReturn(Page.empty());
        when(auditLogRepository.findByActionAndCreatedAtAfter("auth.login", from, pageable)).thenReturn(Page.empty());
        when(auditLogRepository.findByCreatedAtAfter(from, pageable)).thenReturn(Page.empty());

        auditLogService.query("alice", null, null, pageable);
        auditLogService.query(null, "auth.login", null, pageable);
        auditLogService.query("alice", "auth.login", null, pageable);
        auditLogService.query("alice", "auth.login", from, pageable);
        auditLogService.query("alice", null, from, pageable);
        auditLogService.query(null, "auth.login", from, pageable);
        auditLogService.query(null, null, from, pageable);
    }
}
