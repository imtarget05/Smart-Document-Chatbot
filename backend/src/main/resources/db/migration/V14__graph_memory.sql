-- V14: Graph memory tables for cross-session entity/relationship storage
-- Enables GraphRAG-style retrieval using PostgreSQL recursive CTEs

-- Entities: people, organizations, documents, concepts extracted from conversations
CREATE TABLE IF NOT EXISTS entities (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        VARCHAR(512) NOT NULL,
    type        VARCHAR(32)  NOT NULL DEFAULT 'CONCEPT',  -- PERSON, ORG, DOCUMENT, CONCEPT
    metadata    JSONB        NOT NULL DEFAULT '{}'::jsonb,
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

-- Relationships between entities (directed graph edges)
CREATE TABLE IF NOT EXISTS relationships (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_entity_id UUID NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
    target_entity_id UUID NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
    relationship_type VARCHAR(128) NOT NULL,
    weight      FLOAT        NOT NULL DEFAULT 1.0,
    metadata    JSONB        NOT NULL DEFAULT '{}'::jsonb,
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

-- Entity mentions: tracks when/where an entity was mentioned in conversations
CREATE TABLE IF NOT EXISTS entity_mentions (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entity_id   UUID NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
    session_id  VARCHAR(64)  NOT NULL,
    turn_id     INTEGER      NOT NULL DEFAULT 0,
    context_text TEXT        NOT NULL,
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

-- Indexes for efficient graph traversal
CREATE INDEX IF NOT EXISTS idx_entities_name ON entities (name);
CREATE INDEX IF NOT EXISTS idx_entities_name_lower ON entities (LOWER(name));
CREATE INDEX IF NOT EXISTS idx_entities_type ON entities (type);
CREATE INDEX IF NOT EXISTS idx_relationships_source ON relationships (source_entity_id);
CREATE INDEX IF NOT EXISTS idx_relationships_target ON relationships (target_entity_id);
CREATE INDEX IF NOT EXISTS idx_relationships_type ON relationships (relationship_type);
CREATE INDEX IF NOT EXISTS idx_entity_mentions_entity ON entity_mentions (entity_id);
CREATE INDEX IF NOT EXISTS idx_entity_mentions_session ON entity_mentions (session_id);

-- Unique constraint: one entity per (name, type) pair
CREATE UNIQUE INDEX IF NOT EXISTS idx_entities_name_type ON entities (LOWER(name), type);
