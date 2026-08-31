package com.smartdocchat.security;

import com.smartdocchat.config.OidcProperties;
import com.smartdocchat.entity.Role;
import com.smartdocchat.entity.User;
import com.smartdocchat.repository.UserRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.util.Optional;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class CustomOidcUserServiceTest {

    @Mock private UserRepository userRepository;

    private OidcProperties properties;
    private CustomOidcUserService service;

    @BeforeEach
    void setUp() {
        properties = new OidcProperties(true, "https://idp", "cid", "secret", "http://fe", "");
        service = new CustomOidcUserService(userRepository, properties);
    }

    @Test
    void firstLoginProvisionsUserAsViewer() {
        when(userRepository.findByUsername("tuan@corp.vn")).thenReturn(Optional.empty());
        when(userRepository.save(any(User.class))).thenAnswer(inv -> inv.getArgument(0));

        Role role = service.resolveOrProvision("tuan@corp.vn");

        assertEquals(Role.ROLE_USER, role);
        ArgumentCaptor<User> captor = org.mockito.ArgumentCaptor.forClass(User.class);
        verify(userRepository).save(captor.capture());
        User provisioned = captor.getValue();
        assertEquals("tuan@corp.vn", provisioned.getUsername());
        assertEquals(Role.ROLE_USER, provisioned.getRole());
        assertEquals(Boolean.TRUE, provisioned.getEnabled());
        // Placeholder password: SSO accounts must not be usable for password login.
        assertEquals("{noop}sso-provisioned", provisioned.getPassword());
    }

    @Test
    void existingUserKeepsAssignedRoleWithoutResave() {
        User existing = User.builder().username("tuan@corp.vn").role(Role.ROLE_ENGINEER).enabled(true).build();
        when(userRepository.findByUsername("tuan@corp.vn")).thenReturn(Optional.of(existing));

        assertEquals(Role.ROLE_ENGINEER, service.resolveOrProvision("tuan@corp.vn"));
        verify(userRepository, never()).save(any(User.class));
    }

    @Test
    void listedUsernamesArePromotedToAdminOnProvision() {
        properties = new OidcProperties(true, "https://idp", "cid", "secret", "http://fe", "Tuan, hoa");
        service = new CustomOidcUserService(userRepository, properties);
        when(userRepository.findByUsername("tuan")).thenReturn(Optional.empty());
        when(userRepository.save(any(User.class))).thenAnswer(inv -> inv.getArgument(0));

        assertEquals(Role.ROLE_ADMIN, service.resolveOrProvision("tuan"));

        ArgumentCaptor<User> captor = org.mockito.ArgumentCaptor.forClass(User.class);
        verify(userRepository).save(captor.capture());
        assertEquals(Role.ROLE_ADMIN, captor.getValue().getRole());
    }

    @Test
    void listedUsernamesAreMatchedCaseInsensitively() {
        properties = new OidcProperties(true, "https://idp", "cid", "secret", "http://fe", "tuan");
        service = new CustomOidcUserService(userRepository, properties);
        when(userRepository.findByUsername("TUAN")).thenReturn(Optional.empty());
        when(userRepository.save(any(User.class))).thenAnswer(inv -> inv.getArgument(0));

        assertEquals(Role.ROLE_ADMIN, service.resolveOrProvision("TUAN"));
    }

    @Test
    void unlistedNameGetsViewerRole() {
        properties = new OidcProperties(true, "https://idp", "cid", "secret", "http://fe", "tuan");
        service = new CustomOidcUserService(userRepository, properties);
        when(userRepository.findByUsername("hoa")).thenReturn(Optional.empty());
        when(userRepository.save(any(User.class))).thenAnswer(inv -> inv.getArgument(0));

        assertEquals(Role.ROLE_USER, service.resolveOrProvision("hoa"));
    }
}
