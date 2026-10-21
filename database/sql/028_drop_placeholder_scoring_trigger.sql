-- The application persists scoring-engine output with each evidence write.
-- The legacy placeholder overwrites those scores and clears the verdict.
DROP TRIGGER IF EXISTS trigger_calculate_schema_scores ON curations;
DROP FUNCTION IF EXISTS calculate_schema_scores();

-- Record this file; schema_migrations only exists from 030 on, so skip it on a fresh build
-- (030 backfills the baseline) and register it when run later via `make db-migrate`.
DO $$
BEGIN
    IF to_regclass('public.schema_migrations') IS NOT NULL THEN
        INSERT INTO schema_migrations (filename) VALUES ('028_drop_placeholder_scoring_trigger.sql')
        ON CONFLICT DO NOTHING;
    END IF;
END
$$;
