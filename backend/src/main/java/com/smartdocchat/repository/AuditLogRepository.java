package com.smartdocchat.repository;

import com.smartdocchat.entity.AuditLog;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.time.LocalDateTime;
import java.util.List;

@Repository
public interface AuditLogRepository extends JpaRepository<AuditLog, Long> {

    Page<AuditLog> findByUserIdOrderByCreatedAtDesc(Long userId, Pageable pageable);

    Page<AuditLog> findByActionOrderByCreatedAtDesc(String action, Pageable pageable);

    Page<AuditLog> findByEntityTypeAndEntityIdOrderByCreatedAtDesc(String entityType, String entityId, Pageable pageable);

    @Query("SELECT a FROM AuditLog a WHERE " +
           "(:userId IS NULL OR a.userId = :userId) AND " +
           "(:action IS NULL OR a.action = :action) AND " +
           "(:entityType IS NULL OR a.entityType = :entityType) AND " +
           "(:startDate IS NULL OR a.createdAt >= :startDate) AND " +
           "(:endDate IS NULL OR a.createdAt <= :endDate) " +
           "ORDER BY a.createdAt DESC")
    Page<AuditLog> searchAuditLogs(
            @Param("userId") Long userId,
            @Param("action") String action,
            @Param("entityType") String entityType,
            @Param("startDate") LocalDateTime startDate,
            @Param("endDate") LocalDateTime endDate,
            Pageable pageable);

    List<AuditLog> findTop100ByOrderByCreatedAtDesc();

    long countByActionAndCreatedAtBetween(String action, LocalDateTime start, LocalDateTime end);

    long countByCreatedAtBetween(LocalDateTime start, LocalDateTime end);
}