-- V9: Immutable audit trail (production requirement #2).
-- Insert-only table: rows are written by AuditLogService on security-relevant
-- events (document read/upload/delete, login). No UPDATE/DELETE ever issued by
-- application code. Retention/export handled externally (ops).
CREATE TABLE IF NOT EXISTS audit_logs (
    id BIGSERIAL PRIMARY KEY,
    username VARCHAR(50) NOT NULL,
    action VARCHAR(60) NOT NULL,
    resource_type VARCHAR(40),
    resource_id VARCHAR(64),
    ip_address VARCHAR(45),
    detail TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_audit_logs_username_created_at
    ON audit_logs(username, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_logs_action_created_at
    ON audit_logs(action, created_at DESC);