-- Migration 008: Add lock_version for optimistic locking
-- ClinGen SOP v11 - Prevents concurrent modification conflicts
-- Date: 2025-10-14

BEGIN;

-- Add lock_version column to curations table
ALTER TABLE curations
ADD COLUMN lock_version INTEGER NOT NULL DEFAULT 0;

-- Create index for lock version checks
CREATE INDEX idx_curations_lock_version ON curations(id, lock_version);

-- Create trigger function to increment lock_version on update
CREATE OR REPLACE FUNCTION increment_lock_version()
RETURNS TRIGGER AS $$
BEGIN
    NEW.lock_version = OLD.lock_version + 1;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger
CREATE TRIGGER trigger_increment_lock_version
    BEFORE UPDATE ON curations
    FOR EACH ROW
    EXECUTE FUNCTION increment_lock_version();

COMMENT ON COLUMN curations.lock_version IS 'Optimistic locking version number (auto-incremented on update)';
COMMENT ON FUNCTION increment_lock_version() IS 'Auto-increment lock_version on curation updates to detect concurrent modifications';

COMMIT;
