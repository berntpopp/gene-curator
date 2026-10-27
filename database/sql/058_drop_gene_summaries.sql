-- =============================================================================
-- 058: drop the gene_summaries cache (#478)
-- =============================================================================
-- Since #468 no reader uses gene_summaries; summaries are computed live per request.
-- Owner decision 2026-10-27: drop the table, its stale trigger and function. CASCADE takes
-- its indexes, policies and any dependent view. Idempotent; records itself.
-- =============================================================================

DROP TRIGGER IF EXISTS trigger_curation_update_mark_stale ON curations;
DROP FUNCTION IF EXISTS mark_gene_summary_stale() CASCADE;
DROP TABLE IF EXISTS gene_summaries CASCADE;

INSERT INTO schema_migrations (filename)
VALUES ('058_drop_gene_summaries.sql')
ON CONFLICT DO NOTHING;
