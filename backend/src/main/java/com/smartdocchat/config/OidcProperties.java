package com.smartdocchat.config;

import lombok.Getter;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import java.util.Arrays;
import java.util.List;

/**
 * SSO/OIDC federation settings (corporate identity — Keycloak, Entra ID, Okta).
 *
 * Disabled by default so local JWT auth keeps working untouched. When
 * {@code SSO_OIDC_ENABLED=true}, the backend accepts OIDC authorization-code
 * logins, auto-provisions users into the {@code users} table on first login
 * and issues the same app JWT used by the local login flow.
 */
@Getter
@Component
public class OidcProperties {

    private final boolean enabled;
    private final String issuerUri;
    private final String clientId;
    private final String clientSecret;
    /** Frontend URL the browser is sent to after a successful OIDC login. */
    private final String postLoginRedirect;
    /** Usernames auto-promoted to ROLE_ADMIN on first SSO login. */
    private final List<String> adminUsernames;

    public OidcProperties(
            @Value("${sso.oidc.enabled:false}") boolean enabled,
            @Value("${sso.oidc.issuer-uri:}") String issuerUri,
            @Value("${sso.oidc.client-id:}") String clientId,
            @Value("${sso.oidc.client-secret:}") String clientSecret,
            @Value("${sso.oidc.post-login-redirect:http://localhost:3000}") String postLoginRedirect,
            @Value("${sso.oidc.admin-usernames:}") String adminUsernames) {
        this.enabled = enabled;
        this.issuerUri = issuerUri;
        this.clientId = clientId;
        this.clientSecret = clientSecret;
        this.postLoginRedirect = postLoginRedirect;
        this.adminUsernames = adminUsernames.isBlank()
                ? List.of()
                : Arrays.stream(adminUsernames.split(",")).map(String::trim).map(String::toLowerCase).toList();
    }
}
