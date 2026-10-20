-- Baseline installations upgraded through 027; resolve older missing migrations first.
CREATE TABLE IF NOT EXISTS schema_migrations (
    filename text PRIMARY KEY,
    applied_at timestamptz NOT NULL DEFAULT now()
);

-- On an empty database the runner applies the foundation before reaching this file.
INSERT INTO schema_migrations (filename)
SELECT filename FROM (VALUES
    ('001_schema_foundation.sql'),
    ('002_schema_triggers.sql'),
    ('003_schema_views.sql'),
    ('004_seed_data.sql'),
    ('005_rls_setup.sql'),
    ('006_test_user_setup.sql'),
    ('007_logging_tables.sql'),
    ('008_add_lock_version.sql'),
    ('009_create_evidence_items.sql'),
    ('010_create_gene_summaries.sql'),
    ('011_create_validation_cache.sql'),
    ('012_enhance_audit_logs.sql'),
    ('013_add_performance_indexes.sql'),
    ('014_seed_clingen_schema.sql'),
    ('015_migrate_evidence_data.sql'),
    ('016_seed_precuration_schema.sql'),
    ('017_seed_workflow_pair.sql'),
    ('018_fix_curation_schema_lumping_splitting.sql'),
    ('019_fix_experimental_evidence_schema.sql'),
    ('020_complete_sop11_schema.sql'),
    ('021_fix_precuration_triggers.sql'),
    ('022_fix_scope_cascade_delete.sql'),
    ('023_fix_audit_trigger_scope_delete.sql'),
    ('024_add_invitation_expiry.sql'),
    ('025_remove_assigned_scopes.sql'),
    ('026_create_notifications.sql'),
    ('027_fix_reactivation_and_log_retention.sql'),
    ('030_schema_migrations.sql')
) AS baseline(filename)
WHERE to_regclass('public.scopes') IS NOT NULL
ON CONFLICT (filename) DO NOTHING;
