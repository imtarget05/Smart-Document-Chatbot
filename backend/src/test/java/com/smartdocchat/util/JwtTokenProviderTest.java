package com.smartdocchat.util;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

class JwtTokenProviderTest {
    private static final String SECRET =
            "VGhpcy1pcy1hLXRlc3Qtand0LXNlY3JldC13aXRoLWF0LWxlYXN0LTMyLWJ5dGVzIQ==";

    @Test
    void tokenRemainsValidAcrossProviderInstancesWithConfiguredSecret() {
        JwtTokenProvider issuer = new JwtTokenProvider(SECRET, 60_000L);
        JwtTokenProvider verifier = new JwtTokenProvider(SECRET, 60_000L);

        String token = issuer.generateToken("alice", "ROLE_USER");

        assertTrue(verifier.validateToken(token));
        assertEquals("alice", verifier.getUsernameFromToken(token));
        assertEquals("ROLE_USER", verifier.getRoleFromToken(token));
    }
}
