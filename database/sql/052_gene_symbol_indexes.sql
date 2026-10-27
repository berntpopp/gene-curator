-- =============================================================================
-- 052: indexed gene identifier lookup (#379)
-- =============================================================================
-- The gene resolver matched pasted identifiers by scanning every gene. It now filters in SQL on
-- upper(approved_symbol), upper(hgnc_id) and the upper-cased previous/alias symbol arrays; each
-- branch has an index so the OR becomes a bitmap OR of index scans.
-- Idempotent; records itself in schema_migrations.
-- =============================================================================

CREATE OR REPLACE FUNCTION upper_text_array(arr TEXT[])
RETURNS TEXT[] AS $$
    SELECT ARRAY(SELECT upper(x) FROM unnest(arr) AS x)
$$ LANGUAGE SQL IMMUTABLE PARALLEL SAFE SET search_path = pg_catalog, pg_temp;

COMMENT ON FUNCTION upper_text_array(TEXT[]) IS 'Upper-cases every element (indexable gene symbol lookup)';

CREATE INDEX IF NOT EXISTS idx_genes_upper_symbol ON genes (upper(approved_symbol));
CREATE INDEX IF NOT EXISTS idx_genes_upper_hgnc_id ON genes (upper(hgnc_id));
CREATE INDEX IF NOT EXISTS idx_genes_upper_previous_symbols
    ON genes USING GIN (upper_text_array(previous_symbols));
CREATE INDEX IF NOT EXISTS idx_genes_upper_alias_symbols
    ON genes USING GIN (upper_text_array(alias_symbols));

INSERT INTO schema_migrations (filename)
VALUES ('052_gene_symbol_indexes.sql')
ON CONFLICT DO NOTHING;
