package com.smartdocchat.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;
import java.util.List;

@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class ChatResponse {
    private Long id;
    private String sessionId;
    private String userMessage;
    private String aiResponse;

    /** Raw source chunks text (backward-compatible for existing frontend) */
    private String sourceChunks;

    private Long documentId;
    private List<Long> documentIds;

    // ── Structured AI Engineer Output Fields ──────────────────────────

    /** Confidence level: "high", "medium", or "low" */
    private String confidence;

    /** Raw confidence score from vector retrieval (0.0 – 1.0) */
    private Double confidenceScore;

    /** End-to-end LLM processing latency in milliseconds */
    private Long latencyMs;

    /** Name of the LLM model used for generation */
    private String model;

    /** RAG strategy used: "direct", "corrective", "web_search", or "general_knowledge" */
    private String ragStrategy;

    /** Structured source citations with document name, score, and content */
    private List<SourceCitation> sources;
}
