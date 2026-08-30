package com.smartdocchat.config;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.stereotype.Component;

/**
 * Document ingestion (chunking) configuration.
 *
 * chunkSize — target size of each chunk, in tokens (approx. 4 chars/token).
 * chunkOverlap — number of tokens carried over from the end of one chunk to
 * the start of the next, so sentences spanning a chunk boundary keep local
 * context for retrieval. Must be smaller than chunkSize.
 */
@Component
@ConfigurationProperties(prefix = "ingestion")
@Data
public class IngestionConfig {
    private int chunkSize = 500;
    private int chunkOverlap = 100;
}