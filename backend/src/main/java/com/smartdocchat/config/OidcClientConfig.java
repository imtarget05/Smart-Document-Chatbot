package com.smartdocchat.config;

import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.oauth2.client.registration.ClientRegistration;
import org.springframework.security.oauth2.client.registration.ClientRegistrations;
import org.springframework.security.oauth2.client.registration.ClientRegistrationRepository;
import org.springframework.security.oauth2.client.registration.InMemoryClientRegistrationRepository;
import org.springframework.security.oauth2.core.AuthorizationGrantType;

/**
 * OIDC client registration for SSO. The bean only exists when
 * {@code sso.oidc.enabled=true}, so deployments without an identity provider
 * (local/dev, JWT-only production) start exactly as before.
 */
@Configuration
@ConditionalOnProperty(name = "sso.oidc.enabled", havingValue = "true")
public class OidcClientConfig {

    @Bean
    public ClientRegistrationRepository clientRegistrationRepository(OidcProperties properties) {
        ClientRegistration registration = ClientRegistrations
                .fromIssuerLocation(properties.getIssuerUri())
                .registrationId("corporate")
                .clientId(properties.getClientId())
                .clientSecret(properties.getClientSecret())
                .scope("openid", "profile", "email")
                .authorizationGrantType(AuthorizationGrantType.AUTHORIZATION_CODE)
                .build();
        return new InMemoryClientRegistrationRepository(registration);
    }
}
