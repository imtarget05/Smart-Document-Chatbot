package com.smartdocchat.security;

import com.smartdocchat.config.OidcProperties;
import com.smartdocchat.entity.Role;
import com.smartdocchat.entity.User;
import com.smartdocchat.repository.UserRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.security.core.GrantedAuthority;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.oauth2.client.oidc.userinfo.OidcUserRequest;
import org.springframework.security.oauth2.client.oidc.userinfo.OidcUserService;
import org.springframework.security.oauth2.core.oidc.user.DefaultOidcUser;
import org.springframework.security.oauth2.core.oidc.user.OidcUser;
import org.springframework.stereotype.Service;

import java.util.List;
import java.util.Map;

/**
 * Auto-provisioning OIDC user service (SSO — corporate identity).
 *
 * On first login the federated identity is materialised into the local
 * {@code users} table (disabled=false, role=ROLE_USER unless the username is
 * in sso.oidc.admin-usernames). Subsequent logins reuse the stored role so
 * Document RBAC and audit attribution work unchanged.
 */
@Service
@RequiredArgsConstructor
@Slf4j
public class CustomOidcUserService extends OidcUserService {

    private final UserRepository userRepository;
    private final OidcProperties oidcProperties;

    @Override
    public OidcUser loadUser(OidcUserRequest userRequest) {
        OidcUser oidcUser = super.loadUser(userRequest);
        Map<String, Object> claims = oidcUser.getClaims();

        String username = firstNonBlank(claims.get("preferred_username"), claims.get("email"));
        if (username == null) {
            throw new IllegalArgumentException("OIDC token carries no preferred_username or email claim");
        }

        Role role = resolveOrProvision(username);

        List<GrantedAuthority> authorities = List.of(new SimpleGrantedAuthority(role.name()));
        return new DefaultOidcUser(authorities, oidcUser.getIdToken(), oidcUser.getUserInfo());
    }

    /** Visible-for-testing: find the user's role or provision on first login. */
    Role resolveOrProvision(String username) {
        return userRepository.findByUsername(username)
                .map(User::getRole)
                .orElseGet(() -> provisionUser(username));
    }

    private Role provisionUser(String username) {
        Role role = oidcProperties.getAdminUsernames().contains(username.toLowerCase())
                ? Role.ROLE_ADMIN
                : Role.ROLE_USER;
        userRepository.save(User.builder()
                .username(username)
                // Local password never used for SSO accounts; placeholder hash
                // prevents null-password rows without enabling password login.
                .password("{noop}sso-provisioned")
                .role(role)
                .enabled(true)
                .build());
        log.info("SSO auto-provisioned user {} as {}", username, role);
        return role;
    }

    private String firstNonBlank(Object... candidates) {
        for (Object c : candidates) {
            if (c instanceof String s && !s.isBlank()) {
                return s;
            }
        }
        return null;
    }
}
