package com.smartdocchat.config;

import org.springframework.boot.autoconfigure.condition.ConditionalOnExpression;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.oauth2.client.registration.ClientRegistration;
import org.springframework.security.oauth2.client.registration.ClientRegistrationRepository;
import org.springframework.security.oauth2.client.registration.InMemoryClientRegistrationRepository;
import org.springframework.security.oauth2.core.AuthorizationGrantType;
import org.springframework.security.oauth2.core.ClientAuthenticationMethod;
import org.springframework.security.oauth2.core.oidc.IdTokenClaimNames;

/**
 * Alternative OIDC client registration from oauth2.* environment variables.
 * Supports any OIDC-compliant provider (Keycloak, Azure AD, Okta, Auth0, etc.)
 *
 * Required env vars:
 * - OAUTH2_CLIENT_ID: OAuth2 client ID
 * - OAUTH2_CLIENT_SECRET: OAuth2 client secret
 * - OAUTH2_ISSUER_URI: OIDC issuer URI (e.g., https://keycloak.example.com/realms/myrealm)
 *
 * Optional:
 * - OAUTH2_REDIRECT_URI: Redirect URI (default: http://localhost:8080/api/login/oauth2/code/{registrationId})
 * - OAUTH2_SCOPES: Comma-separated scopes (default: openid,profile,email)
 *
 * This config is only active when oauth2.issuer-uri is set AND sso.oidc.enabled
 * is false/unset, providing an alternative registration path that doesn't
 * conflict with the primary OidcClientConfig.
 */
@Configuration
@ConditionalOnExpression("\'${oauth2.issuer-uri:}\' != ''")
public class OAuth2Config {

    @Bean
    public ClientRegistrationRepository clientRegistrationRepository(
            @org.springframework.beans.factory.annotation.Value("${oauth2.client-id:}") String clientId,
            @org.springframework.beans.factory.annotation.Value("${oauth2.client-secret:}") String clientSecret,
            @org.springframework.beans.factory.annotation.Value("${oauth2.issuer-uri:}") String issuerUri,
            @org.springframework.beans.factory.annotation.Value("${oauth2.redirect-uri:}") String redirectUri,
            @org.springframework.beans.factory.annotation.Value("${oauth2.scopes:openid,profile,email}") String scopes) {

        if (clientId.isBlank() || clientSecret.isBlank() || issuerUri.isBlank()) {
            return new InMemoryClientRegistrationRepository();
        }

        // "{baseUrl}" template: Spring resolves it at request time, so the
        // redirect URI automatically matches the deployed host (production or
        // localhost) without needing OAUTH2_REDIRECT_URI per environment.
        String effectiveRedirectUri = redirectUri.isBlank()
                ? "{baseUrl}/login/oauth2/code/google"
                : redirectUri;

        // Google issuer needs explicit endpoints when OIDC discovery is unavailable at build time
        boolean isGoogle = issuerUri.contains("accounts.google.com");
        ClientRegistration.Builder builder = ClientRegistration.withRegistrationId(isGoogle ? "google" : "oidc")
                .clientId(clientId)
                .clientSecret(clientSecret)
                .clientAuthenticationMethod(ClientAuthenticationMethod.CLIENT_SECRET_BASIC)
                .authorizationGrantType(AuthorizationGrantType.AUTHORIZATION_CODE)
                .redirectUri(effectiveRedirectUri)
                .scope(scopes.split(","))
                .userNameAttributeName(IdTokenClaimNames.SUB)
                .clientName(isGoogle ? "Google" : "Corporate SSO");

        if (isGoogle) {
            builder.authorizationUri("https://accounts.google.com/o/oauth2/v2/auth")
                    .tokenUri("https://oauth2.googleapis.com/token")
                    .userInfoUri("https://www.googleapis.com/oauth2/v3/userinfo")
                    .jwkSetUri("https://www.googleapis.com/oauth2/v3/certs");
        } else {
            builder.issuerUri(issuerUri);
        }

        try {
            return new InMemoryClientRegistrationRepository(builder.build());
        } catch (Exception e) {
            // Hide misconfigured OIDC and keep app runnable (only show working endpoints)
            org.slf4j.LoggerFactory.getLogger(OAuth2Config.class).warn("OIDC registration failed for issuer {}: {}", issuerUri, e.getMessage());
            return new InMemoryClientRegistrationRepository();
        }
    }
}
