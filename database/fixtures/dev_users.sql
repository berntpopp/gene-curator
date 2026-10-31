-- =============================================================================
-- Development and test logins: NEVER applied in production
-- =============================================================================
-- Loaded after every migration on a fresh dev/test volume (docker-compose.yml mounts this
-- directory, database/sql/999_dev_fixtures.sh runs it; scripts/test-postgres.sh does the same).
-- The production migrate image contains database/sql only, so none of this reaches it.
-- Written against the current schema. All four logins use the password admin123.
-- =============================================================================

-- 004's disabled seed owner becomes the dev platform admin.
UPDATE users
SET hashed_password = '$2b$12$bs7kTc5txFs0.0F3AtguTuzOTQ6fWItSmWPQmWgI7GMyhiscyNZd6',
    name = 'Admin User',
    is_active = true
WHERE email = 'admin@genecurator.org';

-- Standard users; their scope roles come from scope_memberships below.
INSERT INTO users (email, hashed_password, name, role, institution, orcid_id, expertise_areas, is_active)
VALUES
    ('alice.smith@genecurator.org', '$2b$12$bs7kTc5txFs0.0F3AtguTuzOTQ6fWItSmWPQmWgI7GMyhiscyNZd6',
     'Alice Smith', 'user', 'Nephrology Research Institute', '0000-0001-5000-0001',
     ARRAY['Nephrology', 'CAKUT', 'Ciliopathies'], true),
    ('bob.jones@genecurator.org', '$2b$12$bs7kTc5txFs0.0F3AtguTuzOTQ6fWItSmWPQmWgI7GMyhiscyNZd6',
     'Bob Jones', 'user', 'Cardiovascular Genomics Center', '0000-0001-5000-0002',
     ARRAY['Cardiology', 'Arrhythmia', 'Congenital Heart Disease'], true),
    ('carol.williams@genecurator.org', '$2b$12$bs7kTc5txFs0.0F3AtguTuzOTQ6fWItSmWPQmWgI7GMyhiscyNZd6',
     'Carol Williams', 'user', 'Neurology and Epilepsy Lab', '0000-0001-5000-0003',
     ARRAY['Neurology', 'Epilepsy', 'Intellectual Disability'], true)
ON CONFLICT (email) DO NOTHING;

-- Accepted memberships: admin in the five seeded scopes, one scope role per test user.
INSERT INTO scope_memberships (scope_id, user_id, role, is_active, invitation_status, accepted_at)
SELECT s.id, u.id, m.role::scope_role, true, 'accepted', NOW()
FROM (VALUES
    ('admin@genecurator.org', 'kidney-genetics', 'admin'),
    ('admin@genecurator.org', 'cardio-genetics', 'admin'),
    ('admin@genecurator.org', 'neuro-genetics', 'admin'),
    ('admin@genecurator.org', 'oncogenetics', 'admin'),
    ('admin@genecurator.org', 'rare-disease', 'admin'),
    ('alice.smith@genecurator.org', 'kidney-genetics', 'curator'),
    ('bob.jones@genecurator.org', 'cardio-genetics', 'reviewer'),
    ('carol.williams@genecurator.org', 'neuro-genetics', 'viewer')
) AS m(email, scope, role)
JOIN users u ON u.email = m.email
JOIN scopes s ON s.name = m.scope
ON CONFLICT (scope_id, user_id) DO NOTHING;
