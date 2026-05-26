package com.smartdocchat.dto;

import jakarta.validation.constraints.NotBlank;
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
    private String sessionId;
    
    private Long documentId;
    private List<Long> documentIds;
    
    @NotBlank(message = "Message must not be blank")
    private String message;
}
