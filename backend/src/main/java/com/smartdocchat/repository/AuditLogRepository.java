package com.smartdocchat.repository;

import com.smartdocchat.entity.AuditLog;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.time.LocalDateTime;

@Repository
public interface AuditLogRepository extends JpaRepository<AuditLog, Long> {

    Page<AuditLog> findByUsername(String username, Pageable pageable);

    Page<AuditLog> findByAction(String action, Pageable pageable);

    Page<AuditLog> findByUsernameAndAction(String username, String action, Pageable pageable);

    Page<AuditLog> findByCreatedAtAfter(LocalDateTime from, Pageable pageable);

    Page<AuditLog> findByUsernameAndCreatedAtAfter(String username, LocalDateTime from, Pageable pageable);

    Page<AuditLog> findByActionAndCreatedAtAfter(String action, LocalDateTime from, Pageable pageable);

    Page<AuditLog> findByUsernameAndActionAndCreatedAtAfter(
            String username, String action, LocalDateTime from, Pageable pageable);
}
