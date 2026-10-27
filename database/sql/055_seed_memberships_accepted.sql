-- =============================================================================
-- 055: seeded scope memberships are accepted, not pending invitations (#486)
-- =============================================================================
-- 004 inserted the demo memberships with invitation_status 'accepted' but accepted_at NULL,
-- and RLS and the API treat accepted_at IS NULL as a pending invitation that grants nothing.
-- 004 now sets accepted_at; this backfills existing databases. Only rows already marked
-- accepted (the API never writes that status without accepted_at) of the seeded demo users.
-- Idempotent; records itself in schema_migrations.
-- =============================================================================

UPDATE scope_memberships m
SET accepted_at = m.invited_at
FROM users u
WHERE u.id = m.user_id
  AND m.accepted_at IS NULL
  AND m.invitation_status = 'accepted'
  AND u.email IN (
      'admin@genecurator.org',
      'alice.smith@genecurator.org',
      'bob.jones@genecurator.org',
      'carol.williams@genecurator.org'
  );

INSERT INTO schema_migrations (filename)
VALUES ('055_seed_memberships_accepted.sql')
ON CONFLICT DO NOTHING;
