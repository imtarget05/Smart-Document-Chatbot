-- V13: Add email column to users table (required by User entity)
ALTER TABLE users ADD COLUMN IF NOT EXISTS email VARCHAR(255);
