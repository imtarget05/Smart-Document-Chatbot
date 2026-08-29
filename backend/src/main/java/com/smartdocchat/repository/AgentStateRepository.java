package com.smartdocchat.repository;

import com.smartdocchat.entity.AgentState;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface AgentStateRepository extends JpaRepository<AgentState, Long> {

    Optional<AgentState> findBySessionId(String sessionId);

    List<AgentState> findByOwnerUsernameOrderByCreatedAtDesc(String ownerUsername);

    List<AgentState> findByOwnerUsernameAndStatus(String ownerUsername, String status);

    void deleteBySessionId(String sessionId);
}
