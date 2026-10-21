-- Seed 014 named the scoring engine "clingen"; the registered engine is "clingen_sop_v11".
-- Idempotent: rows already fixed no longer match.
UPDATE curation_schemas
SET scoring_configuration = jsonb_set(scoring_configuration, '{engine}', '"clingen_sop_v11"')
WHERE scoring_configuration->>'engine' = 'clingen';

-- Fresh databases run this file via initdb, which does not record it; register it so
-- `make db-migrate` does not treat it as pending.
INSERT INTO schema_migrations (filename)
VALUES ('032_fix_scoring_engine_names.sql')
ON CONFLICT DO NOTHING;
