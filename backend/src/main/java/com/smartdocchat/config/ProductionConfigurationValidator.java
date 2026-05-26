package com.smartdocchat.config;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.core.env.Environment;
import org.springframework.stereotype.Component;

import java.util.Arrays;

@Component
public class ProductionConfigurationValidator implements ApplicationRunner {
    private final Environment environment;
    private final String jwtSecret;
    private final String serviceToken;
    private final String databasePassword;

    public ProductionConfigurationValidator(
            Environment environment,
            @Value("${jwt.secret}") String jwtSecret,
            @Value("${service.internal-token}") String serviceToken,
            @Value("${spring.datasource.password}") String databasePassword) {
        this.environment = environment;
        this.jwtSecret = jwtSecret;
        this.serviceToken = serviceToken;
        this.databasePassword = databasePassword;
    }

    @Override
    public void run(ApplicationArguments args) {
        if (Arrays.stream(environment.getActiveProfiles()).noneMatch("production"::equals)) {
            return;
        }
        if (jwtSecret.startsWith("VGhpcy1pcy1hLWxvY2Fs") || jwtSecret.length() < 43) {
            throw new IllegalStateException("JWT_SECRET must be a unique base64-encoded 256-bit secret in production");
        }
        if (serviceToken.contains("local-development") || serviceToken.length() < 32) {
            throw new IllegalStateException("INTERNAL_SERVICE_TOKEN must be replaced with a strong secret in production");
        }
        if ("postgres".equals(databasePassword) || "CHANGE_ME".equals(databasePassword)) {
            throw new IllegalStateException("Database password must be replaced in production");
        }
    }
}
