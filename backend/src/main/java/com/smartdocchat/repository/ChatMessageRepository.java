package com.smartdocchat.repository;

import com.smartdocchat.entity.ChatMessage;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface ChatMessageRepository extends JpaRepository<ChatMessage, Long> {
    List<ChatMessage> findBySessionIdOrderByCreatedAtAsc(String sessionId);
    List<ChatMessage> findBySessionIdAndDocumentIdOrderByCreatedAtAsc(String sessionId, Long documentId);
    List<ChatMessage> findByOwnerUsernameAndSessionIdOrderByCreatedAtAsc(String ownerUsername, String sessionId);
    List<ChatMessage> findByOwnerUsernameAndSessionIdAndDocumentIdOrderByCreatedAtAsc(
            String ownerUsername, String sessionId, Long documentId);

    @org.springframework.data.jpa.repository.Query(value = 
        "SELECT DISTINCT ON (session_id) session_id, user_message, created_at " +
        "FROM chat_messages WHERE owner_username = :ownerUsername " +
        "ORDER BY session_id, created_at DESC", nativeQuery = true)
    List<Object[]> findUniqueSessionsByOwner(String ownerUsername);
}
