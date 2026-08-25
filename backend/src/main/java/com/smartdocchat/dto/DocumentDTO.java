package com.smartdocchat.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;
import java.time.LocalDateTime;

@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class DocumentDTO {
    private Long id;
    private String fileName;
    private String fileType;
    private Long fileSize;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;
    private Integer chunkCount;
    // Legal metadata (Decision 13/15/16A). Nullable.
    private String title;
    private String documentNumber;
    private String issuingBody;
    private java.time.LocalDate issueDate;
    private java.time.LocalDate effectiveDate;
    private String sourceType;
}