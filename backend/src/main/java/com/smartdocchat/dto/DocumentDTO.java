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
}
