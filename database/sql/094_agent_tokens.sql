-- 094: a platform admin issues an agent account's personal access token (#639). Agent accounts
-- have no password sign-in to create their own. These policies add to 056's own-token rules
-- (permissive policies are OR-ed) and cover agent accounts only, so a person's tokens stay
-- theirs alone. SELECT covers the read-back of the inserted row.
DROP POLICY IF EXISTS personal_access_tokens_agent_insert_policy ON personal_access_tokens;
CREATE POLICY personal_access_tokens_agent_insert_policy ON personal_access_tokens
    FOR INSERT WITH CHECK (
        is_application_admin()
        AND EXISTS (SELECT 1 FROM users u WHERE u.id = user_id AND u.is_agent)
    );
DROP POLICY IF EXISTS personal_access_tokens_agent_select_policy ON personal_access_tokens;
CREATE POLICY personal_access_tokens_agent_select_policy ON personal_access_tokens
    FOR SELECT USING (
        is_application_admin()
        AND EXISTS (SELECT 1 FROM users u WHERE u.id = user_id AND u.is_agent)
    );

INSERT INTO schema_migrations (filename)
VALUES ('094_agent_tokens.sql')
ON CONFLICT DO NOTHING;
