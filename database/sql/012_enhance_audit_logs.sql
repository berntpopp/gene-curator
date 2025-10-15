-- Migration 012: Enhance audit_logs with detailed tracking
-- ClinGen SOP v11 - ALCOA+ compliance (Attributable, Legible, Contemporaneous, Original, Accurate)
-- Date: 2025-10-14

BEGIN;

-- Add new columns for enhanced tracking
ALTER TABLE audit_log
ADD COLUMN change_type VARCHAR(50),           -- 'evidence_added', 'score_updated', 'status_changed'
ADD COLUMN old_values JSONB,                  -- Previous state snapshot
ADD COLUMN new_values JSONB,                  -- New state snapshot
ADD COLUMN change_metadata JSONB,             -- User agent, IP, client info
ADD COLUMN alcoa_metadata JSONB;              -- ALCOA+ compliance fields

/*
ALCOA+ Metadata Structure:
{
  "attributable": {
    "user_id": "uuid",
    "user_name": "Jane Doe",
    "user_role": "curator",
    "timestamp": "2025-10-14T12:00:00Z"
  },
  "contemporaneous": true,
  "original": true,
  "accurate": {
    "validation_passed": true,
    "validation_errors": []
  },
  "complete": true,
  "consistent": true,
  "enduring": {
    "stored_location": "primary_db",
    "backup_verified": true
  },
  "available": {
    "access_granted": ["curator", "reviewer", "admin"],
    "retention_until": "2035-10-14"
  }
}
*/

-- Backfill existing rows with legacy marker
UPDATE audit_log
SET change_type = 'legacy_action',
    change_metadata = jsonb_build_object(
        'migrated', true,
        'original_operation', operation
    )
WHERE change_type IS NULL;

-- Make change_type NOT NULL after backfill
ALTER TABLE audit_log
ALTER COLUMN change_type SET NOT NULL;

-- Create indexes for new columns
CREATE INDEX idx_audit_logs_change_type ON audit_log(change_type);
CREATE INDEX idx_audit_logs_entity ON audit_log(entity_type, entity_id);
CREATE INDEX idx_audit_logs_user_action ON audit_log(user_id, change_type, timestamp DESC);

-- GIN indexes for JSONB searches
CREATE INDEX idx_audit_logs_old_values ON audit_log USING gin(old_values);
CREATE INDEX idx_audit_logs_new_values ON audit_log USING gin(new_values);

COMMENT ON COLUMN audit_log.change_type IS 'Detailed change type: evidence_added, score_updated, status_changed, etc.';
COMMENT ON COLUMN audit_log.old_values IS 'Previous state snapshot before change';
COMMENT ON COLUMN audit_log.new_values IS 'New state snapshot after change';
COMMENT ON COLUMN audit_log.change_metadata IS 'Additional context: user agent, IP address, client information';
COMMENT ON COLUMN audit_log.alcoa_metadata IS 'ALCOA+ compliance metadata for regulatory requirements';

COMMIT;
