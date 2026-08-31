package com.smartdocchat.service;

import com.smartdocchat.entity.Role;
import org.junit.jupiter.api.Test;
import org.springframework.security.access.AccessDeniedException;

import static org.junit.jupiter.api.Assertions.*;

class DocumentAccessServiceTest {

    private final DocumentAccessService service = new DocumentAccessService();

    // ------------------------------------------------------------------
    // canRead
    // ------------------------------------------------------------------
    @Test
    void adminCanReadAnyDocument() {
        assertTrue(service.canRead(Role.ROLE_ADMIN, "bob", "alice"));
    }

    @Test
    void nonAdminCanOnlyReadOwnDocuments() {
        assertTrue(service.canRead(Role.ROLE_USER, "alice", "alice"));
        assertTrue(service.canRead(Role.ROLE_ENGINEER, "alice", "alice"));
        assertFalse(service.canRead(Role.ROLE_USER, "bob", "alice"));
        assertFalse(service.canRead(Role.ROLE_ENGINEER, "bob", "alice"));
    }

    // ------------------------------------------------------------------
    // canUpload
    // ------------------------------------------------------------------
    @Test
    void onlyAdminAndEngineerCanUpload() {
        assertTrue(service.canUpload(Role.ROLE_ADMIN));
        assertTrue(service.canUpload(Role.ROLE_ENGINEER));
        assertFalse(service.canUpload(Role.ROLE_USER));
    }

    @Test
    void viewerUploadThrows403() {
        AccessDeniedException ex = assertThrows(AccessDeniedException.class,
                () -> service.checkUpload(Role.ROLE_USER));
        assertTrue(ex.getMessage().contains("ROLE_USER"));
        assertDoesNotThrow(() -> service.checkUpload(Role.ROLE_ENGINEER));
        assertDoesNotThrow(() -> service.checkUpload(Role.ROLE_ADMIN));
    }

    // ------------------------------------------------------------------
    // canDelete
    // ------------------------------------------------------------------
    @Test
    void adminDeletesAnythingOwnerDeletesOwn() {
        assertTrue(service.canDelete(Role.ROLE_ADMIN, "bob", "alice"));
        assertTrue(service.canDelete(Role.ROLE_ENGINEER, "alice", "alice"));
        assertFalse(service.canDelete(Role.ROLE_ENGINEER, "bob", "alice"));
    }

    @Test
    void viewerDeletingOwnDocumentIs403() {
        assertThrows(AccessDeniedException.class,
                () -> service.checkDelete(Role.ROLE_USER, "alice", "alice"));
    }

    @Test
    void deletingAnotherUsersDocumentIsNotFound() {
        assertThrows(SecurityException.class,
                () -> service.checkDelete(Role.ROLE_USER, "bob", "alice"));
        assertThrows(SecurityException.class,
                () -> service.checkDelete(Role.ROLE_ENGINEER, "bob", "alice"));
    }

    // ------------------------------------------------------------------
    // isAdmin
    // ------------------------------------------------------------------
    @Test
    void isAdminOnlyTrueForAdminRole() {
        assertTrue(service.isAdmin(Role.ROLE_ADMIN));
        assertFalse(service.isAdmin(Role.ROLE_ENGINEER));
        assertFalse(service.isAdmin(Role.ROLE_USER));
    }
}
