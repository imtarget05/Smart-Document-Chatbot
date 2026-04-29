package com.smartdocchat.util;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.stereotype.Component;

@Component
@ConfigurationProperties(prefix = "openai")
@Data
public class OpenAIConfig {
    private String apiKey;
    private String model;
    private String embeddingModel;
    private double temperature;
}
