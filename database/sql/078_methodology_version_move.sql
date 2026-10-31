-- =============================================================================
-- 078: Move curations to a newer methodology version (#591)
-- =============================================================================
-- 042 pinned every precuration and curation to its methodology version for good. The
-- admin "Move to version" (backend/app/services/version_move.py) re-pins rows in one
-- audited transaction, so the pin may now change in one case only: a platform admin
-- moves the row forward to a later version of the same schema. Moving back, to another
-- schema, or without a signed-in admin (migrations, the owner role) is still refused.
-- An active curation whose result would change is never edited: the move inserts an open
-- copy (draft or in review, never approved) of it, which a platform admin may insert
-- only for the curator, entity and workflow pair of an active curation (policy below).
-- Idempotent; records itself.
-- =============================================================================

CREATE OR REPLACE FUNCTION reject_methodology_version_change()
RETURNS TRIGGER AS $$
BEGIN
    IF is_application_admin() AND EXISTS (
        SELECT 1
        FROM methodology_versions o
        JOIN methodology_versions n ON n.schema_id = o.schema_id
        WHERE o.id = OLD.methodology_version_id
          AND n.id = NEW.methodology_version_id
          AND n.version > o.version
    ) THEN
        RETURN NEW;
    END IF;
    RAISE EXCEPTION '%.methodology_version_id is pinned at creation and cannot change', TG_TABLE_NAME
        USING ERRCODE = 'integrity_constraint_violation';
END;
$$ LANGUAGE plpgsql SET search_path = public, pg_temp;

COMMENT ON COLUMN precurations.methodology_version_id IS 'Methodology version pinned at creation; only an admin move to a later version of the same schema changes it (078)';
COMMENT ON COLUMN curations.methodology_version_id IS 'Methodology version pinned at creation; only an admin move to a later version of the same schema changes it (078)';

-- SECURITY DEFINER: a curations policy cannot query curations itself (recursion)
CREATE OR REPLACE FUNCTION has_active_curation(
    gene UUID, scope UUID, entity TEXT, pair UUID, curator UUID
) RETURNS BOOLEAN AS $$
    SELECT EXISTS (
        SELECT 1 FROM curations a
        WHERE a.status = 'active'
          AND a.gene_id = gene AND a.scope_id = scope AND a.entity_key = entity
          AND a.workflow_pair_id = pair
          AND a.created_by IS NOT DISTINCT FROM curator
    )
$$ LANGUAGE SQL STABLE SECURITY DEFINER SET search_path = public, pg_temp;

DROP POLICY IF EXISTS curation_version_move_insert_policy ON curations;
CREATE POLICY curation_version_move_insert_policy ON curations
    FOR INSERT
    WITH CHECK (
        is_application_admin()
        AND curations.status IN ('draft', 'in_review')
        AND curations.approved_at IS NULL AND curations.approved_by IS NULL
        AND has_active_curation(
            curations.gene_id, curations.scope_id, curations.entity_key,
            curations.workflow_pair_id, curations.created_by
        )
    );

COMMENT ON POLICY curation_version_move_insert_policy ON curations IS 'Move to version (#591): a platform admin opens a re-curation copy of an active curation';

INSERT INTO schema_migrations (filename)
VALUES ('078_methodology_version_move.sql')
ON CONFLICT DO NOTHING;
