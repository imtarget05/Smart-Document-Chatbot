-- V4: Legal document model (Decision 13)
-- Adds legal metadata to documents and an addressable evidence-unit table.
-- Backward-safe: no data dropped, existing chunks column untouched. Existing
-- documents keep their legacy JSON-string chunks and remain fully usable;
-- LegalChunk rows are created only for newly ingested structured documents.

ALTER TABLE documents ADD COLUMN IF NOT EXISTS title VARCHAR(500);
ALTER TABLE documents ADD COLUMN IF NOT EXISTS document_number VARCHAR(100);
ALTER TABLE documents ADD COLUMN IF NOT EXISTS issuing_body VARCHAR(255);
ALTER TABLE documents ADD COLUMN IF NOT EXISTS issue_date DATE;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS effective_date DATE;
-- Existing rows are classified as user uploads; never auto-promoted to OFFICIAL.
ALTER TABLE documents ADD COLUMN IF NOT EXISTS source_type VARCHAR(20) NOT NULL DEFAULT 'USER';

CREATE TABLE IF NOT EXISTS legal_chunks (
    id BIGSERIAL PRIMARY KEY,
    document_id BIGINT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    ordinal INTEGER NOT NULL,
    content TEXT NOT NULL,
    chapter_number VARCHAR(50),
    article_number VARCHAR(50),
    clause_number VARCHAR(50),
    point_label VARCHAR(50),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_legal_chunks_document_id ON legal_chunks(document_id);
CREATE INDEX IF NOT EXISTS idx_legal_chunks_doc_article ON legal_chunks(document_id, article_number);
CREATE INDEX IF NOT EXISTS idx_documents_document_number ON documents(document_number);
CREATE INDEX IF NOT EXISTS idx_documents_source_type ON documents(source_type);