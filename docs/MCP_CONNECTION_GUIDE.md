# Connecting an MCP client to Gene Curator

Gene Curator runs an MCP server at `<API base URL>/mcp` (local development:
`http://localhost:8051/mcp`). An MCP client acts as you: every tool is an existing API endpoint
and runs with your identity, your scope roles and the same checks as the web app (row-level
security, four-eyes review, optimistic locking). It can do exactly what you can do, nothing more.

## 1. Create a token

1. Sign in, open the user menu and choose **Access tokens**.
2. Enter a name for the client (for example "Claude Code on my laptop"), pick an expiry (at most
   365 days) and tick **Read-only** if the client should never write.
3. Click **Create token** and copy the token (`gc_pat_...`). It is shown only once; Gene Curator
   stores only a hash.

The dialog also shows a ready-to-paste Claude Code command. The token name appears in the audit
trail as the client of every write it makes.

## 2. Connect a client

### Claude Code

```bash
claude mcp add --transport http gene-curator http://localhost:8051/mcp \
  --header "Authorization: Bearer gc_pat_..."
```

Check the connection with `claude mcp list`.

### Claude Desktop

Claude Desktop connects through [`mcp-remote`](https://www.npmjs.com/package/mcp-remote), which
passes the token as a header. Add this to `claude_desktop_config.json` and restart Claude Desktop:

```json
{
  "mcpServers": {
    "gene-curator": {
      "command": "npx",
      "args": [
        "mcp-remote",
        "http://localhost:8051/mcp",
        "--header",
        "Authorization:Bearer ${GENE_CURATOR_TOKEN}"
      ],
      "env": { "GENE_CURATOR_TOKEN": "gc_pat_..." }
    }
  }
}
```

### Other clients

Any MCP client that speaks Streamable HTTP and can send an `Authorization: Bearer` header works.
The server is stateless and answers with JSON.

## 3. Revoke a token

Open **Access tokens** and click **Revoke** next to the token. Clients using it stop working at
once. Expired and revoked tokens stay listed for reference. A lost or leaked token should be
revoked immediately.

## What the server exposes

- Server instructions that clients load on connect: the workflow (Entry -> Precuration ->
  Curation -> Review -> Active) with the tool for each step, what each scope role may do, and the
  4-eyes rule.
- One tool per API operation, named `verb_noun` after the endpoint (`list_scopes`,
  `get_curation`, `approve_precuration`, ...).
- Tools that only read are marked `readOnlyHint`; deletes, approvals, rejections, submissions,
  workflow transitions, merges, methodology publishing and updates (PUT/PATCH, except draft saves
  and marking notifications read) are marked `destructiveHint` and their
  description asks the client to confirm with you first.
- Not exposed: login, refresh, logout, registration and the REST auth index, and account control that a token may
  never perform (user management, password changes, creating tokens).
- Errors carry a closed code (`invalid_input`, `unauthorized`, `forbidden`, `not_found`, `conflict`,
  `rate_limited`, `upstream_unavailable`, `internal`) plus the HTTP status and the API's message.
  `conflict` means a stale write (reload and retry) or an inactive scope.
- Rate limits are per user, shared by all of a user's tokens and sessions.
- Every write is recorded in the audit log with `channel: mcp` and the token name as client.

## Not yet supported

OAuth 2.1 sign-in and dynamic client registration (remote connectors without a token) are planned
for phase 2. Until then, use a personal access token as above.
