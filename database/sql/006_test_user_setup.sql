-- =============================================================================
-- 006: intentionally empty
-- =============================================================================
-- This file used to create the login role test_user/test_password (and granted CONNECT on
-- the hard-coded gene_curator_dev database). Nothing uses it: the test lane connects as
-- app_user, and 031 disables the role on databases that still have it. Kept, empty, so the
-- numbering and the schema_migrations baseline (030) stay unchanged.
SELECT 1;
