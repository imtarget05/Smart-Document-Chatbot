package com.smartdocchat.util;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.stereotype.Component;

@Component
@ConfigurationProperties(prefix = "openrouter")
@Data
public class OpenRouterConfig {
    private String apiKey;
    private String model;
    private double temperature;
}
