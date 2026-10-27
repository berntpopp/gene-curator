-- =============================================================================
-- 057: LLM configuration: providers, encrypted keys, models, versioned prompts,
--      scope opt-in with caps, run log (#489, slice b: database and admin API)
-- =============================================================================
-- Keys are write-only: app_user cannot SELECT llm_credentials.ciphertext at all (column
-- privileges); the server path that decrypts for a call reads it through
-- llm_credential_ciphertext(). Published prompt versions are immutable for every role
-- (trigger, like 042 methodology_versions); an edit creates a new draft.
-- Caps are NOT NULL and default to 0, so a scope without explicit caps can run nothing.
-- Idempotent; records itself in schema_migrations.
-- =============================================================================

CREATE TABLE IF NOT EXISTS llm_providers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL UNIQUE,
    kind TEXT NOT NULL CHECK (kind IN ('openai_compatible', 'anthropic', 'mock')),
    base_url TEXT NOT NULL,
    enabled BOOLEAN NOT NULL DEFAULT true,
    lock_version INTEGER NOT NULL DEFAULT 1,
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS llm_credentials (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    provider_id UUID NOT NULL UNIQUE REFERENCES llm_providers(id) ON DELETE CASCADE,
    ciphertext BYTEA NOT NULL,
    key_id TEXT NOT NULL,
    fingerprint TEXT NOT NULL,
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    rotated_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS llm_models (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    provider_id UUID NOT NULL REFERENCES llm_providers(id) ON DELETE CASCADE,
    model_id TEXT NOT NULL,
    input_price_per_mtok_cents NUMERIC(12, 4) NOT NULL CHECK (input_price_per_mtok_cents >= 0),
    output_price_per_mtok_cents NUMERIC(12, 4) NOT NULL CHECK (output_price_per_mtok_cents >= 0),
    max_tokens INTEGER NOT NULL CHECK (max_tokens > 0),
    timeout_s INTEGER NOT NULL DEFAULT 60 CHECK (timeout_s BETWEEN 30 AND 60),
    uses_max_completion_tokens BOOLEAN NOT NULL DEFAULT false,
    enabled BOOLEAN NOT NULL DEFAULT true,
    lock_version INTEGER NOT NULL DEFAULT 1,
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_llm_models_provider_model UNIQUE (provider_id, model_id)
);
COMMENT ON COLUMN llm_models.model_id IS 'Dated, pinned provider model id; responses must match it';
COMMENT ON COLUMN llm_models.uses_max_completion_tokens IS 'OpenAI o-series: send max_completion_tokens instead of max_tokens';

CREATE TABLE IF NOT EXISTS prompt_templates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    key TEXT NOT NULL UNIQUE,
    strategy TEXT NOT NULL CHECK (strategy IN ('skeptic', 'advocate')),
    description TEXT,
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS prompt_template_versions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    template_id UUID NOT NULL REFERENCES prompt_templates(id) ON DELETE CASCADE,
    version INTEGER NOT NULL CHECK (version > 0),
    system_text TEXT NOT NULL,
    user_text TEXT NOT NULL,
    output_schema JSONB NOT NULL DEFAULT '{}'::jsonb,
    few_shot_examples JSONB NOT NULL DEFAULT '[]'::jsonb,
    sha256 TEXT,
    published_at TIMESTAMPTZ,
    derived_from UUID REFERENCES prompt_template_versions(id),
    lock_version INTEGER NOT NULL DEFAULT 1,
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_prompt_template_versions_version UNIQUE (template_id, version),
    CONSTRAINT ck_prompt_version_published_hash CHECK (published_at IS NULL OR sha256 IS NOT NULL)
);
COMMENT ON TABLE prompt_template_versions IS 'Drafts are editable; once published_at is set the row is immutable';

CREATE OR REPLACE FUNCTION prompt_version_immutable()
RETURNS TRIGGER AS $$
BEGIN
    IF OLD.published_at IS NULL THEN
        RETURN CASE WHEN TG_OP = 'DELETE' THEN OLD ELSE NEW END;
    END IF;
    -- Deleting the template itself cascades here
    IF TG_OP = 'DELETE' AND NOT EXISTS (SELECT 1 FROM prompt_templates WHERE id = OLD.template_id) THEN
        RETURN OLD;
    END IF;
    RAISE EXCEPTION 'prompt version % is published and immutable', OLD.id
        USING ERRCODE = 'integrity_constraint_violation';
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_prompt_version_immutable ON prompt_template_versions;
CREATE TRIGGER trigger_prompt_version_immutable
    BEFORE UPDATE OR DELETE ON prompt_template_versions
    FOR EACH ROW
    EXECUTE FUNCTION prompt_version_immutable();

CREATE TABLE IF NOT EXISTS scope_llm_settings (
    scope_id UUID PRIMARY KEY REFERENCES scopes(id) ON DELETE CASCADE,
    enabled BOOLEAN NOT NULL DEFAULT false,
    model_id UUID REFERENCES llm_models(id) ON DELETE SET NULL,
    skeptic_prompt_version_id UUID REFERENCES prompt_template_versions(id),
    advocate_prompt_version_id UUID REFERENCES prompt_template_versions(id),
    monthly_token_cap BIGINT NOT NULL DEFAULT 0 CHECK (monthly_token_cap >= 0),
    monthly_cost_cap_cents INTEGER NOT NULL DEFAULT 0 CHECK (monthly_cost_cap_cents >= 0),
    daily_run_cap INTEGER NOT NULL DEFAULT 0 CHECK (daily_run_cap >= 0),
    lock_version INTEGER NOT NULL DEFAULT 1,
    updated_by UUID REFERENCES users(id),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS llm_runs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    curation_id UUID REFERENCES curations(id) ON DELETE SET NULL,
    scope_id UUID NOT NULL REFERENCES scopes(id) ON DELETE CASCADE,
    strategy TEXT NOT NULL CHECK (strategy IN ('skeptic', 'advocate')),
    llm_model_id UUID REFERENCES llm_models(id) ON DELETE SET NULL,
    model_id TEXT NOT NULL,
    prompt_version_id UUID REFERENCES prompt_template_versions(id),
    prompt_sha256 TEXT,
    methodology_version_id UUID,  -- no FK: the 042 downgrade test drops methodology_versions
    status TEXT NOT NULL DEFAULT 'queued'
        CHECK (status IN ('queued', 'running', 'succeeded', 'failed')),
    input_tokens INTEGER NOT NULL DEFAULT 0,
    output_tokens INTEGER NOT NULL DEFAULT 0,
    cost_cents NUMERIC(12, 4) NOT NULL DEFAULT 0,
    duration_ms INTEGER,
    error_code TEXT,
    request_sha256 TEXT,
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finished_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_llm_runs_scope_created ON llm_runs (scope_id, created_at DESC);

-- Keys are write-only for the API role: every column but the ciphertext is readable.
REVOKE SELECT ON llm_credentials FROM app_user;
GRANT SELECT (id, provider_id, key_id, fingerprint, created_by, created_at, rotated_at)
    ON llm_credentials TO app_user;

-- The one read path for a ciphertext: the server call that decrypts it with the env key ring.
CREATE OR REPLACE FUNCTION llm_credential_ciphertext(p_provider_id UUID)
RETURNS BYTEA AS $$
    SELECT ciphertext FROM llm_credentials WHERE provider_id = p_provider_id
$$ LANGUAGE SQL STABLE SECURITY DEFINER SET search_path = public;
REVOKE ALL ON FUNCTION llm_credential_ciphertext(UUID) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION llm_credential_ciphertext(UUID) TO app_user;

-- RLS. Configuration is read by every signed-in user (scope admins pick from it) and
-- written by platform admins only; credentials, settings and runs are narrower.
DO $$
DECLARE
    t TEXT;
BEGIN
    FOREACH t IN ARRAY ARRAY['llm_providers', 'llm_models', 'prompt_templates', 'prompt_template_versions'] LOOP
        EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY', t);
        EXECUTE format('ALTER TABLE %I FORCE ROW LEVEL SECURITY', t);
        EXECUTE format('DROP POLICY IF EXISTS %I ON %I', t || '_select_policy', t);
        EXECUTE format('CREATE POLICY %I ON %I FOR SELECT USING (get_current_user_uuid() IS NOT NULL)', t || '_select_policy', t);
        EXECUTE format('DROP POLICY IF EXISTS %I ON %I', t || '_insert_policy', t);
        EXECUTE format('CREATE POLICY %I ON %I FOR INSERT WITH CHECK (is_application_admin())', t || '_insert_policy', t);
        EXECUTE format('DROP POLICY IF EXISTS %I ON %I', t || '_update_policy', t);
        EXECUTE format('CREATE POLICY %I ON %I FOR UPDATE USING (is_application_admin()) WITH CHECK (is_application_admin())', t || '_update_policy', t);
        EXECUTE format('DROP POLICY IF EXISTS %I ON %I', t || '_delete_policy', t);
        EXECUTE format('CREATE POLICY %I ON %I FOR DELETE USING (is_application_admin())', t || '_delete_policy', t);
    END LOOP;
END $$;

ALTER TABLE llm_credentials ENABLE ROW LEVEL SECURITY;
ALTER TABLE llm_credentials FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS llm_credentials_select_policy ON llm_credentials;
CREATE POLICY llm_credentials_select_policy ON llm_credentials
    FOR SELECT USING (is_application_admin());
DROP POLICY IF EXISTS llm_credentials_insert_policy ON llm_credentials;
CREATE POLICY llm_credentials_insert_policy ON llm_credentials
    FOR INSERT WITH CHECK (is_application_admin());
DROP POLICY IF EXISTS llm_credentials_update_policy ON llm_credentials;
CREATE POLICY llm_credentials_update_policy ON llm_credentials
    FOR UPDATE USING (is_application_admin()) WITH CHECK (is_application_admin());
-- Changing a provider's base URL deletes its key (it must not follow to a new host).
DROP POLICY IF EXISTS llm_credentials_delete_policy ON llm_credentials;
CREATE POLICY llm_credentials_delete_policy ON llm_credentials
    FOR DELETE USING (is_application_admin());

ALTER TABLE scope_llm_settings ENABLE ROW LEVEL SECURITY;
ALTER TABLE scope_llm_settings FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS scope_llm_settings_select_policy ON scope_llm_settings;
CREATE POLICY scope_llm_settings_select_policy ON scope_llm_settings
    FOR SELECT USING (is_application_admin() OR is_scope_admin(scope_id));
DROP POLICY IF EXISTS scope_llm_settings_insert_policy ON scope_llm_settings;
CREATE POLICY scope_llm_settings_insert_policy ON scope_llm_settings
    FOR INSERT WITH CHECK (is_application_admin() OR is_scope_admin(scope_id));
DROP POLICY IF EXISTS scope_llm_settings_update_policy ON scope_llm_settings;
CREATE POLICY scope_llm_settings_update_policy ON scope_llm_settings
    FOR UPDATE USING (is_application_admin() OR is_scope_admin(scope_id))
    WITH CHECK (is_application_admin() OR is_scope_admin(scope_id));

-- ponytail: read-only until the run worker slice adds its INSERT/UPDATE path.
ALTER TABLE llm_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE llm_runs FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS llm_runs_select_policy ON llm_runs;
CREATE POLICY llm_runs_select_policy ON llm_runs
    FOR SELECT USING (is_application_admin() OR is_scope_admin(scope_id));

INSERT INTO schema_migrations (filename)
VALUES ('057_llm_configuration.sql')
ON CONFLICT DO NOTHING;
