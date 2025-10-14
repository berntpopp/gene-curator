-- Migration: Rename genes_new table to genes
-- Author: Claude Code
-- Date: 2025-10-14
-- Purpose: Clean up "_new" suffix from gene-related objects after scope-centric refactor

BEGIN;

-- Rename the table
ALTER TABLE genes_new RENAME TO genes;

-- Note: No sequence to rename - table uses uuid_generate_v4() for ID

-- Rename the GIN index on details field
DROP INDEX IF EXISTS idx_genes_new_details_gin;
CREATE INDEX idx_genes_details_gin ON genes USING gin (details);

-- Rename other indexes
ALTER INDEX genes_new_pkey RENAME TO genes_pkey;
ALTER INDEX genes_new_hgnc_id_key RENAME TO genes_hgnc_id_key;
ALTER INDEX genes_new_record_hash_key RENAME TO genes_record_hash_key;
ALTER INDEX idx_genes_new_chromosome RENAME TO idx_genes_chromosome;
ALTER INDEX idx_genes_new_created_by RENAME TO idx_genes_created_by;
ALTER INDEX idx_genes_new_hgnc_id RENAME TO idx_genes_hgnc_id;
ALTER INDEX idx_genes_new_symbol RENAME TO idx_genes_symbol;

-- Rename check constraint
ALTER TABLE genes RENAME CONSTRAINT valid_hgnc_id TO genes_valid_hgnc_id;

-- Rename foreign key constraints
ALTER TABLE genes RENAME CONSTRAINT fk_genes_new_created_by TO fk_genes_created_by;
ALTER TABLE genes RENAME CONSTRAINT fk_genes_new_updated_by TO fk_genes_updated_by;

-- Note: Foreign key constraints are named after the constraint, not the table,
-- so they don't need to be updated. The constraints will automatically reference
-- the renamed table.

-- Verify the changes
DO $$
BEGIN
    -- Check that the table exists with the new name
    IF NOT EXISTS (SELECT 1 FROM information_schema.tables
                   WHERE table_schema = 'public' AND table_name = 'genes') THEN
        RAISE EXCEPTION 'Table genes does not exist after rename';
    END IF;

    -- Check that the old table name is gone
    IF EXISTS (SELECT 1 FROM information_schema.tables
               WHERE table_schema = 'public' AND table_name = 'genes_new') THEN
        RAISE EXCEPTION 'Table genes_new still exists after rename';
    END IF;

    RAISE NOTICE 'Successfully renamed genes_new to genes';
END $$;

COMMIT;
