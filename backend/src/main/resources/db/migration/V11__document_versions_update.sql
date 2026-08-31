-- V11: Add missing columns to document_versions for full version tracking.
-- Adds file_type, chunk_count, change_summary, changed_by columns and
-- constraints to match the updated DocumentVersion entity.

ALTER TABLE document_versions
    ADD COLUMN IF NOT EXISTS file_type VARCHAR(50) NOT NULL DEFAULT 'txt',
    ADD COLUMN IF NOT EXISTS chunk_count INT,
    ADD COLUMN IF NOT EXISTS change_summary TEXT,
    ADD COLUMN IF NOT EXISTS changed_by VARCHAR(100) NOT NULL DEFAULT 'system';

-- Add foreign key constraint if not exists (PostgreSQL doesn't support IF NOT EXISTS for constraints)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'fk_document_versions_document'
        AND table_name = 'document_versions'
    ) THEN
        ALTER TABLE document_versions
            ADD CONSTRAINT fk_document_versions_document
            FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE;
    END IF;
END$$;

-- Add unique constraint if not exists
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'uk_document_versions_document_version'
        AND table_name = 'document_versions'
    ) THEN
        ALTER TABLE document_versions
            ADD CONSTRAINT uk_document_versions_document_version
            UNIQUE(document_id, version_number);
    END IF;
END$$;

-- Create indexes if not exists
CREATE INDEX IF NOT EXISTS idx_document_versions_document_id ON document_versions(document_id);
CREATE INDEX IF NOT EXISTS idx_document_versions_created_at ON document_versions(created_at);
