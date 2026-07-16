package com.smartdocchat.controller;

import com.smartdocchat.dto.UserDto;
import com.smartdocchat.entity.Role;
import com.smartdocchat.entity.User;
import com.smartdocchat.repository.UserRepository;
import com.smartdocchat.service.AuditService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.web.PageableDefault;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Optional;

@RestController
@RequestMapping("/admin")
@RequiredArgsConstructor
@Slf4j
@PreAuthorize("hasRole('ADMIN')")
public class AdminController {

    private final UserRepository userRepository;
    private final PasswordEncoder passwordEncoder;
    private final AuditService auditService;

    @GetMapping("/users")
    public ResponseEntity<Page<UserDto>> getAllUsers(
            @PageableDefault(size = 20) Pageable pageable) {
        Page<User> users = userRepository.findAll(pageable);
        return ResponseEntity.ok(users.map(this::toDto));
    }

    @GetMapping("/users/{id}")
    public ResponseEntity<UserDto> getUserById(@PathVariable Long id) {
        return userRepository.findById(id)
                .map(user -> ResponseEntity.ok(toDto(user)))
                .orElse(ResponseEntity.notFound().build());
    }

    @PostMapping("/users")
    public ResponseEntity<UserDto> createUser(@Valid @RequestBody UserDto userDto) {
        if (userRepository.existsByUsername(userDto.getUsername())) {
            return ResponseEntity.badRequest().build();
        }

        User user = User.builder()
                .username(userDto.getUsername())
                .password(passwordEncoder.encode(userDto.getPassword()))
                .role(userDto.getRole() != null ? userDto.getRole() : Role.ROLE_USER)
                .enabled(userDto.getEnabled() != null ? userDto.getEnabled() : true)
                .build();

        User saved = userRepository.save(user);
        auditService.logSuccess("AdminController.createUser", "User", saved.getId().toString(),
                "Created user: " + saved.getUsername());
        return ResponseEntity.ok(toDto(saved));
    }

    @PutMapping("/users/{id}")
    public ResponseEntity<UserDto> updateUser(@PathVariable Long id, @Valid @RequestBody UserDto userDto) {
        return userRepository.findById(id)
                .map(user -> {
                    user.setUsername(userDto.getUsername());
                    if (userDto.getPassword() != null && !userDto.getPassword().isEmpty()) {
                        user.setPassword(passwordEncoder.encode(userDto.getPassword()));
                    }
                    if (userDto.getRole() != null) {
                        user.setRole(userDto.getRole());
                    }
                    if (userDto.getEnabled() != null) {
                        user.setEnabled(userDto.getEnabled());
                    }
                    User saved = userRepository.save(user);
                    auditService.logSuccess("AdminController.updateUser", "User", saved.getId().toString(),
                            "Updated user: " + saved.getUsername());
                    return ResponseEntity.ok(toDto(saved));
                })
                .orElse(ResponseEntity.notFound().build());
    }

    @DeleteMapping("/users/{id}")
    public ResponseEntity<Void> deleteUser(@PathVariable Long id) {
        return userRepository.findById(id)
                .map(user -> {
                    userRepository.delete(user);
                    auditService.logSuccess("AdminController.deleteUser", "User", id.toString(),
                            "Deleted user: " + user.getUsername());
                    return ResponseEntity.noContent().<Void>build();
                })
                .orElse(ResponseEntity.notFound().build());
    }

    @GetMapping("/roles")
    public ResponseEntity<List<String>> getAllRoles() {
        return ResponseEntity.ok(List.of("ROLE_USER", "ROLE_ENGINEER", "ROLE_ADMIN"));
    }

    private UserDto toDto(User user) {
        return UserDto.builder()
                .id(user.getId())
                .username(user.getUsername())
                .role(user.getRole())
                .enabled(user.getEnabled())
                .createdAt(user.getCreatedAt())
                .lastLoginAt(user.getLastLoginAt())
                .build();
    }
}