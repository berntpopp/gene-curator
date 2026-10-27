# Gene Curator

<p align="center">
  <a href="https://github.com/berntpopp/gene-curator/actions/workflows/ci.yml"><img src="https://github.com/berntpopp/gene-curator/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="backend/pyproject.toml"><img src="https://img.shields.io/badge/python-3.12-3776ab?logo=python&logoColor=white" alt="Python 3.12"></a>
  <a href="backend/pyproject.toml"><img src="https://img.shields.io/badge/FastAPI-0.139-009688?logo=fastapi&logoColor=white" alt="FastAPI"></a>
  <a href="frontend/package.json"><img src="https://img.shields.io/badge/typescript-6.0-3178c6?logo=typescript&logoColor=white" alt="TypeScript"></a>
  <a href="frontend/package.json"><img src="https://img.shields.io/badge/vue-3.5-4fc08d?logo=vuedotjs&logoColor=white" alt="Vue 3.5"></a>
  <a href="database/sql"><img src="https://img.shields.io/badge/PostgreSQL-15-4169e1?logo=postgresql&logoColor=white" alt="PostgreSQL 15"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue" alt="MIT license"></a>
</p>

**Gene Curator** is a methodology-agnostic platform for curating gene-disease associations.
Teams capture evidence in structured, schema-driven forms, get scores computed automatically, and
move every assertion through an independent peer review before it becomes the team's active call.
ClinGen SOP v11 and GenCC ship built in; your own method is a schema away.

> **Research use only.** Gene Curator supports systematic curation for research; it is not a
> clinical diagnostic tool. Classifications and scores require independent expert review before any
> clinical use (see the in-app disclaimer). Never commit patient data or real credentials.

## What it does

- **Any methodology:** field definitions, validation rules, scoring and form layout live in
  versioned curation schemas in the database. ClinGen SOP v11, GenCC and a qualitative method are
  included; new scoring engines plug into a registry.
- **Scope-based teams:** curation happens inside scopes (for example kidney genetics or
  cardiology) with per-scope roles: admin, curator, reviewer, viewer. Invitations are GitHub-style
  and grant nothing until accepted.
- **Multi-stage workflow:** Entry → Precuration (disease entity, lumping/splitting) → Curation →
  Review → Active. Review follows the 4-eyes principle, backward transitions are allowed, and there
  is one active curation per gene and scope.
- **Evidence capture with live checks:** genes, HPO terms and PubMed IDs are validated against
  HGNC, HPO and PubMed while you type. Scores update as evidence changes.
- **Traceable records:** audit log, content hashes on records, optimistic locking against
  concurrent edits, and PostgreSQL row-level security for tenant isolation.

## Quick start

