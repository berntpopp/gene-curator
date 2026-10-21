-- =============================================================================
-- 039: publications cache table (POST /publications/validate returned 500)
-- =============================================================================
-- The Publication model had no migration, so a fresh database lacked the table.
-- Reference data (PubMed/Europe PMC metadata cache). The async publication endpoints
-- already require an authenticated user and open a session without an RLS user context,
-- so the policies cannot test the caller; they allow the runtime role to read, cache and
-- refresh rows and deny deletes (no policy). Idempotent; records itself in schema_migrations.
-- =============================================================================

CREATE TABLE IF NOT EXISTS publications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    pmid VARCHAR(20) NOT NULL UNIQUE,
    title TEXT NOT NULL,
    authors TEXT[] NOT NULL DEFAULT '{}',
    author_string TEXT,
    journal VARCHAR(500) NOT NULL,
    journal_abbrev VARCHAR(100),
    volume VARCHAR(50),
    issue VARCHAR(50),
    pages VARCHAR(50),
    pub_year INTEGER,
    pub_date VARCHAR(50),
    doi VARCHAR(200),
    pmcid VARCHAR(20),
    abstract TEXT,
    pub_type VARCHAR(100),
    is_open_access BOOLEAN NOT NULL DEFAULT FALSE,
    cited_by_count INTEGER,
    api_response JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_fetched_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    added_by UUID REFERENCES users(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS ix_publications_pmid ON publications (pmid);
CREATE INDEX IF NOT EXISTS ix_publications_pub_year ON publications (pub_year);
CREATE INDEX IF NOT EXISTS ix_publications_doi ON publications (doi);
CREATE INDEX IF NOT EXISTS ix_publications_pmcid ON publications (pmcid);
CREATE INDEX IF NOT EXISTS idx_publications_year ON publications (pub_year);
CREATE INDEX IF NOT EXISTS idx_publications_journal ON publications (journal);
CREATE INDEX IF NOT EXISTS idx_publications_search ON publications (pmid, doi, title);

ALTER TABLE publications ENABLE ROW LEVEL SECURITY;
ALTER TABLE publications FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS publications_select_policy ON publications;
CREATE POLICY publications_select_policy ON publications FOR SELECT USING (true);
DROP POLICY IF EXISTS publications_insert_policy ON publications;
CREATE POLICY publications_insert_policy ON publications FOR INSERT WITH CHECK (true);
DROP POLICY IF EXISTS publications_update_policy ON publications;
CREATE POLICY publications_update_policy ON publications FOR UPDATE USING (true) WITH CHECK (true);

-- app_user gets table rights from the default privileges of 031; make that explicit
-- for databases created before it.
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_user') THEN
        GRANT SELECT, INSERT, UPDATE ON publications TO app_user;
    END IF;
END $$;

INSERT INTO schema_migrations (filename)
VALUES ('039_publications_table.sql')
ON CONFLICT DO NOTHING;
