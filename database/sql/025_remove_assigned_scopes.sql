-- Migration: Remove assigned_scopes column from users table
-- Date: January 2026

-- Step 1: Migrate any existing data to scope_memberships
INSERT INTO scope_memberships (id, user_id, scope_id, role, is_active, created_at, updated_at)
SELECT
    gen_random_uuid(),
    u.id,
    scope_elem.scope_id,
    'viewer',
    true,
    NOW(),
    NOW()
FROM users u
CROSS JOIN LATERAL unnest(u.assigned_scopes) AS scope_elem(scope_id)
WHERE u.assigned_scopes IS NOT NULL
  AND array_length(u.assigned_scopes, 1) > 0
  AND NOT EXISTS (
    SELECT 1 FROM scope_memberships sm
    WHERE sm.user_id = u.id
    AND sm.scope_id = scope_elem.scope_id
)
ON CONFLICT DO NOTHING;

-- Step 2: Drop the column
ALTER TABLE users DROP COLUMN IF EXISTS assigned_scopes;
