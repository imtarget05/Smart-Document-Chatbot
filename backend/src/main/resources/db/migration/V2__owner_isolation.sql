CREATE TABLE IF NOT EXISTS users (
    id BIGSERIAL PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL DEFAULT 'ROLE_USER',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

ALTER TABLE documents ADD COLUMN IF NOT EXISTS status VARCHAR(30) NOT NULL DEFAULT 'READY';
ALTER TABLE documents ADD COLUMN IF NOT EXISTS summary TEXT;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS suggested_questions TEXT;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS concept_map TEXT;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS owner_username VARCHAR(50) NOT NULL DEFAULT 'legacy';
ALTER TABLE chat_messages ADD COLUMN IF NOT EXISTS document_ids TEXT;
ALTER TABLE chat_messages ADD COLUMN IF NOT EXISTS owner_username VARCHAR(50) NOT NULL DEFAULT 'legacy';

CREATE INDEX IF NOT EXISTS idx_documents_owner_created_at ON documents(owner_username, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_chat_messages_owner_session_created_at
    ON chat_messages(owner_username, session_id, created_at ASC);
