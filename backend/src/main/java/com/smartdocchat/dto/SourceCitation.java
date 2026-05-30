package com.smartdocchat.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * Structured source citation for RAG responses.
 * Provides traceable evidence of which document chunk was used to generate the answer.
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class SourceCitation {
    /** Original filename of the source document */
    private String document;

    /** Database ID of the source document */
    private Long documentId;

    /** The text content of the retrieved chunk */
    private String content;

    /** Cosine similarity score between query and chunk (0.0 – 1.0) */
    private double score;
}
