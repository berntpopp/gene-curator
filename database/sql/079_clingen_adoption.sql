-- 079: ClinGen adoption marker (#105). The GeneFoundry clingen_get_gene_validity fields of an
-- adopted ClinGen classification, stored verbatim; NULL for a curation of our own.
ALTER TABLE curations ADD COLUMN IF NOT EXISTS clingen_adoption JSONB;

COMMENT ON COLUMN curations.clingen_adoption IS
    'ClinGen record a curation adopted (source, cggv_id, permalink, classification, moi, mondo, '
    'expert_panel, classified_date, retrieved_at, record_sha256, citation, hgnc_id); NULL otherwise';

INSERT INTO schema_migrations (filename)
VALUES ('079_clingen_adoption.sql')
ON CONFLICT DO NOTHING;
