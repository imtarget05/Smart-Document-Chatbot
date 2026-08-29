-- V8: Document workflow result (Phase 2 document agentic pipeline).
-- Lưu kết quả classify → extract → map → match PO↔Invoice từ llm-router.
ALTER TABLE documents ADD COLUMN IF NOT EXISTS workflow_result TEXT;
