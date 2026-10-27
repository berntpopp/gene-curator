# Connecting an MCP client to Gene Curator

Gene Curator runs two MCP endpoints with the same token, checks, audit and rate limits:

- `<API base URL>/mcp` (local development: `http://localhost:8051/mcp`): the curation core, about
  70 tools for curating a gene end to end and checking or reviewing a curation, plus lookups
  (genes, scopes, members, ontology, publications, your work). Start here.
- `<API base URL>/mcp/full`: every API operation (schema and workflow-pair authoring,
  statistics, logs, LLM and platform administration).

An MCP client acts as you: every tool is an existing API endpoint
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

Check the connection with `claude mcp list`. For administration tools, add a second server
with the same token at `http://localhost:8051/mcp/full`.

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
- On `/mcp/full` one tool per API operation, named `verb_noun` after the endpoint (`list_scopes`,
  `get_curation`, `approve_precuration`, ...); `/mcp` lists the curation subset of the same tools.
- The tool list depends on who asks: tools only platform admins can use (user, log, LLM and
  schema administration) are listed for platform admins only. Anyone else calling one gets the
  API's own `forbidden`.
- Tools that only read are marked `readOnlyHint`; deletes, approvals, rejections, submissions,
  workflow transitions, merges, methodology publishing and updates (PUT/PATCH, except draft saves
  and marking notifications read) are marked `destructiveHint`; the server instructions ask the
  client to confirm these with you first.
- Each result is sent once, as compact JSON text (no `structuredContent` or `outputSchema`), so
  clients do not pay for it twice. Null fields are left out (empty objects and lists stay).
  On `/mcp` results are leaner still: no internal hashes or autosave stamps, MONDO and HPO
  searches return ids and labels, `validate_pmids` returns title, journal and year
  (`get_publication` has the abstract), `list_members` drops invitation details, and
  `get_curation_schema` is compact unless you pass `compact=false`. REST responses are unchanged.
- On `/mcp`, a list or search result over about 8,000 tokens is not sent; the error
  `response_too_large` says how to narrow it (paging, filters, `compact=true`). Single items such
  as a curation are always returned whole, and `/mcp/full` never caps.
- Not exposed: login, refresh, logout, registration and the REST auth index, and account control that a token may
  never perform (user management, password changes, creating tokens).
- Errors carry a closed code (`invalid_input`, `unauthorized`, `forbidden`, `not_found`, `conflict`,
  `rate_limited`, `upstream_unavailable`, `internal`, `response_too_large`) plus the HTTP status and the API's message.
  `conflict` means a stale write (reload and retry) or an inactive scope.
- Rate limits are per user, shared by all of a user's tokens and sessions.
- Every write is recorded in the audit log with `channel: mcp` and the token name as client.

## Not yet supported

OAuth 2.1 sign-in and dynamic client registration (remote connectors without a token) are planned
for phase 2. Until then, use a personal access token as above.
