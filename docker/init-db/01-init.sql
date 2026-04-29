-- ============================================
-- Database Initialization Script
-- Runs only on first PostgreSQL container startup
-- ============================================

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Grant permissions
GRANT ALL PRIVILEGES ON DATABASE smart_doc_chatbot TO postgres;
