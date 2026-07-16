package com.smartdocchat.service;

import com.smartdocchat.entity.AuditLog;
import com.smartdocchat.repository.AuditLogRepository;
import jakarta.servlet.http.HttpServletRequest;
import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.context.request.RequestContextHolder;
import org.springframework.web.context.request.ServletRequestAttributes;

import java.time.LocalDateTime;
import java.util.Optional;

@Service
@RequiredArgsConstructor
public class AuditService {

    private final AuditLogRepository auditLogRepository;

    @Transactional
    public AuditLog log(String action, String entityType, String entityId, String details, String status, String errorMessage) {
        AuditLog auditLog = AuditLog.builder()
                .userId(getCurrentUserId())
                .username(getCurrentUsername())
                .action(action)
                .entityType(entityType)
                .entityId(entityId)
                .details(details)
                .ipAddress(getClientIp())
                .userAgent(getUserAgent())
                .status(status != null ? status : "SUCCESS")
                .errorMessage(errorMessage)
                .build();
        return auditLogRepository.save(auditLog);
    }

    @Transactional
    public AuditLog logSuccess(String action, String entityType, String entityId, String details) {
        return log(action, entityType, entityId, details, "SUCCESS", null);
    }

    @Transactional
    public AuditLog logFailure(String action, String entityType, String entityId, String details, String errorMessage) {
        return log(action, entityType, entityId, details, "FAILURE", errorMessage);
    }

    @Transactional(readOnly = true)
    public Page<AuditLog> searchAuditLogs(Long userId, String action, String entityType,
                                          LocalDateTime startDate, LocalDateTime endDate, Pageable pageable) {
        return auditLogRepository.searchAuditLogs(userId, action, entityType, startDate, endDate, pageable);
    }

    @Transactional(readOnly = true)
    public Page<AuditLog> getAuditLogs(Pageable pageable) {
        return auditLogRepository.findAll(pageable);
    }

    @Transactional(readOnly = true)
    public Optional<AuditLog> getAuditLogById(Long id) {
        return auditLogRepository.findById(id);
    }

    @Transactional(readOnly = true)
    public long countActionsSince(String action, LocalDateTime since) {
        return auditLogRepository.countByActionAndCreatedAtBetween(action, since, LocalDateTime.now());
    }

    @Transactional(readOnly = true)
    public long countTotalSince(LocalDateTime since) {
        return auditLogRepository.countByCreatedAtBetween(since, LocalDateTime.now());
    }

    private Long getCurrentUserId() {
        try {
            ServletRequestAttributes attrs = (ServletRequestAttributes) RequestContextHolder.getRequestAttributes();
            if (attrs != null && attrs.getRequest().getAttribute("userId") != null) {
                return (Long) attrs.getRequest().getAttribute("userId");
            }
        } catch (Exception ignored) {}
        return null;
    }

    private String getCurrentUsername() {
        try {
            ServletRequestAttributes attrs = (ServletRequestAttributes) RequestContextHolder.getRequestAttributes();
            if (attrs != null && attrs.getRequest().getAttribute("username") != null) {
                return (String) attrs.getRequest().getAttribute("username");
            }
        } catch (Exception ignored) {}
        return "anonymous";
    }

    private String getClientIp() {
        try {
            ServletRequestAttributes attrs = (ServletRequestAttributes) RequestContextHolder.getRequestAttributes();
            if (attrs != null) {
                HttpServletRequest request = attrs.getRequest();
                String ip = request.getHeader("X-Forwarded-For");
                if (ip == null || ip.isEmpty()) ip = request.getRemoteAddr();
                return ip;
            }
        } catch (Exception ignored) {}
        return null;
    }

    private String getUserAgent() {
        try {
            ServletRequestAttributes attrs = (ServletRequestAttributes) RequestContextHolder.getRequestAttributes();
            if (attrs != null) {
                return attrs.getRequest().getHeader("User-Agent");
            }
        } catch (Exception ignored) {}
        return null;
    }
}