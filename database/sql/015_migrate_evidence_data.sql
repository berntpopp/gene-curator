-- Migration 015: Migrate existing evidence from JSONB to evidence_items table
-- ClinGen SOP v11 - Data migration (optional, only if existing curations have evidence)
-- Date: 2025-10-14

BEGIN;

-- This migration is OPTIONAL and should only be run if there are existing curations
-- with evidence_data in JSONB format that need to be migrated to the evidence_items table

-- Check if there are any curations with evidence data
DO $$
DECLARE
    curations_with_evidence INTEGER;
    migrated_count INTEGER := 0;
    evidence_record RECORD;
    evidence_item RECORD;
BEGIN
    -- Count curations with evidence data
    SELECT COUNT(*) INTO curations_with_evidence
    FROM curations
    WHERE evidence_data IS NOT NULL
    AND jsonb_typeof(evidence_data) = 'object'
    AND (
        jsonb_array_length(evidence_data->'genetic_evidence') > 0
        OR jsonb_array_length(evidence_data->'experimental_evidence') > 0
    );

    IF curations_with_evidence = 0 THEN
        RAISE NOTICE 'ℹ️  No curations with evidence data found. Skipping migration.';
        RETURN;
    END IF;

    RAISE NOTICE 'ℹ️  Found % curations with evidence data. Starting migration...', curations_with_evidence;

    -- Migrate genetic evidence
    FOR evidence_record IN
        SELECT
            c.id as curation_id,
            c.created_by,
            jsonb_array_elements(c.evidence_data->'genetic_evidence') as evidence_item
        FROM curations c
        WHERE c.evidence_data IS NOT NULL
        AND jsonb_typeof(c.evidence_data) = 'object'
        AND c.evidence_data ? 'genetic_evidence'
        AND jsonb_array_length(c.evidence_data->'genetic_evidence') > 0
    LOOP
        INSERT INTO evidence_items (
            id,
            curation_id,
            created_by,
            evidence_category,
            evidence_type,
            evidence_data,
            validation_status,
            created_at,
            updated_at
        ) VALUES (
            gen_random_uuid(),
            evidence_record.curation_id,
            evidence_record.created_by,
            COALESCE(evidence_record.evidence_item->>'evidence_category', 'unknown'),
            'genetic',
            evidence_record.evidence_item,
            'migrated',  -- Mark as migrated for tracking
            NOW(),
            NOW()
        );
        migrated_count := migrated_count + 1;
    END LOOP;

    -- Migrate experimental evidence
    FOR evidence_record IN
        SELECT
            c.id as curation_id,
            c.created_by,
            jsonb_array_elements(c.evidence_data->'experimental_evidence') as evidence_item
        FROM curations c
        WHERE c.evidence_data IS NOT NULL
        AND jsonb_typeof(c.evidence_data) = 'object'
        AND c.evidence_data ? 'experimental_evidence'
        AND jsonb_array_length(c.evidence_data->'experimental_evidence') > 0
    LOOP
        INSERT INTO evidence_items (
            id,
            curation_id,
            created_by,
            evidence_category,
            evidence_type,
            evidence_data,
            validation_status,
            created_at,
            updated_at
        ) VALUES (
            gen_random_uuid(),
            evidence_record.curation_id,
            evidence_record.created_by,
            COALESCE(evidence_record.evidence_item->>'evidence_category', 'unknown'),
            'experimental',
            evidence_record.evidence_item,
            'migrated',  -- Mark as migrated for tracking
            NOW(),
            NOW()
        );
        migrated_count := migrated_count + 1;
    END LOOP;

    RAISE NOTICE '✅ Migrated % evidence items to evidence_items table', migrated_count;

    -- Optional: Archive the old evidence_data in curations table
    -- Uncomment the following lines if you want to clear the old data after migration
    -- UPDATE curations
    -- SET evidence_data = jsonb_build_object(
    --     '_migrated', true,
    --     '_migration_date', NOW(),
    --     '_original_count', jsonb_array_length(evidence_data->'genetic_evidence') + jsonb_array_length(evidence_data->'experimental_evidence')
    -- )
    -- WHERE evidence_data IS NOT NULL
    -- AND jsonb_typeof(evidence_data) = 'object';

EXCEPTION
    WHEN OTHERS THEN
        RAISE NOTICE '❌ Migration failed: %', SQLERRM;
        RAISE;
END $$;

COMMIT;
