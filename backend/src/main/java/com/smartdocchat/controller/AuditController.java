package com.smartdocchat.controller;

import com.smartdocchat.entity.AuditLog;
import com.smartdocchat.service.AuditService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.web.PageableDefault;
import org.springframework.format.annotation.DateTimeFormat;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.*;

import java.time.LocalDateTime;
import java.util.Map;

@RestController
@RequestMapping("/api/audit")
@RequiredArgsConstructor
@Slf4j
@PreAuthorize("hasRole('ADMIN')")
public class AuditController {

    private final AuditService auditService;

    @GetMapping
    public ResponseEntity<Page<AuditLog>> getAllAuditLogs(
            @PageableDefault(size = 50) Pageable pageable) {
        return ResponseEntity.ok(auditService.getAuditLogs(pageable));
    }

    @GetMapping("/search")
    public ResponseEntity<Page<AuditLog>> searchAuditLogs(
            @RequestParam(required = false) Long userId,
            @RequestParam(required = false) String action,
            @RequestParam(required = false) String entityType,
            @RequestParam(required = false) @DateTimeFormat(iso = DateTimeFormat.ISO.DATE_TIME) LocalDateTime startDate,
            @RequestParam(required = false) @DateTimeFormat(iso = DateTimeFormat.ISO.DATE_TIME) LocalDateTime endDate,
            @PageableDefault(size = 50) Pageable pageable) {
        return ResponseEntity.ok(auditService.searchAuditLogs(userId, action, entityType, startDate, endDate, pageable));
    }

    @GetMapping("/{id}")
    public ResponseEntity<AuditLog> getAuditLogById(@PathVariable Long id) {
        return auditService.getAuditLogById(id)
                .map(ResponseEntity::ok)
                .orElse(ResponseEntity.notFound().build());
    }

    @GetMapping("/stats")
    public ResponseEntity<Map<String, Object>> getAuditStats() {
        LocalDateTime now = LocalDateTime.now();
        LocalDateTime last24h = now.minusHours(24);
        LocalDateTime last7d = now.minusDays(7);

        return ResponseEntity.ok(Map.of(
                "totalLast24h", auditService.countTotalSince(last24h),
                "totalLast7d", auditService.countTotalSince(last7d),
                "failedLast24h", auditService.countActionsSince("FAILURE", last24h),
                "timestamp", now.toString()
        ));
    }
}