package com.smartdocchat.controller;

import com.smartdocchat.dto.AuthRequest;
import com.smartdocchat.dto.AuthResponse;
import com.smartdocchat.dto.RegisterRequest;
import com.smartdocchat.entity.Role;
import com.smartdocchat.entity.User;
import com.smartdocchat.repository.UserRepository;
import com.smartdocchat.service.AuditLogService;
import com.smartdocchat.service.LoginAuditService;
import com.smartdocchat.util.JwtTokenProvider;
import jakarta.servlet.http.Cookie;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/auth")
@RequiredArgsConstructor
@Slf4j
public class AuthController {

    private final UserRepository userRepository;
    private final PasswordEncoder passwordEncoder;
    private final JwtTokenProvider tokenProvider;
    private final LoginAuditService loginAuditService;
    private final AuditLogService auditLogService;

    private static final String JWT_COOKIE_NAME = "jwt_token";
    private static final int JWT_COOKIE_MAX_AGE_SECONDS = 86400;

    @PostMapping("/register")
    public ResponseEntity<?> registerUser(@Valid @RequestBody RegisterRequest registerRequest) {
        log.info("Registering user: {}", registerRequest.getUsername());

        if (userRepository.existsByUsername(registerRequest.getUsername())) {
            return ResponseEntity
                    .status(HttpStatus.BAD_REQUEST)
                    .body("Username is already taken!");
        }

        User user = User.builder()
                .username(registerRequest.getUsername())
                .password(passwordEncoder.encode(registerRequest.getPassword()))
                .email(registerRequest.getEmail())
                .role(Role.ROLE_USER)
                .enabled(true)
                .build();

        userRepository.save(user);

        String token = tokenProvider.generateToken(user.getUsername(), user.getRole().name());
        return ResponseEntity.ok(AuthResponse.builder()
                .token(token)
                .username(user.getUsername())
                .role(user.getRole().name())
                .build());
    }

    @PostMapping("/login")
    public ResponseEntity<?> authenticateUser(
            @Valid @RequestBody AuthRequest authRequest,
            HttpServletRequest request,
            HttpServletResponse response) {

        String clientIp = getClientIp(request);
        String username = authRequest.getUsername();
        log.info("Authenticating user: {} from ip: {}", username, clientIp);

        if (loginAuditService.isAccountLocked(username)) {
            log.warn("Login attempt for locked account: {}", username);
            return ResponseEntity
                    .status(HttpStatus.TOO_MANY_REQUESTS)
                    .body("Account temporarily locked due to multiple failed login attempts. Please try again later.");
        }

        return userRepository.findByUsername(username)
                .filter(User::getEnabled)
                .filter(user -> passwordEncoder.matches(authRequest.getPassword(), user.getPassword()))
                .<ResponseEntity<?>>map(user -> {
                    loginAuditService.recordSuccess(username, clientIp);
                    auditLogService.record(username, "auth.login", "user", username, clientIp, "success");

                    String token = tokenProvider.generateToken(user.getUsername(), user.getRole().name());

                    Cookie jwtCookie = new Cookie(JWT_COOKIE_NAME, token);
                    jwtCookie.setHttpOnly(true);
                    jwtCookie.setPath("/");
                    jwtCookie.setMaxAge(JWT_COOKIE_MAX_AGE_SECONDS);
                    jwtCookie.setAttribute("SameSite", "Lax");
                    jwtCookie.setSecure("https".equalsIgnoreCase(System.getProperty("server.scheme", "http")));
                    response.addCookie(jwtCookie);

                    return ResponseEntity.ok(AuthResponse.builder()
                            .token(token)
                            .username(user.getUsername())
                            .role(user.getRole().name())
                            .build());
                })
                .orElseGet(() -> {
                    loginAuditService.recordFailure(username, clientIp);
                    auditLogService.record(username, "auth.login.failed", "user", username, clientIp, "invalid credentials");
                    return ResponseEntity
                            .status(HttpStatus.UNAUTHORIZED)
                            .body("Invalid username or password");
                });
    }

    @PostMapping("/logout")
    public ResponseEntity<?> logout(HttpServletResponse response) {
        Cookie jwtCookie = new Cookie(JWT_COOKIE_NAME, null);
        jwtCookie.setHttpOnly(true);
        jwtCookie.setPath("/");
        jwtCookie.setMaxAge(0);
        jwtCookie.setAttribute("SameSite", "Lax");
        jwtCookie.setSecure("https".equalsIgnoreCase(System.getProperty("server.scheme", "http")));
        response.addCookie(jwtCookie);
        return ResponseEntity.ok("Logged out successfully");
    }

    private String getClientIp(HttpServletRequest request) {
        String xfHeader = request.getHeader("X-Forwarded-For");
        if (xfHeader != null && !xfHeader.isBlank()) {
            return xfHeader.split(",")[0].trim();
        }
        return request.getRemoteAddr();
    }
}
