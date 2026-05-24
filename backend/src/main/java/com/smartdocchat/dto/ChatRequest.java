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
public class ChatRequest {
    private String sessionId;
    private Long documentId;
    private List<Long> documentIds;
    private String message;
}
