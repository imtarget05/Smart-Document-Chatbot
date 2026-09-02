package com.smartdocchat.service;

import com.smartdocchat.entity.Role;
import org.springframework.security.access.AccessDeniedException;
import org.springframework.stereotype.Service;

/**
 * Document RBAC (production requirement #3): role-based access on top of the
 * existing owner isolation.
 *
 * Rules:
 *  - ROLE_ADMIN   : full access to every document (read, upload, delete, list all).
 *  - ROLE_ENGINEER: may upload and manage documents; reads only their own.
 *  - ROLE_USER    : may upload, read and chat over their own documents; may not delete.
 *
 * Read denials throw the same "not found" as owner isolation so callers cannot
 * distinguish "missing" from "not yours". Write denials surface as 403.
 */
@Service
public class DocumentAccessService {

    public boolean isAdmin(Role role) {
        return role == Role.ROLE_ADMIN;
    }

    public boolean canRead(Role role, String ownerUsername, String callerUsername) {
        if (role == Role.ROLE_ADMIN) {
            return true;
        }
        return ownerUsername != null && ownerUsername.equals(callerUsername);
    }

    public boolean canUpload(Role role) {
        return role == Role.ROLE_ADMIN || role == Role.ROLE_ENGINEER || role == Role.ROLE_USER;
    }

    public boolean canDelete(Role role, String ownerUsername, String callerUsername) {
        if (role == Role.ROLE_ADMIN) {
            return true;
        }
        // ROLE_USER may never delete, even their own documents — deletion is an
        // engineer/admin action. canUpload now includes ROLE_USER, so we must
        // explicitly exclude it here.
        if (role == Role.ROLE_USER) {
            return false;
        }
        return ownerUsername != null && ownerUsername.equals(callerUsername);
    }

    /** Upload denial → 403 (AccessDeniedException is mapped by GlobalExceptionHandler). */
    public void checkUpload(Role role) {
        if (!canUpload(role)) {
            throw new AccessDeniedException("This role cannot upload documents");
        }
    }

    /** Read denial → same signal as owner isolation (not found). */
    public void checkRead(Role role, String ownerUsername, String callerUsername) {
        if (!canRead(role, ownerUsername, callerUsername)) {
            throw new SecurityException("Document not found with id");
        }
    }

    /** Delete denial: non-owner/non-admin → not-found; viewer of own doc → 403. */
    public void checkDelete(Role role, String ownerUsername, String callerUsername) {
        if (canDelete(role, ownerUsername, callerUsername)) {
            return;
        }
        if (ownerUsername != null && ownerUsername.equals(callerUsername) && role == Role.ROLE_USER) {
            throw new AccessDeniedException("ROLE_USER cannot delete documents");
        }
        throw new SecurityException("Document not found with id");
    }

    /** Replace (new version) requires upload rights; ownership unless admin. */
    public void checkReplace(Role role, String ownerUsername, String callerUsername) {
        if (!canUpload(role)) {
            throw new AccessDeniedException("ROLE_USER cannot replace documents");
        }
        if (!isAdmin(role) && (ownerUsername == null || !ownerUsername.equals(callerUsername))) {
            throw new SecurityException("Document not found with id");
        }
    }
}
