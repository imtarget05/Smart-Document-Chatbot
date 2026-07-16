package com.smartdocchat.entity;

import jakarta.persistence.*;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

@Entity
@Table(name = "data_sources")
@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class DataSource {
    public enum SourceType {
        REST_API,
        DATABASE,
        SHAREPOINT,
        GOOGLE_DRIVE,
        SLACK,
        GMAIL
    }

    public enum SyncStatus {
        PENDING,
        SYNCING,
        READY,
        FAILED
    }

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false, unique = true)
    private String name;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false)
    private SourceType type;

    @Column(nullable = false)
    private String connectionUrl;

    @Column(nullable = false)
    private String description;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false)
    @Builder.Default
    private SyncStatus status = SyncStatus.PENDING;

    @Column(name = "created_at", nullable = false, updatable = false)
    private LocalDateTime createdAt;

    @PrePersist
    public void prePersist() {
        createdAt = LocalDateTime.now();
        if (status == null) {
            status = SyncStatus.PENDING;
        }
    }
}
