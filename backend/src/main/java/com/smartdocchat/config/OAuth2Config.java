package com.smartdocchat.config;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.oauth2.client.registration.ClientRegistration;
import org.springframework.security.oauth2.client.registration.ClientRegistrationRepository;
import org.springframework.security.oauth2.client.registration.InMemoryClientRegistrationRepository;
import org.springframework.security.oauth2.core.AuthorizationGrantType;
import org.springframework.security.oauth2.core.ClientAuthenticationMethod;
import org.springframework.security.oauth2.core.oidc.IdTokenClaimNames;

@Configuration
public class OAuth2Config {

    /**
     * OIDC client registration for corporate SSO (Keycloak, Azure AD, Okta, Auth0...).
     *
     * Properties (oauth2.* takes precedence, sso.oidc.* is the fallback):
     * - oauth2.client-id     / sso.oidc.client-id
     * - oauth2.client-secret / sso.oidc.client-secret
     * - oauth2.issuer-uri    / sso.oidc.issuer-uri
     * - oauth2.redirect-uri  (default: http://localhost:8080/api/login/oauth2/code/oidc)
     * - oauth2.scopes        (default: openid,profile,email)
     *
     * When nothing is configured an EMPTY repository is registered so local
     * JWT deployments start exactly as before. The oauth2Login flow itself is
     * only wired into the security chain when sso.oidc.enabled=true
     * (see SecurityConfig).
     */
    @Bean
    public ClientRegistrationRepository clientRegistrationRepository(
            @org.springframework.beans.factory.annotation.Value("${oauth2.client-id:${sso.oidc.client-id:}}") String clientId,
            @org.springframework.beans.factory.annotation.Value("${oauth2.client-secret:${sso.oidc.client-secret:}}") String clientSecret,
            @org.springframework.beans.factory.annotation.Value("${oauth2.issuer-uri:${sso.oidc.issuer-uri:}}") String issuerUri,
            @org.springframework.beans.factory.annotation.Value("${oauth2.redirect-uri:}") String redirectUri,
            @org.springframework.beans.factory.annotation.Value("${oauth2.scopes:openid,profile,email}") String scopes) {

        if (clientId.isBlank() || clientSecret.isBlank() || issuerUri.isBlank()) {
            // Return empty repository if not configured
            return new InMemoryClientRegistrationRepository();
        }

        String effectiveRedirectUri = redirectUri.isBlank()
                ? "http://localhost:8080/api/login/oauth2/code/oidc"
                : redirectUri;

        ClientRegistration registration = ClientRegistration.withRegistrationId("oidc")
                .clientId(clientId)
                .clientSecret(clientSecret)
                .clientAuthenticationMethod(ClientAuthenticationMethod.CLIENT_SECRET_BASIC)
                .authorizationGrantType(AuthorizationGrantType.AUTHORIZATION_CODE)
                .redirectUri(effectiveRedirectUri)
                .scope(scopes.split(","))
                .issuerUri(issuerUri)
                .userNameAttributeName(IdTokenClaimNames.SUB)
                .clientName("Corporate SSO")
                .build();

        return new InMemoryClientRegistrationRepository(registration);
    }
}
