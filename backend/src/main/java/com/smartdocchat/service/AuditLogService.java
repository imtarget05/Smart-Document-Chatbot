package com.smartdocchat.service;

import com.smartdocchat.entity.AuditLog;
import com.smartdocchat.repository.AuditLogRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;

/**
 * Audit trail service (production requirement #2).
 * Records security-relevant events into the immutable audit_logs table.
 *
 * Fail-safe by design: a failed audit write is logged and swallowed so it can
 * never break the business request it is observing. Callers should treat this
 * as best-effort persistence, unlike the document operations themselves.
 */
@Service
@RequiredArgsConstructor
@Slf4j
public class AuditLogService {

    private final AuditLogRepository auditLogRepository;

    public void record(String username, String action, String resourceType,
                       String resourceId, String ipAddress, String detail) {
        try {
            auditLogRepository.save(AuditLog.builder()
                    .username(username != null ? username : "anonymous")
                    .action(action)
                    .resourceType(resourceType)
                    .resourceId(resourceId)
                    .ipAddress(ipAddress)
                    .detail(detail)
                    .build());
        } catch (RuntimeException e) {
            // Audit failure must never break the protected operation.
            log.error("Failed to persist audit log for {} by {}: {}", action, username, e.getMessage());
        }
    }

    /** Read-only query API for admins. Filter arguments are nullable. */
    public Page<AuditLog> query(String username, String action, LocalDateTime from, Pageable pageable) {
        boolean hasUser = username != null && !username.isBlank();
        boolean hasAction = action != null && !action.isBlank();
        boolean hasFrom = from != null;

        if (hasUser && hasAction) {
            return hasFrom
                    ? auditLogRepository.findByUsernameAndActionAndCreatedAtAfter(username, action, from, pageable)
                    : auditLogRepository.findByUsernameAndAction(username, action, pageable);
        }
        if (hasUser) {
            return hasFrom
                    ? auditLogRepository.findByUsernameAndCreatedAtAfter(username, from, pageable)
                    : auditLogRepository.findByUsername(username, pageable);
        }
        if (hasAction) {
            return hasFrom
                    ? auditLogRepository.findByActionAndCreatedAtAfter(action, from, pageable)
                    : auditLogRepository.findByAction(action, pageable);
        }
        return hasFrom
                ? auditLogRepository.findByCreatedAtAfter(from, pageable)
                : auditLogRepository.findAll(pageable);
    }
}
