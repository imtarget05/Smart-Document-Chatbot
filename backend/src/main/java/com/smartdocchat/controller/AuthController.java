package com.smartdocchat.controller;

import com.smartdocchat.dto.AuthRequest;
import com.smartdocchat.dto.AuthResponse;
import com.smartdocchat.entity.Role;
import com.smartdocchat.entity.User;
import com.smartdocchat.repository.UserRepository;
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

    private static final String JWT_COOKIE_NAME = "jwt_token";
    private static final int JWT_COOKIE_MAX_AGE_SECONDS = 86400; // 24h

    @PostMapping("/register")
    public ResponseEntity<?> registerUser(@Valid @RequestBody AuthRequest authRequest) {
        log.info("Registering user: {}", authRequest.getUsername());

        if (userRepository.existsByUsername(authRequest.getUsername())) {
            return ResponseEntity
                    .status(HttpStatus.BAD_REQUEST)
                    .body("Username is already taken!");
        }

        User user = User.builder()
                .username(authRequest.getUsername())
                .password(passwordEncoder.encode(authRequest.getPassword()))
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

        // Check account lockout
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
                    // Success – record audit, clear failures, set httpOnly cookie
                    loginAuditService.recordSuccess(username, clientIp);

                    String token = tokenProvider.generateToken(user.getUsername(), user.getRole().name());

                    // httpOnly + SameSite cookie (Secure only on HTTPS)
                    Cookie jwtCookie = new Cookie(JWT_COOKIE_NAME, token);
                    jwtCookie.setHttpOnly(true);
                    jwtCookie.setPath("/");
                    jwtCookie.setMaxAge(JWT_COOKIE_MAX_AGE_SECONDS);
                    jwtCookie.setAttribute("SameSite", "Lax");
                    jwtCookie.setSecure("https".equalsIgnoreCase(System.getProperty("server.scheme", "http")));
                    response.addCookie(jwtCookie);

                    // Also return token in body for non-browser clients (mobile apps, CLI)
                    return ResponseEntity.ok(AuthResponse.builder()
                            .token(token)
                            .username(user.getUsername())
                            .role(user.getRole().name())
                            .build());
                })
                .orElseGet(() -> {
                    // Failed – record audit
                    loginAuditService.recordFailure(username, clientIp);
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
