-- V6: Agent state persistence (supply chain agent stateful workflows)
-- Track agent state giữa các request cho multi-step supply chain processes.

CREATE TABLE IF NOT EXISTS agent_state (
    id BIGSERIAL PRIMARY KEY,
    session_id VARCHAR(100) NOT NULL,
    owner_username VARCHAR(255) NOT NULL,
    trace_id VARCHAR(100),
    current_step VARCHAR(50),
    tool_choice VARCHAR(50),
    tool_result TEXT,
    final_answer TEXT,
    status VARCHAR(20) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_agent_state_session
    ON agent_state(session_id);

CREATE INDEX IF NOT EXISTS idx_agent_state_owner
    ON agent_state(owner_username);