Requires Docker, GNU Make, [uv](https://docs.astral.sh/uv/) and Node.js 24 (`.nvmrc`).

```bash
git clone https://github.com/berntpopp/gene-curator.git
cd gene-curator
make install      # backend + frontend dependencies and git hooks
make hybrid-up    # PostgreSQL in Docker
make backend      # terminal 1: API on http://localhost:8051/docs
make frontend     # terminal 2: UI on http://localhost:5193
```

Create `frontend/.env.local` with `VITE_API_BASE_URL=http://localhost:8051` and
`VITE_ENABLE_DEV_LOGIN=true`, then sign in as `admin@genecurator.org` / `admin123` (seeded
development data only). Prefer everything in containers? `make dev` (UI on port 3051).

The API connects to PostgreSQL as `app_user` (no superuser, so row-level security applies);
`POSTGRES_USER` only runs migrations. Set `APP_DB_PASSWORD` and use the same password in
`DATABASE_URL`/`DATABASE_URL_DOCKER`; production needs distinct strong passwords for both roles.
An existing database gets the role with `make db-migrate` before the backend restarts.

### Upgrading to v0.8.0

Run `make db-migrate` (050–055) before restarting the backend. Users outside a scope now see only
active curations of active public scopes, and get 404 for drafts and other non-active work; scope
members are unaffected. Saving a GenCC or qualitative curation now scores it with its schema's
engine, so its stored verdict can change on the next save; `make recompute-scores` stays
ClinGen-only. Writes in an inactive scope return 409. Production builds no longer contain the seeded dev logins. Details and known limits:
[docs/releases/v0.8.0.md](docs/releases/v0.8.0.md).
([#474](https://github.com/berntpopp/gene-curator/pull/474),
[#472](https://github.com/berntpopp/gene-curator/pull/472),
[#467](https://github.com/berntpopp/gene-curator/pull/467),
[#488](https://github.com/berntpopp/gene-curator/pull/488))

### Upgrading to v0.7.0

Run `make db-migrate` (048–049) before restarting the backend. Migration 048 corrects the
catalogue view's genetic/experimental score expressions. Migration 049 publishes an immutable ClinGen successor for
eligible unchanged stock schemas; it preserves existing versions, record pins, evidence and
stored scores. New records use the latest published version; existing records keep their pin.
No historical rescore or re-pinning is part of this upgrade.
([#440](https://github.com/berntpopp/gene-curator/pull/440),
[#450](https://github.com/berntpopp/gene-curator/pull/450))

The successor uses variant-specific AR starting suggestions and requires explicit segregation
points. Review the [release notes](docs/releases/v0.7.0.md) for clinical limits, the stricter
required-content checks, MONDO suggestion filtering and known unresolved defects. Deployments
older than v0.6.0 must first follow the earlier-release upgrade steps below.
([#450](https://github.com/berntpopp/gene-curator/pull/450),
[#445](https://github.com/berntpopp/gene-curator/pull/445),
[#451](https://github.com/berntpopp/gene-curator/pull/451))

### Upgrading to v0.6.0

Run `make db-migrate` (migrations 042-047) before restarting the backend, then recompute stored
scores once: `make recompute-scores`. It logs every curation whose total or class changes (SOP v11
corrections: Models and Rescue cap 4, case-control summed cap 12, AR other-variant proband up to 3,
and the contradictory-evidence rule). Contradictory rows with no Impact no longer dispute a
curation: re-label any that really dispute. Custom point models are untouched, and published
methodology versions are immutable. Details: [docs/releases/v0.6.0.md](docs/releases/v0.6.0.md).

### Upgrading to v0.5.0

Run `make db-migrate` (migrations 036-041) before restarting the backend. Curation and precuration
updates now require `lock_version`. Details: [docs/releases/v0.5.0.md](docs/releases/v0.5.0.md).

### Upgrading to v0.4.0

1. Set `APP_DB_PASSWORD` (required; the runtime connects as the non-superuser `app_user`).
2. Run `make db-migrate` to apply all pending migrations (028-035) once, before restarting the backend.
3. Run `make recompute-scores` once to rescore curations under ClinGen SOP v11.
4. Redis is gone; remove any Redis service or `REDIS_*` settings from your deployment.

## Development and verification

Checks run locally first; GitHub Actions runs the same `make` targets and only confirms.

| Command | Purpose |
| --- | --- |
| `make check` | Fast gate (pre-push hook): lint, types, file-size limit, unit tests |
| `make ci` | Everything CI runs, including coverage gates, the PostgreSQL lane and the production build |
| `make format` | Auto-fix formatting and lint findings |
| `make test` / `make test-frontend` | Backend (pytest) / frontend (Vitest) tests |
| `make test-postgres` | Builds a fresh database from `database/sql` and runs the RLS tests on it |
| `make test-e2e` | Playwright end-to-end tests against a running stack |
| `make api-types` | Regenerate frontend API types from the backend OpenAPI schema |
| `make audit` | Known-vulnerability scan of both lockfiles |
| `make db-shell` / `make db-reset` | psql into the dev database / rebuild it from scratch |
| `make help` | All targets |

Quality bar: source files at most 650 lines, at least 90% coverage on changed lines with ratcheting
global floors, strict mypy and vue-tsc, and no `print` or `console.*` outside the logging layer.
Details are in [AGENTS.md](AGENTS.md).

## Architecture

| Layer | Path | Responsibility |
| --- | --- | --- |
| API | `backend/app/api/v1/endpoints/` | FastAPI routers, auth and scope-role dependencies |
| Domain | `backend/app/crud/`, `backend/app/services/` | Data access, workflow engine, permissions, external validators |
| Scoring | `backend/app/scoring/` | ClinGen, GenCC and qualitative engines behind a registry |
| Database | `database/sql/` | Schema, RLS policies, triggers, seed data (numbered SQL migrations) |
| UI | `frontend/src/` | Vue 3 + Vuetify views, Pinia stores, schema-driven dynamic forms |
| Contract | `frontend/src/types/api.generated.ts` | TypeScript types generated from the API's OpenAPI schema |

Stack: Python 3.12, FastAPI, SQLAlchemy 2.0, Pydantic 2 · Vue 3.5, TypeScript 6, Vite 7, Pinia,
Vuetify 4 · PostgreSQL 15.

### LLM

- Data sharing: a run sends only allowlisted curation fields and public IDs (HGNC, MONDO),
  never user names or emails; scope admins see the exact request in the preview
  (`GET /api/v1/scopes/{id}/curations/{id}/llm-preview`).
- The database owner that runs the migrations must be a superuser (or have BYPASSRLS):
  the SECURITY DEFINER functions (`llm_claim_run`, `llm_credential_ciphertext`, like the
  005 RLS helpers) read past FORCE ROW LEVEL SECURITY as that owner. On managed Postgres
  such as RDS, where the master user is not a superuser, grant it BYPASSRLS or the worker
  claims nothing.

## MCP server

Gene Curator is also an MCP server at `<API base URL>/mcp`, so Claude Code, Claude Desktop or an
agent can work as you: every tool is an existing API endpoint and runs with your identity, scope
roles, row-level security and four-eyes rules. Create a personal access token under
**Access tokens** in the user menu, then:

```bash
claude mcp add --transport http gene-curator http://localhost:8051/mcp \
  --header "Authorization: Bearer gc_pat_..."
```

`/mcp` serves the curation core (curate a gene, review a curation, lookups); `/mcp/full` serves
every API operation with the same token. Writes are audited with channel `mcp` and the token
name. Claude Desktop, revocation and the tool list are covered in [docs/MCP_CONNECTION_GUIDE.md](docs/MCP_CONNECTION_GUIDE.md). OAuth 2.1 sign-in
and dynamic client registration come in phase 2. Existing databases need `make db-migrate` (059).

## Documentation

- [AGENTS.md](AGENTS.md): developer and coding-agent guide (setup, commands, architecture, rules)
- [CONTRIBUTING.md](CONTRIBUTING.md): how to propose changes
- [docs/MCP_CONNECTION_GUIDE.md](docs/MCP_CONNECTION_GUIDE.md): connecting MCP clients with a token
- API reference: http://localhost:8051/docs (interactive OpenAPI) while the backend runs
- `backend/docs/`: architecture and schema format notes

## License

MIT, see [LICENSE](LICENSE).

## Acknowledgments

The [ClinGen](https://clinicalgenome.org/) Gene-Disease Validity working group for the SOPs this
platform implements, and the [Gene Curation Coalition (GenCC)](https://thegencc.org/) for its
harmonised standards.
