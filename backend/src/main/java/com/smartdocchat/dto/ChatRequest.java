package com.smartdocchat.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
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
    @NotBlank(message = "Session ID must not be blank")
    @Size(max = 100, message = "Session ID must be at most 100 characters")
    private String sessionId;
    
    private Long documentId;
    private List<Long> documentIds;
    
    @NotBlank(message = "Message must not be blank")
    @Size(max = 8000, message = "Message must be at most 8000 characters")
    private String message;

    private boolean deepThinking;
    private boolean webSearch;
}
