package com.smartdocchat.dto;

import com.smartdocchat.entity.Role;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class UserDto {
    private Long id;
    private String username;
    private String password;
    private Role role;
    private Boolean enabled;
    private LocalDateTime createdAt;
    private LocalDateTime lastLoginAt;
}