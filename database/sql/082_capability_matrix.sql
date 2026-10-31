-- =============================================================================
-- 082: capability matrix as data, scope-owned configuration, allowed pairs (#284)
-- =============================================================================
-- role_capabilities is the role -> capability matrix (seeded from the #284 table; the same
-- rows as app.core.capabilities.DEFAULT_MATRIX). The API's require() and the RLS helper
-- functions below both read it, so one table decides who may do what in a scope.
-- owner_scope_id on curation_schemas, methodology_versions and workflow_pairs: NULL is a
-- global template (platform admins only), otherwise that scope's admins manage it.
-- scope_workflow_pairs lists the pairs a scope may use besides its default pair.
-- Platform admins keep no RLS bypass for review (D1). Idempotent; records itself.
-- =============================================================================

CREATE TABLE IF NOT EXISTS role_capabilities (
    role scope_role NOT NULL,
    capability TEXT NOT NULL,
    PRIMARY KEY (role, capability)
);

INSERT INTO role_capabilities (role, capability) VALUES
    ('viewer', 'scope.view'),
    ('reviewer', 'scope.view'),
    ('reviewer', 'curation.review'),
    ('curator', 'scope.view'),
    ('curator', 'curation.edit'),
    ('curator', 'gene.create'),
    ('admin', 'scope.view'),
    ('admin', 'curation.edit'),
    ('admin', 'curation.review'),
    ('admin', 'gene.create'),
    ('admin', 'gene.assign'),
    ('admin', 'scope.manage'),
    ('admin', 'scope.members.manage'),
    ('admin', 'methodology.derive'),
    ('admin', 'methodology.edit'),
    ('admin', 'methodology.publish'),
    ('admin', 'workflow.create'),
    ('admin', 'workflow.assign_to_scope')
ON CONFLICT DO NOTHING;

ALTER TABLE curation_schemas
    ADD COLUMN IF NOT EXISTS owner_scope_id UUID REFERENCES scopes(id) ON DELETE SET NULL;
ALTER TABLE workflow_pairs
    ADD COLUMN IF NOT EXISTS owner_scope_id UUID REFERENCES scopes(id) ON DELETE SET NULL;
-- No foreign key: versions are immutable (042), so ON DELETE SET NULL could never run
ALTER TABLE methodology_versions ADD COLUMN IF NOT EXISTS owner_scope_id UUID;
CREATE INDEX IF NOT EXISTS idx_curation_schemas_owner_scope ON curation_schemas (owner_scope_id);
CREATE INDEX IF NOT EXISTS idx_workflow_pairs_owner_scope ON workflow_pairs (owner_scope_id);

CREATE TABLE IF NOT EXISTS scope_workflow_pairs (
    scope_id UUID NOT NULL REFERENCES scopes(id) ON DELETE CASCADE,
    workflow_pair_id UUID NOT NULL REFERENCES workflow_pairs(id) ON DELETE CASCADE,
    PRIMARY KEY (scope_id, workflow_pair_id)
);

-- A version belongs to its schema's scope (set here, so no API path can forget it)
CREATE OR REPLACE FUNCTION methodology_version_owner()
RETURNS TRIGGER AS $$
BEGIN
    NEW.owner_scope_id := (SELECT owner_scope_id FROM curation_schemas WHERE id = NEW.schema_id);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, pg_temp;

DROP TRIGGER IF EXISTS trigger_methodology_version_owner ON methodology_versions;
CREATE TRIGGER trigger_methodology_version_owner
    BEFORE INSERT ON methodology_versions
    FOR EACH ROW EXECUTE FUNCTION methodology_version_owner();

-- -----------------------------------------------------------------------------
-- Capability helpers: the matrix decides; the old role helpers now read it
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION user_has_scope_capability(scope_uuid UUID, user_uuid UUID, cap TEXT)
RETURNS BOOLEAN AS $$
    SELECT EXISTS (
        SELECT 1 FROM scope_memberships m
        JOIN role_capabilities rc ON rc.role = m.role
        WHERE m.scope_id = scope_uuid
          AND m.user_id = user_uuid
          AND m.is_active
          AND m.accepted_at IS NOT NULL
          AND rc.capability = cap
    )
$$ LANGUAGE SQL STABLE SECURITY DEFINER SET search_path = public, pg_temp;

-- Each wrapper has its own EXISTS: one SECURITY DEFINER call per row, not a chain
CREATE OR REPLACE FUNCTION has_scope_capability(scope_uuid UUID, cap TEXT)
RETURNS BOOLEAN AS $$
    SELECT EXISTS (
        SELECT 1 FROM scope_memberships m
        JOIN role_capabilities rc ON rc.role = m.role
        WHERE m.scope_id = scope_uuid
          AND m.user_id = get_current_user_uuid()
          AND m.is_active
          AND m.accepted_at IS NOT NULL
          AND rc.capability = cap
    )
$$ LANGUAGE SQL STABLE SECURITY DEFINER SET search_path = public, pg_temp;

-- Global configuration (owner NULL): platform admins; scope-owned: that scope's capability
CREATE OR REPLACE FUNCTION can_manage_config(owner_uuid UUID, cap TEXT)
RETURNS BOOLEAN AS $$
    SELECT is_application_admin()
        OR (owner_uuid IS NOT NULL AND EXISTS (
            SELECT 1 FROM scope_memberships m
            JOIN role_capabilities rc ON rc.role = m.role
            WHERE m.scope_id = owner_uuid
              AND m.user_id = get_current_user_uuid()
              AND m.is_active
              AND m.accepted_at IS NOT NULL
              AND rc.capability = cap
        ))
$$ LANGUAGE SQL STABLE SECURITY DEFINER SET search_path = public, pg_temp;

CREATE OR REPLACE FUNCTION is_scope_admin(scope_uuid UUID)
RETURNS BOOLEAN AS $$
    SELECT EXISTS (
        SELECT 1 FROM scope_memberships m
        JOIN role_capabilities rc ON rc.role = m.role
        WHERE m.scope_id = scope_uuid
          AND m.user_id = get_current_user_uuid()
          AND m.is_active
          AND m.accepted_at IS NOT NULL
          AND rc.capability = 'scope.members.manage'
    )
$$ LANGUAGE SQL STABLE SECURITY DEFINER SET search_path = public, pg_temp;

CREATE OR REPLACE FUNCTION can_curate_in_scope(scope_uuid UUID)
RETURNS BOOLEAN AS $$
    SELECT EXISTS (
        SELECT 1 FROM scope_memberships m
        JOIN role_capabilities rc ON rc.role = m.role
        WHERE m.scope_id = scope_uuid
          AND m.user_id = get_current_user_uuid()
          AND m.is_active
          AND m.accepted_at IS NOT NULL
          AND rc.capability = 'curation.edit'
    )
$$ LANGUAGE SQL STABLE SECURITY DEFINER SET search_path = public, pg_temp;

CREATE OR REPLACE FUNCTION can_review_in_scope(scope_uuid UUID)
RETURNS BOOLEAN AS $$
    SELECT EXISTS (
        SELECT 1 FROM scope_memberships m
        JOIN role_capabilities rc ON rc.role = m.role
        WHERE m.scope_id = scope_uuid
          AND m.user_id = get_current_user_uuid()
          AND m.is_active
          AND m.accepted_at IS NOT NULL
          AND rc.capability = 'curation.review'
    )
$$ LANGUAGE SQL STABLE SECURITY DEFINER SET search_path = public, pg_temp;

CREATE OR REPLACE FUNCTION is_scope_reviewer(scope_uuid UUID, reviewer_uuid UUID)
RETURNS BOOLEAN AS $$
    SELECT EXISTS (
        SELECT 1 FROM scope_memberships m
        JOIN role_capabilities rc ON rc.role = m.role
        WHERE m.scope_id = scope_uuid
          AND m.user_id = reviewer_uuid
          AND m.is_active
          AND m.accepted_at IS NOT NULL
          AND rc.capability = 'curation.review'
    )
$$ LANGUAGE SQL STABLE SECURITY DEFINER SET search_path = public, pg_temp;

CREATE OR REPLACE FUNCTION is_earlier_reviewer(curation_uuid UUID, reviewer_uuid UUID)
RETURNS BOOLEAN AS $$
    SELECT EXISTS (
        SELECT 1 FROM reviews WHERE curation_id = curation_uuid AND reviewer_id = reviewer_uuid
    ) AND EXISTS (
        SELECT 1 FROM curations c
        JOIN scope_memberships m ON m.scope_id = c.scope_id
        JOIN role_capabilities rc ON rc.role = m.role
        WHERE c.id = curation_uuid
          AND m.user_id = reviewer_uuid
          AND m.is_active
          AND m.accepted_at IS NOT NULL
          AND rc.capability = 'curation.review'
    )
$$ LANGUAGE SQL STABLE SECURITY DEFINER SET search_path = public, pg_temp;

-- -----------------------------------------------------------------------------
-- RLS: everyone reads configuration (as before); writes follow the matrix
-- -----------------------------------------------------------------------------
ALTER TABLE role_capabilities ENABLE ROW LEVEL SECURITY;
ALTER TABLE role_capabilities FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS role_capabilities_select_policy ON role_capabilities;
CREATE POLICY role_capabilities_select_policy ON role_capabilities FOR SELECT USING (true);
DROP POLICY IF EXISTS role_capabilities_write_policy ON role_capabilities;
CREATE POLICY role_capabilities_write_policy ON role_capabilities
    FOR ALL USING (is_application_admin()) WITH CHECK (is_application_admin());

ALTER TABLE curation_schemas ENABLE ROW LEVEL SECURITY;
ALTER TABLE curation_schemas FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS curation_schemas_select_policy ON curation_schemas;
CREATE POLICY curation_schemas_select_policy ON curation_schemas FOR SELECT USING (true);
DROP POLICY IF EXISTS curation_schemas_insert_policy ON curation_schemas;
CREATE POLICY curation_schemas_insert_policy ON curation_schemas
    FOR INSERT WITH CHECK (can_manage_config(owner_scope_id, 'methodology.derive'));
DROP POLICY IF EXISTS curation_schemas_update_policy ON curation_schemas;
CREATE POLICY curation_schemas_update_policy ON curation_schemas
    FOR UPDATE USING (can_manage_config(owner_scope_id, 'methodology.edit'))
    WITH CHECK (can_manage_config(owner_scope_id, 'methodology.edit'));
DROP POLICY IF EXISTS curation_schemas_delete_policy ON curation_schemas;
CREATE POLICY curation_schemas_delete_policy ON curation_schemas
    FOR DELETE USING (can_manage_config(owner_scope_id, 'methodology.edit'));

DROP POLICY IF EXISTS methodology_versions_insert_policy ON methodology_versions;
CREATE POLICY methodology_versions_insert_policy ON methodology_versions
    FOR INSERT WITH CHECK (can_manage_config(owner_scope_id, 'methodology.publish'));

ALTER TABLE workflow_pairs ENABLE ROW LEVEL SECURITY;
ALTER TABLE workflow_pairs FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS workflow_pairs_select_policy ON workflow_pairs;
CREATE POLICY workflow_pairs_select_policy ON workflow_pairs FOR SELECT USING (true);
DROP POLICY IF EXISTS workflow_pairs_write_policy ON workflow_pairs;
CREATE POLICY workflow_pairs_write_policy ON workflow_pairs
    FOR ALL USING (can_manage_config(owner_scope_id, 'workflow.create'))
    WITH CHECK (can_manage_config(owner_scope_id, 'workflow.create'));

ALTER TABLE scope_workflow_pairs ENABLE ROW LEVEL SECURITY;
ALTER TABLE scope_workflow_pairs FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS scope_workflow_pairs_select_policy ON scope_workflow_pairs;
CREATE POLICY scope_workflow_pairs_select_policy ON scope_workflow_pairs FOR SELECT USING (true);
DROP POLICY IF EXISTS scope_workflow_pairs_write_policy ON scope_workflow_pairs;
CREATE POLICY scope_workflow_pairs_write_policy ON scope_workflow_pairs
    FOR ALL USING (can_manage_config(scope_id, 'workflow.assign_to_scope'))
    WITH CHECK (can_manage_config(scope_id, 'workflow.assign_to_scope'));

INSERT INTO schema_migrations (filename)
VALUES ('082_capability_matrix.sql')
ON CONFLICT DO NOTHING;
