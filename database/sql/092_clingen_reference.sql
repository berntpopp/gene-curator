-- 092: ClinGen reference on a curation of our own (KGDB 2026-10-31). The GeneFoundry
-- clingen_get_gene_validity record of the same gene-disease-MOI, stored verbatim and shown
-- beside our classification; NULL when ClinGen has not curated the entity. Not an adoption.
ALTER TABLE curations ADD COLUMN IF NOT EXISTS clingen_reference JSONB;

COMMENT ON COLUMN curations.clingen_reference IS
    'ClinGen record cited beside our classification (fields as clingen_adoption); NULL otherwise';

INSERT INTO schema_migrations (filename)
VALUES ('092_clingen_reference.sql')
ON CONFLICT DO NOTHING;
