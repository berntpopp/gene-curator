-- Migration: Add use_dynamic_form flag to curation_schemas
-- Purpose: Feature flag for gradual DynamicForm rollout
-- Date: 2026-01-23

-- Add column with default false (safe default)
ALTER TABLE curation_schemas
ADD COLUMN IF NOT EXISTS use_dynamic_form BOOLEAN NOT NULL DEFAULT false;

-- Enable for non-ClinGen schemas immediately (they already use DynamicForm)
UPDATE curation_schemas
SET use_dynamic_form = true
WHERE name NOT ILIKE '%clingen%' AND name NOT ILIKE '%sop%';

-- Optionally enable for one test ClinGen schema for validation
-- UPDATE curation_schemas SET use_dynamic_form = true WHERE name = 'Test ClinGen Schema';

COMMENT ON COLUMN curation_schemas.use_dynamic_form IS
  'When true, use DynamicForm instead of ClinGenCurationForm for this schema';
