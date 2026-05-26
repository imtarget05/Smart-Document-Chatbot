package com.smartdocchat.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import lombok.Data;

import java.util.List;

@Data
public class EtlCompleteRequest {
    @NotBlank
    @JsonProperty("vector_collection_id")
    private String vectorCollectionId;

    @NotNull
    @Min(0)
    @JsonProperty("chunk_count")
    private Integer chunkCount;

    private String summary;
    @JsonProperty("suggested_questions")
    private List<String> suggestedQuestions;
}
