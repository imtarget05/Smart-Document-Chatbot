-- V3: Add chunks column to documents (for RAG retrieval)
ALTER TABLE documents ADD COLUMN IF NOT EXISTS chunks TEXT;