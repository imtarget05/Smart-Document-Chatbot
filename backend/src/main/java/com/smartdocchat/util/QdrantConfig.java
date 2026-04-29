package com.smartdocchat.util;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.stereotype.Component;

@Component
@ConfigurationProperties(prefix = "qdrant")
@Data
public class QdrantConfig {
    private String host;
    private int port;
    private String collectionName;
}
