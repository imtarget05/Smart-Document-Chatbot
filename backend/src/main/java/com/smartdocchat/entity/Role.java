package com.smartdocchat.entity;

/**
 * Role enumeration for RBAC system.
 */
public enum Role {
    ROLE_USER,      // Viewer: read-only access to docs and chat
    ROLE_ENGINEER,  // Engineer: can upload, delete, access agent features
    ROLE_ADMIN      // Admin: full access including user management and audit logs
}