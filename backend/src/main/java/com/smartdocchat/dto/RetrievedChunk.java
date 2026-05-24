package com.smartdocchat.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class RetrievedChunk {
    private String text;
    private String parentText;
    private double score;

    public RetrievedChunk(String text, double score) {
        this.text = text;
        this.parentText = text;
        this.score = score;
    }
}
