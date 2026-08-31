package com.smartdocchat.service;

import com.smartdocchat.entity.User;
import com.smartdocchat.repository.UserRepository;
import com.smartdocchat.util.JwtTokenProvider;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.security.oauth2.client.oidc.userinfo.OidcUserRequest;
import org.springframework.security.oauth2.client.oidc.userinfo.OidcUserService;
import org.springframework.security.oauth2.core.OAuth2AuthenticationException;
import org.springframework.security.oauth2.core.oidc.user.OidcUser;
import org.springframework.stereotype.Service;

import java.util.Optional;

/**
 * OIDC user service for OAuth2 login. Loads OIDC user and maps to internal user.
 * Creates user if not exists, generates internal JWT.
 *
 * This is a supplementary user service that can be used as an alternative to
 * CustomOidcUserService. It provides additional JWT generation capabilities
 * directly within the user service.
 */
@Service
@RequiredArgsConstructor
@Slf4j
public class OAuth2UserService extends OidcUserService {

    private final UserRepository userRepository;
    private final JwtTokenProvider jwtTokenProvider;
    private final AuditLogService auditLogService;

    /**
     * Load OIDC user and map to internal user.
     * Creates user if not exists, generates internal JWT.
     */
    @Override
    public OidcUser loadUser(OidcUserRequest userRequest) throws OAuth2AuthenticationException {
        OidcUser oidcUser = super.loadUser(userRequest);

        String email = oidcUser.getEmail();
        String name = oidcUser.getFullName();
        if (name == null) name = oidcUser.getGivenName();
        if (name == null) name = email;

        // Extract roles from ID token claims (if provided by IdP)
        String role = extractRole(oidcUser);

        // Find or create internal user
        Optional<User> existingUser = userRepository.findByUsername(email);
        User user;
        if (existingUser.isPresent()) {
            user = existingUser.get();
            // Update role if changed
            if (!user.getRole().name().equals(role)) {
                user.setRole(com.smartdocchat.entity.Role.valueOf(role));
                userRepository.save(user);
            }
        } else {
            user = User.builder()
                    .username(email)
                    .password("{noop}sso-provisioned")
                    .role(com.smartdocchat.entity.Role.valueOf(role))
                    .build();
            user = userRepository.save(user);
            log.info("Created new OAuth2 user: {} with role: {}", email, role);
        }

        auditLogService.record(user.getUsername(), "OAUTH2_LOGIN", "USER",
                user.getId().toString(), null, "SSO login via OIDC");

        // Generate internal JWT for the user
        String internalToken = jwtTokenProvider.generateToken(user.getUsername(), user.getRole().name());

        // Store the internal token as a claim (will be returned to client)
        oidcUser.getAttributes().put("internal_jwt", internalToken);

        return oidcUser;
    }

    private String extractRole(OidcUser oidcUser) {
        // Try to extract role from various claim locations
        // Azure AD: groups claim
        // Keycloak: realm_access.roles
        // Generic: role or roles claim

        Object rolesClaim = oidcUser.getClaim("roles");
        if (rolesClaim instanceof java.util.List<?> roles && !roles.isEmpty()) {
            String firstRole = roles.get(0).toString().toUpperCase();
            if (firstRole.contains("ADMIN")) return "ROLE_ADMIN";
            if (firstRole.contains("ENGINEER")) return "ROLE_ENGINEER";
        }

        // Default role for SSO users
        return "ROLE_USER";
    }
}
