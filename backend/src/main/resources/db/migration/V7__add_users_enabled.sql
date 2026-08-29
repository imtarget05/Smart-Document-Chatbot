-- V7: Align users table with User entity (adds `enabled` flag).
-- V1__initial_schema.sql omitted this column, so a fresh database fails
-- Hibernate schema validation with "missing column [enabled] in table [users]".
ALTER TABLE users ADD COLUMN IF NOT EXISTS enabled BOOLEAN NOT NULL DEFAULT TRUE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS last_login_at TIMESTAMP;