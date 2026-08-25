-- V5: Idempotent document processing (Blueprint #17)
-- Tracks content identity so repeated ingestion of the same document does not
-- create duplicate metadata. Backward-safe: existing rows keep NULL hash and
-- remain fully usable; hashing applies to new uploads only.

ALTER TABLE documents ADD COLUMN IF NOT EXISTS content_hash VARCHAR(64);

CREATE INDEX IF NOT EXISTS idx_documents_owner_content_hash
    ON documents(owner_username, content_hash);