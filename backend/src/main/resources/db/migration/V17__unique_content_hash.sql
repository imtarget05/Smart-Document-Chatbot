-- V17: Enforce per-owner content-hash idempotency at the database level.
--
-- V5 added a non-unique lookup index (idx_documents_owner_content_hash) plus
-- an application-level check-then-insert dedup in DocumentService.uploadDocument.
-- Under two concurrent uploads of identical content both application checks can
-- pass (TOCTOU race), creating duplicate document metadata. This migration
-- closes that race with a partial unique index.
--
-- Step 1 — non-destructive cleanup: if duplicate rows already exist (possible
-- from historical races), clear the hash on every row except the oldest so the
-- unique index can be created without failing on legacy data. No rows are
-- deleted; losing rows keep all their data but opt out of the constraint.
UPDATE documents d
SET content_hash = NULL
WHERE d.content_hash IS NOT NULL
  AND d.id > (
      SELECT MIN(d2.id) FROM documents d2
      WHERE d2.owner_username = d.owner_username
        AND d2.content_hash = d.content_hash
  );

-- Step 2 — the race-closing constraint (partial: NULL hashes are exempt).
CREATE UNIQUE INDEX IF NOT EXISTS uq_documents_owner_content_hash
    ON documents(owner_username, content_hash)
WHERE content_hash IS NOT NULL;
