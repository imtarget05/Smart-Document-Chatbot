package com.smartdocchat.config;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.stereotype.Component;

/**
 * Security guards for the classic chat path.
 */
@Component
@ConfigurationProperties(prefix = "security.prompt-injection")
@Data
public class PromptInjectionProperties {

    /** Enable heuristic prompt-injection detection on user messages. */
    private boolean enabled = true;
}