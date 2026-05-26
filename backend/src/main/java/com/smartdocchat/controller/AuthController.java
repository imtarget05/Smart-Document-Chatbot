package com.smartdocchat.controller;

import com.smartdocchat.dto.AuthRequest;
import com.smartdocchat.dto.AuthResponse;
import com.smartdocchat.entity.User;
import com.smartdocchat.repository.UserRepository;
import com.smartdocchat.util.JwtTokenProvider;
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
                .role("ROLE_USER")
                .build();

        userRepository.save(user);
        
        String token = tokenProvider.generateToken(user.getUsername(), user.getRole());
        return ResponseEntity.ok(AuthResponse.builder()
                .token(token)
                .username(user.getUsername())
                .role(user.getRole())
                .build());
    }

    @PostMapping("/login")
    public ResponseEntity<?> authenticateUser(@Valid @RequestBody AuthRequest authRequest) {
        log.info("Authenticating user: {}", authRequest.getUsername());

        return userRepository.findByUsername(authRequest.getUsername())
                .filter(user -> passwordEncoder.matches(authRequest.getPassword(), user.getPassword()))
                .map(user -> {
                    String token = tokenProvider.generateToken(user.getUsername(), user.getRole());
                    return ResponseEntity.ok(AuthResponse.builder()
                            .token(token)
                            .username(user.getUsername())
                            .role(user.getRole())
                            .build());
                })
                .orElseGet(() -> ResponseEntity
                        .status(HttpStatus.UNAUTHORIZED)
                        .body("Invalid username or password"));
    }
}
