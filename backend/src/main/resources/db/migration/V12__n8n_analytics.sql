-- Tables for n8n workflow automation analytics

CREATE TABLE IF NOT EXISTS document_analytics (
    document_id BIGINT PRIMARY KEY REFERENCES documents(id) ON DELETE CASCADE,
    chunk_count INT,
    processed_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS escalation_queue (
    id BIGSERIAL PRIMARY KEY,
    session_id VARCHAR(100) NOT NULL,
    question TEXT NOT NULL,
    confidence VARCHAR(20),
    status VARCHAR(50) NOT NULL DEFAULT 'pending_review',
    assigned_to VARCHAR(100),
    resolved_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS document_summaries (
    id BIGSERIAL PRIMARY KEY,
    document_id BIGINT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    summary TEXT NOT NULL,
    generated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_escalation_status ON escalation_queue(status);
CREATE INDEX idx_escalation_created ON escalation_queue(created_at);
CREATE INDEX idx_summaries_doc ON document_summaries(document_id);
