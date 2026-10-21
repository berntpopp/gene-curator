-- The application persists scoring-engine output with each evidence write.
-- The legacy placeholder overwrites those scores and clears the verdict.
DROP TRIGGER IF EXISTS trigger_calculate_schema_scores ON curations;
DROP FUNCTION IF EXISTS calculate_schema_scores();
