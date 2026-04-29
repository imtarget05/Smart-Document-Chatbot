package com.smartdocchat.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class ChatResponse {
    private Long id;
    private String sessionId;
    private String userMessage;
    private String aiResponse;
    private String sourceChunks;
    private Long documentId;
}
