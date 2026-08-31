package com.smartdocchat.controller;

import com.smartdocchat.dto.AuthRequest;
import com.smartdocchat.dto.AuthResponse;
import com.smartdocchat.dto.RegisterRequest;
import com.smartdocchat.entity.Role;
import com.smartdocchat.entity.User;
import com.smartdocchat.repository.UserRepository;
import com.smartdocchat.service.LoginAuditService;
import com.smartdocchat.util.JwtTokenProvider;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.mock.web.MockHttpServletRequest;
import org.springframework.mock.web.MockHttpServletResponse;
import org.springframework.security.crypto.password.PasswordEncoder;

import java.util.Optional;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class AuthControllerTest {

    @Mock private UserRepository userRepository;
    @Mock private PasswordEncoder passwordEncoder;
    @Mock private JwtTokenProvider tokenProvider;
    @Mock private LoginAuditService loginAuditService;
    @Mock private com.smartdocchat.service.AuditLogService auditLogService;

    private AuthController controller;

    private AuthRequest request(String username, String password) {
        return AuthRequest.builder().username(username).password(password).build();
    }

    private RegisterRequest registerRequest(String username, String password, String email) {
        return RegisterRequest.builder().username(username).password(password).email(email).build();
    }

    private User enabledUser(String username, String encoded) {
        return User.builder().username(username).password(encoded).role(Role.ROLE_USER).enabled(true).build();
    }

    @Test
    void registerCreatesUserAndReturnsToken() {
        controller = new AuthController(userRepository, passwordEncoder, tokenProvider, loginAuditService, auditLogService);
        when(userRepository.existsByUsername("alice")).thenReturn(false);
        when(passwordEncoder.encode("password123456")).thenReturn("encoded");
        when(userRepository.save(any(User.class))).thenAnswer(inv -> inv.getArgument(0));
        when(tokenProvider.generateToken("alice", "ROLE_USER")).thenReturn("jwt-token");

        ResponseEntity<?> response = controller.registerUser(registerRequest("alice", "password123456", "alice@example.com"));

        assertEquals(HttpStatus.OK, response.getStatusCode());
        AuthResponse body = (AuthResponse) response.getBody();
        assertEquals("jwt-token", body.getToken());
        assertEquals("alice", body.getUsername());
        assertEquals("ROLE_USER", body.getRole());
    }

    @Test
    void registerRejectsDuplicateUsername() {
        controller = new AuthController(userRepository, passwordEncoder, tokenProvider, loginAuditService, auditLogService);
        when(userRepository.existsByUsername("alice")).thenReturn(true);

        ResponseEntity<?> response = controller.registerUser(registerRequest("alice", "password123456", "alice@example.com"));

        assertEquals(HttpStatus.BAD_REQUEST, response.getStatusCode());
        assertEquals("Username is already taken!", response.getBody());
    }

    @Test
    void loginSucceedsAndSetsHttpOnlyCookie() {
        controller = new AuthController(userRepository, passwordEncoder, tokenProvider, loginAuditService, auditLogService);
        when(userRepository.findByUsername("bob")).thenReturn(Optional.of(enabledUser("bob", "encoded")));
        when(passwordEncoder.matches("password123456", "encoded")).thenReturn(true);
        when(tokenProvider.generateToken("bob", "ROLE_USER")).thenReturn("jwt-cookie");

        MockHttpServletRequest servletRequest = new MockHttpServletRequest();
        servletRequest.setRemoteAddr("10.0.0.9");
        MockHttpServletResponse servletResponse = new MockHttpServletResponse();
        ResponseEntity<?> response =
                controller.authenticateUser(request("bob", "password123456"), servletRequest, servletResponse);

        assertEquals(HttpStatus.OK, response.getStatusCode());
        assertEquals("jwt-cookie", ((AuthResponse) response.getBody()).getToken());
        verify(loginAuditService).recordSuccess("bob", "10.0.0.9");
        assertEquals("jwt-cookie", servletResponse.getCookie("jwt_token").getValue());
        assertTrue(servletResponse.getCookie("jwt_token").isHttpOnly());
    }

    @Test
    void loginFailsWhenAccountLocked() {
        controller = new AuthController(userRepository, passwordEncoder, tokenProvider, loginAuditService, auditLogService);
        when(loginAuditService.isAccountLocked("bob")).thenReturn(true);

        MockHttpServletRequest request = new MockHttpServletRequest();
        ResponseEntity<?> response =
                controller.authenticateUser(request("bob", "password123456"), request, new MockHttpServletResponse());

        assertEquals(HttpStatus.TOO_MANY_REQUESTS, response.getStatusCode());
    }

    @Test
    void loginUsesForwardedForHeaderWhenPresent() {
        controller = new AuthController(userRepository, passwordEncoder, tokenProvider, loginAuditService, auditLogService);
        when(userRepository.findByUsername("bob")).thenReturn(Optional.of(enabledUser("bob", "encoded")));
        when(passwordEncoder.matches("password123456", "encoded")).thenReturn(false);

        MockHttpServletRequest request = new MockHttpServletRequest();
        request.addHeader("X-Forwarded-For", "203.0.113.7, 10.0.0.1");
        ResponseEntity<?> response =
                controller.authenticateUser(request("bob", "password123456"), request, new MockHttpServletResponse());

        assertEquals(HttpStatus.UNAUTHORIZED, response.getStatusCode());
        verify(loginAuditService).recordFailure("bob", "203.0.113.7");
    }

    @Test
    void loginRejectsDisabledUser() {
        controller = new AuthController(userRepository, passwordEncoder, tokenProvider, loginAuditService, auditLogService);
        when(userRepository.findByUsername("bob"))
                .thenReturn(Optional.of(User.builder().username("bob").password("encoded")
                        .role(Role.ROLE_USER).enabled(false).build()));

        ResponseEntity<?> response = controller.authenticateUser(
                request("bob", "password123456"), new MockHttpServletRequest(), new MockHttpServletResponse());

        assertEquals(HttpStatus.UNAUTHORIZED, response.getStatusCode());
        verify(loginAuditService).recordFailure(eq("bob"), anyString());
    }

    @Test
    void loginRecordsFailureOnBadCredentials() {
        controller = new AuthController(userRepository, passwordEncoder, tokenProvider, loginAuditService, auditLogService);
        when(userRepository.findByUsername("bob")).thenReturn(Optional.of(enabledUser("bob", "encoded")));
        when(passwordEncoder.matches("wrong-password", "encoded")).thenReturn(false);

        ResponseEntity<?> response = controller.authenticateUser(
                request("bob", "wrong-password"), new MockHttpServletRequest(), new MockHttpServletResponse());

        assertEquals(HttpStatus.UNAUTHORIZED, response.getStatusCode());
        assertEquals("Invalid username or password", response.getBody());
        verify(loginAuditService).recordFailure(eq("bob"), anyString());
    }

    @Test
    void logoutClearsCookie() {
        controller = new AuthController(userRepository, passwordEncoder, tokenProvider, loginAuditService, auditLogService);
        MockHttpServletResponse servletResponse = new MockHttpServletResponse();

        ResponseEntity<?> response = controller.logout(servletResponse);

        assertEquals(HttpStatus.OK, response.getStatusCode());
        assertEquals("Logged out successfully", response.getBody());
        assertEquals(0, servletResponse.getCookie("jwt_token").getMaxAge());
        assertNull(servletResponse.getCookie("jwt_token").getValue());
    }
}
