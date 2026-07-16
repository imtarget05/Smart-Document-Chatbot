package com.smartdocchat.entity;

import jakarta.persistence.*;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

@Entity
@Table(name = "eight_d_cases")
@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class EightDCase {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false)
    private String title;

    @Column(nullable = false)
    private String severity; // CRITICAL, HIGH, MEDIUM, LOW

    @Column(nullable = false)
    private String status; // OPEN, IN_PROGRESS, CLOSED

    @Column(nullable = false)
    private String owner;

    @Column(columnDefinition = "TEXT")
    private String summary;

    // D1: Team establishment
    @Column(name = "d1_team", columnDefinition = "TEXT")
    private String d1Team;

    // D2: Problem description
    @Column(name = "d2_describe", columnDefinition = "TEXT")
    private String d2Describe;

    // D3: Containment actions
    @Column(name = "d3_containment", columnDefinition = "TEXT")
    private String d3Containment;

    // D4: Root cause analysis
    @Column(name = "d4_root_cause", columnDefinition = "TEXT")
    private String d4RootCause;

    // D5: Corrective actions
    @Column(name = "d5_corrective", columnDefinition = "TEXT")
    private String d5Corrective;

    // D6: Verification of effectiveness
    @Column(name = "d6_verification", columnDefinition = "TEXT")
    private String d6Verification;

    // D7: Preventive measures
    @Column(name = "d7_preventive", columnDefinition = "TEXT")
    private String d7Preventive;

    // D8: Recognition & closure
    @Column(name = "d8_recognition", columnDefinition = "TEXT")
    private String d8Recognition;

    // Timeline of events as JSON string
    @Column(name = "timeline", columnDefinition = "TEXT")
    private String timeline;

    // AI-suggested actions/resolutions
    @Column(name = "ai_suggestions", columnDefinition = "TEXT")
    private String aiSuggestions;

    @Column(name = "document_id")
    private Long documentId;

    @Column(name = "created_at", nullable = false, updatable = false)
    private LocalDateTime createdAt;

    @Column(name = "updated_at")
    private LocalDateTime updatedAt;

    @PrePersist
    public void prePersist() {
        createdAt = LocalDateTime.now();
        updatedAt = LocalDateTime.now();
    }

    @PreUpdate
    public void preUpdate() {
        updatedAt = LocalDateTime.now();
    }
}