package com.smartdocchat.entity;

import jakarta.persistence.*;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;
import java.time.LocalDateTime;

/**
 * Agent state persistence — lưu trạng thái agent antara request cho stateful
 * multi-step supply chain workflows (PO receipt → approval → fulfillment → shipment).
 *
 * Mảnh ghép cho #5 trong supply-chain-sprint-plan.md.
 */
@Entity
@Table(name = "agent_state", indexes = {
        @Index(name = "idx_agent_state_session", columnList = "session_id"),
        @Index(name = "idx_agent_state_owner", columnList = "owner_username")
})
@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class AgentState {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "session_id", nullable = false, length = 100)
    private String sessionId;

    @Column(name = "owner_username", nullable = false)
    private String ownerUsername;

    @Column(name = "trace_id", length = 100)
    private String traceId;

    @Column(name = "current_step", length = 50)
    private String currentStep;

    @Column(name = "tool_choice", length = 50)
    private String toolChoice;

    @Column(name = "tool_result", columnDefinition = "TEXT")
    private String toolResult;

    @Column(name = "final_answer", columnDefinition = "TEXT")
    private String finalAnswer;

    @Column(name = "status", length = 20)
    private String status;

    @Column(name = "created_at", nullable = false, updatable = false)
    private LocalDateTime createdAt;

    @Column(name = "updated_at", nullable = false)
    private LocalDateTime updatedAt;

    @PrePersist
    public void prePersist() {
        LocalDateTime now = LocalDateTime.now();
        createdAt = now;
        updatedAt = now;
        if (status == null) {
            status = "active";
        }
    }

    @PreUpdate
    public void preUpdate() {
        updatedAt = LocalDateTime.now();
    }
}
