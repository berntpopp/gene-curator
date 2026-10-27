-- =============================================================================
-- 053: publications.added_by cannot be reassigned (#386)
-- =============================================================================
-- publications_update_policy (039) is permissive (a shared metadata cache any caller may
-- refresh), so any caller could rewrite added_by. A policy cannot compare OLD with NEW; a
-- trigger keeps the adder fixed for everyone. The cache stays refreshable, and
-- deleting the adder still nulls it through the FK (ON DELETE SET NULL).
-- Idempotent; records itself in schema_migrations.
-- =============================================================================

-- Definer: reads users past RLS to recognise the FK's SET NULL after the adder was deleted.
CREATE OR REPLACE FUNCTION guard_publication_added_by()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.added_by IS DISTINCT FROM OLD.added_by
       AND NOT (NEW.added_by IS NULL
                AND NOT EXISTS (SELECT 1 FROM users WHERE id = OLD.added_by)) THEN
        RAISE EXCEPTION 'publications.added_by is immutable' USING ERRCODE = '42501';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, pg_temp;

DROP TRIGGER IF EXISTS trigger_guard_publication_added_by ON publications;
CREATE TRIGGER trigger_guard_publication_added_by
    BEFORE UPDATE ON publications
    FOR EACH ROW EXECUTE FUNCTION guard_publication_added_by();

INSERT INTO schema_migrations (filename)
VALUES ('053_publications_added_by_immutable.sql')
ON CONFLICT DO NOTHING;
