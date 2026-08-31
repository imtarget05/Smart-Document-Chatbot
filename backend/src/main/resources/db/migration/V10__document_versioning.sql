-- V10: Document versioning (production requirement #4).
-- Legal texts are amended frequently: every replacement upload archives the
-- previous state as an immutable snapshot in document_versions and bumps
-- documents.version_number, so "điều luật nào đang hiệu lực" is answerable
-- from metadata alone.
ALTER TABLE documents ADD COLUMN IF NOT EXISTS version_number INT NOT NULL DEFAULT 1;

CREATE TABLE IF NOT EXISTS document_versions (
    id BIGSERIAL PRIMARY KEY,
    document_id BIGINT NOT NULL,
    version_number INT NOT NULL,
    file_name VARCHAR(255) NOT NULL,
    file_path VARCHAR(500) NOT NULL,
    file_type VARCHAR(20) NOT NULL,
    file_size BIGINT,
    content_hash VARCHAR(64) NOT NULL,
    chunk_count INT,
    change_summary TEXT,
    changed_by VARCHAR(50) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_document_versions_document
    ON document_versions(document_id, version_number DESC);