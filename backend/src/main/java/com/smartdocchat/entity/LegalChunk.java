package com.smartdocchat.entity;

import jakarta.persistence.*;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

/**
 * An addressable legal evidence unit extracted from a legal document
 * (article / clause / point granularity where detectable).
 *
 * Legal labels are nullable: a unit without verifiable structure carries
 * no invented metadata (null is preferred over a fabricated article number).
 */
@Entity
@Table(name = "legal_chunks", indexes = {
        @Index(name = "idx_legal_chunks_document_id", columnList = "document_id"),
        @Index(name = "idx_legal_chunks_doc_article", columnList = "document_id, article_number")
})
@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class LegalChunk {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "document_id", nullable = false)
    private Long documentId;

    /** Stable position of this unit within the document (0-based). */
    @Column(nullable = false)
    private Integer ordinal;

    @Column(nullable = false, columnDefinition = "TEXT")
    private String content;

    @Column(name = "chapter_number")
    private String chapterNumber;

    @Column(name = "article_number")
    private String articleNumber;

    @Column(name = "clause_number")
    private String clauseNumber;

    @Column(name = "point_label")
    private String pointLabel;

    @Column(name = "created_at", nullable = false, updatable = false)
    private LocalDateTime createdAt;

    @PrePersist
    public void prePersist() {
        createdAt = LocalDateTime.now();
    }
}