package com.smartdocchat.repository;

import com.smartdocchat.entity.ChatMessage;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface ChatMessageRepository extends JpaRepository<ChatMessage, Long> {
    List<ChatMessage> findBySessionIdOrderByCreatedAtAsc(String sessionId);
    List<ChatMessage> findBySessionIdAndDocumentIdOrderByCreatedAtAsc(String sessionId, Long documentId);
}
