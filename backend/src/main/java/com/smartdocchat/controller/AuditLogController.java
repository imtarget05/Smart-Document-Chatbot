package com.smartdocchat.controller;

import com.smartdocchat.entity.AuditLog;
import com.smartdocchat.service.AuditLogService;
import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Sort;
import org.springframework.format.annotation.DateTimeFormat;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.*;

import java.time.LocalDateTime;
import java.util.LinkedHashMap;
import java.util.Map;

/**
 * Read-only audit trail API for administrators (production requirement #2).
 * Requires ROLE_ADMIN — enforced via method security on top of the JWT role
 * authority emitted by JwtAuthenticationFilter.
 */
@RestController
@RequestMapping("/admin/audit-logs")
@RequiredArgsConstructor
public class AuditLogController {

    private final AuditLogService auditLogService;

    @GetMapping
    @PreAuthorize("hasRole('ADMIN')")
    public ResponseEntity<Map<String, Object>> getAuditLogs(
            @RequestParam(required = false) String username,
            @RequestParam(required = false) String action,
            @RequestParam(required = false)
            @DateTimeFormat(iso = DateTimeFormat.ISO.DATE_TIME) LocalDateTime from,
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "50") int size) {

        if (size < 1 || size > 200) {
            size = 50;
        }
        if (page < 0) {
            page = 0;
        }

        Page<AuditLog> result = auditLogService.query(username, action, from,
                PageRequest.of(page, size, Sort.by(Sort.Direction.DESC, "createdAt")));

        Map<String, Object> body = new LinkedHashMap<>();
        body.put("page", result.getNumber());
        body.put("size", result.getSize());
        body.put("totalElements", result.getTotalElements());
        body.put("totalPages", result.getTotalPages());
        body.put("logs", result.getContent().stream().map(l -> {
            Map<String, Object> m = new LinkedHashMap<>();
            m.put("id", l.getId());
            m.put("username", l.getUsername());
            m.put("action", l.getAction());
            m.put("resourceType", l.getResourceType());
            m.put("resourceId", l.getResourceId());
            m.put("ipAddress", l.getIpAddress());
            m.put("detail", l.getDetail());
            m.put("createdAt", l.getCreatedAt());
            return m;
        }).toList());
        return ResponseEntity.ok(body);
    }
}
