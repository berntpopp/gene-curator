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
  concurrent edits, and PostgreSQL row-level security for tenant isolation. Evidence rows cite
  sources (PMID, DOI, ClinVar, ClinGen, URL) and record who added them, including the AI agent
  of an MCP write; the export carries this as GA4GH VA-Spec contributions.
- **Configurable permissions:** a role-to-capability matrix stored as data; scope admins own
  their scope's methodologies and workflows and choose which workflow pairs the scope allows.
- **ClinGen adoption and KGDB export:** genes ClinGen already curated are adopted in bulk and
  confirmed by a second person; the versioned export feeds downstream databases such as KGDB
  ([docs/EXPORT.md](docs/EXPORT.md)).

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

### Upgrading to v0.13.0

Run `make db-migrate` (078–082, 084–086, 088, 089, 091; 083, 087 and 090 are unused) before
restarting the backend. Breaking: 4-eyes refusals are 403 and workflow-state refusals 409 (no longer 400);
a scope with a default pair only accepts that pair and the ones listed under scope settings,
*Other allowed workflows* (086 fills the list from each scope's existing work); schema saves
need `lock_version`; a `database` source needs `prefix:id`; a value off its points step is
refused at submit; multifactorial MOI is HP:0010982; export `mode_of_inheritance` is the HPO
CURIE (text in `mode_of_inheritance_entered`). KGDB: re-import
`docs/schemas/kidney-genetics/kgdb-methodology.json` (dry run first) for the approved
susceptibility tiering. Details: [docs/releases/v0.13.0.md](docs/releases/v0.13.0.md#upgrading).
([#592](https://github.com/berntpopp/gene-curator/pull/592),
[#599](https://github.com/berntpopp/gene-curator/pull/599),
[#603](https://github.com/berntpopp/gene-curator/pull/603),
[#604](https://github.com/berntpopp/gene-curator/pull/604),
[#609](https://github.com/berntpopp/gene-curator/pull/609),
[#617](https://github.com/berntpopp/gene-curator/pull/617),
[#619](https://github.com/berntpopp/gene-curator/pull/619),
[#624](https://github.com/berntpopp/gene-curator/pull/624))

### Upgrading to v0.12.0

Before upgrading production, run the duplicate query printed by migration 077 (also in
[docs/releases/v0.12.0.md](docs/releases/v0.12.0.md#upgrading)) and archive all but one open
precuration per gene, scope and disease entity; 077 stops with the list otherwise. Then run
`make db-migrate` (076 `export_evidence_public`, off by default; 077 one open precuration per
entity) before restarting the backend. Breaking: publishing a point model whose paths name
missing fields now fails; fix them in the schema editor before the next publish. Schemas and
point models are now built and published in the UI. The KGDB methodology bundle
`docs/schemas/kidney-genetics/kgdb-methodology.json` imports as a platform admin through
Schema Management, *Import methodology* (dry run first), or
`POST /api/v1/schemas/methodologies/import` (see its
[README](docs/schemas/kidney-genetics/README.md)).
([#570](https://github.com/berntpopp/gene-curator/pull/570),
[#582](https://github.com/berntpopp/gene-curator/pull/582),
[#583](https://github.com/berntpopp/gene-curator/pull/583),
[#585](https://github.com/berntpopp/gene-curator/pull/585))

### Upgrading to v0.11.0

Run `make db-migrate` (071–075, applied in order) before restarting the backend. New are a
curator classification next to the computed one, a relationship type (Mendelian or
susceptibility; susceptibility entity keys end in `|SUSCEPTIBILITY`) and schema-defined
classification vocabularies. Two scope settings, both off by default: `auto_second_view_on_submit`
queues the LLM second view on submit, and `approvals_require_session` lets only a signed-in
person approve (tokens and MCP can still comment). Custom schemas flag fields an LLM run may
see with `"llm_share": true` (see [LLM](#llm)). Breaking: a save that moves a curation to
another entity returns 409. Export consumers: see the KGDB contract notes in
[docs/releases/v0.11.0.md](docs/releases/v0.11.0.md).
([#553](https://github.com/berntpopp/gene-curator/pull/553),
[#554](https://github.com/berntpopp/gene-curator/pull/554),
[#555](https://github.com/berntpopp/gene-curator/pull/555),
[#562](https://github.com/berntpopp/gene-curator/pull/562))

### Upgrading to v0.10.1

Run `make db-migrate` before restarting the backend: it applies 070, which publishes a ClinGen
Precuration version with the X-linked and Undetermined MOI options. No breaking changes; new are
the export of reviewed curations (`GET /api/v1/export/curations`, see
[docs/EXPORT.md](docs/EXPORT.md)) and url fields in schemas. Details:
[docs/releases/v0.10.1.md](docs/releases/v0.10.1.md).
([#545](https://github.com/berntpopp/gene-curator/pull/545),
[#547](https://github.com/berntpopp/gene-curator/pull/547),
[#548](https://github.com/berntpopp/gene-curator/pull/548))

### Upgrading to v0.10.0

Run `make db-migrate` (064–069, applied in order) before restarting the backend. The migration
user must be a superuser or have BYPASSRLS, because 064 adds SECURITY DEFINER functions for
OAuth. Run it while nobody is editing: the 067 backfill bumps `lock_version`, so open editors
get 409 on their next save. Set `GENE_CURATOR_PUBLIC_URL` (https in production) and
`GENE_CURATOR_FRONTEND_URL`; `docker-compose.prod.yml` refuses to start without them. Claude
Code signs in over OAuth with `claude mcp add --transport http gene-curator https://<API host>/mcp`,
then `/mcp` and Authenticate; personal access tokens keep working. Breaking: the four
`/curations/{id}/evidence...` endpoints are removed; `make recompute-scores` now covers every
engine, and out-of-range rows score 0. Details: [docs/releases/v0.10.0.md](docs/releases/v0.10.0.md).
([#528](https://github.com/berntpopp/gene-curator/pull/528),
[#537](https://github.com/berntpopp/gene-curator/pull/537),
[#527](https://github.com/berntpopp/gene-curator/pull/527))

### Upgrading to v0.9.0

Run `make db-migrate` (056–063) before restarting the backend. The database owner that runs
migrations must be a superuser or have BYPASSRLS, because SECURITY DEFINER functions read past
FORCE RLS as that owner; without it, personal access tokens and MCP get 401, curators cannot
assign reviewers, and the LLM worker claims nothing. Set `LLM_CREDENTIAL_KEYS` and `LLM_CREDENTIAL_ACTIVE_KID` (see `.env.example`).
Rate limiting is on in `docker-compose.prod.yml`; behind a reverse proxy set
`FORWARDED_ALLOW_IPS` to the proxy's address. Buckets are per worker, so N workers allow up to N times the configured rate. Breaking: curation writes, scope lists and schema
lists answer concisely unless `detail=true`; `CurationDetail.calculated_score` is gone; the
evidence-item endpoints are deprecated; only cited evidence scores (no or unknown PMID, no or a
placeholder variant, or a blank `score_status` scores 0 and submit refuses it); `gene_summaries`
is dropped; `/mcp` serves the curation core and `/mcp/full` everything; 422s no longer echo
input. Details: [docs/releases/v0.9.0.md](docs/releases/v0.9.0.md).
([#494](https://github.com/berntpopp/gene-curator/pull/494),
[#500](https://github.com/berntpopp/gene-curator/pull/500),
[#492](https://github.com/berntpopp/gene-curator/pull/492),
[#506](https://github.com/berntpopp/gene-curator/pull/506),
[#511](https://github.com/berntpopp/gene-curator/pull/511),
[#519](https://github.com/berntpopp/gene-curator/pull/519))

### Upgrading to v0.8.0

Run `make db-migrate` (050–055) before restarting the backend. Users outside a scope now see only
active curations of active public scopes, and get 404 for drafts and other non-active work; scope
members are unaffected. Saving a GenCC or qualitative curation now scores it with its schema's
engine, so its stored verdict can change on the next save; `make recompute-scores` was
ClinGen-only until v0.10.0, which covers every engine. Writes in an inactive scope return 409. Production builds no longer contain the seeded dev logins. Details and known limits:
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

## Adopting a ClinGen classification

Gene Curator also includes genes that ClinGen has already curated; an adopted curation shows an
*Adopted from ClinGen* badge linking the ClinGen record. To adopt instead of re-scoring, a curator
or agent sends one row per entity to `POST /api/v1/curations/clingen-adoptions` (MCP
`adopt_clingen_classifications`, `dry_run=true` first): the gene, scope, workflow pair, MONDO id
and MOI, plus the ClinGen record exactly as GeneFoundry `clingen_get_gene_validity` returns it
(`perm_id` as `cggv_id`, `raw_sha256` as `record_sha256`, `recommended_citation` as `citation`,
`provenance.retrieved_at` as `retrieved_at`, with `permalink`, `classification`, `moi`, `mondo`,
`hgnc_id`, `expert_panel`, `classified_date`). Gene Curator never fetches the record; it checks
that gene, MONDO id and MOI match the entity and that the class is one of the schema's. Any
invalid row refuses the whole batch (422 listing each row's errors); an entity with an open
curation is refused, and re-adopting the same record changes nothing. Each curation goes to
review with the ClinGen class as the curator classification and the comment "Curation details
were taken from ClinGen as available there, the individual point values must be re-scored
manually." Another reviewer of the scope confirms it by approving (4-eyes). The export carries
it as an `adoption` statement (see [docs/EXPORT.md](docs/EXPORT.md)).

## Backup and restore

`make db-backup` runs `scripts/backup.sh`: a `pg_dump` in custom format, checked with
`pg_restore --list` before it is kept as `backups/backup_YYYYMMDD_HHMMSS.dump`. A failed or
unreadable dump leaves no file behind. Only the newest `BACKUP_KEEP` dumps (default 14) are kept.
For periodic backups, schedule the script (see its header for a cron line) and copy `backups/`
off the host.

To restore:

1. Stop the backend so no writes land during the restore.
2. Check the dump: `docker exec -i gene_curator_postgres pg_restore --list < backups/<file>.dump`.
3. `make db-restore FILE=backups/<file>.dump` (drops and recreates the dumped objects).
4. Run `make db-migrate` if the dump predates the current migrations, then start the backend.

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

### Rate limiting

Off by default (`features.enable_rate_limiting: false` in `backend/config/api.yaml`), so dev and
tests run unthrottled; `docker-compose.prod.yml` turns it on. Enable it elsewhere with
`GENE_CURATOR_API__FEATURES__ENABLE_RATE_LIMITING=true`; tiers (`default` per IP, `authenticated`,
`admin`) are under `rate_limits`. Buckets live in each worker's memory, so N workers allow up to
N times the configured rate and a restart resets them. Behind a reverse proxy set
`FORWARDED_ALLOW_IPS` to the proxy's address, or every caller shares the proxy's bucket.

### LLM

- Data sharing: a run sends only allowlisted curation fields and public IDs (HGNC, MONDO),
  never user names or emails; scope admins see the exact request in the preview
  (`GET /api/v1/scopes/{id}/curations/{id}/llm-preview`).
- AI second view (#464, #465): the skeptic and advocate get the evidence facts only (PMIDs,
  variants, phenotypes, descriptions), never the curator's points, score status, rationale,
  summary or classification. Their output is advisory and cannot change a curation. Provider
  API keys are encrypted at rest and stay on the server; no response or log carries them.
- Custom and derived schemas: a field is sent only if it is a seeded evidence key or flagged
  `"llm_share": true` in `field_definitions`; `"llm_share": false` withholds even a seeded key.
  Sharing is by key name at every depth, so schema validation refuses a name flagged
  differently in two places, refuses the flag on curator judgement keys and warns about
  fields a run would drop (#534).
- Second view on submit (#464): opt-in per scope (`auto_second_view_on_submit`, off by
  default). A submit queues it under the scope caps and never fails because of it; the run is
  attributed to the admin who last saved the scope's LLM settings.
- The database owner that runs the migrations must be a superuser (or have BYPASSRLS):
  SECURITY DEFINER functions read past FORCE ROW LEVEL SECURITY as that owner
  (`authenticate_personal_access_token` in 056, `llm_credential_ciphertext` in 057,
  `llm_claim_run` in 060, `is_scope_reviewer` in 061, like the 005 RLS helpers). On managed
  Postgres such as RDS, where the master user is not a superuser, grant it BYPASSRLS; without
  it, personal access tokens and MCP get 401, curators cannot assign reviewers, and the LLM
  worker claims nothing.

## MCP server

Gene Curator is also an MCP server at `<API base URL>/mcp`, so Claude Code, Claude Desktop or an
agent can work as you: every tool is an existing API endpoint and runs with your identity, scope
roles, row-level security and four-eyes rules. Create a personal access token under
**Access tokens** in the user menu, then:

```bash
claude mcp add --transport http gene-curator http://localhost:8051/mcp \
  --header "Authorization: Bearer gc_pat_..."
```

`/mcp` serves the curation core (set up a scope, curate a gene, review a curation; research goes through a literature MCP such as GeneFoundry); `/mcp/full` serves
every API operation with the same token. Writes are audited with channel `mcp` and the token
name. Claude Desktop, revocation and the tool list are covered in [docs/MCP_CONNECTION_GUIDE.md](docs/MCP_CONNECTION_GUIDE.md). Existing databases need `make db-migrate` (064).

### OAuth sign-in

Clients that speak MCP OAuth 2.1 need no token: add the server without a header and sign in
when the client opens the browser.

```bash
claude mcp add --transport http gene-curator https://<API host>/mcp
```

In Claude.ai add a custom connector with the same URL. The client registers itself (RFC 7591),
finds the server through `/.well-known/oauth-protected-resource/mcp` and
`/.well-known/oauth-authorization-server`, and sends you to the consent page, where you allow or
deny it while signed in. Only the authorization code flow with PKCE S256 is served. The access
token lasts an hour and is refreshed with a rotating refresh token (30 days, sliding). Each
connection appears under **Access tokens** as `OAuth: <client name>`; revoking it there ends the
connection, refresh included. OAuth calls get exactly the token treatment above: your identity,
RLS, four-eyes and no account or token management. Only hashes of codes, tokens and client
secrets are stored. Configure the public URLs; `docker-compose.prod.yml` refuses to start
without them, and with `ENVIRONMENT=production` the API refuses a non-HTTPS issuer:

| Variable | Default | Meaning |
| --- | --- | --- |
| `GENE_CURATOR_PUBLIC_URL` | `http://localhost:8051` | API origin MCP clients reach (OAuth issuer) |
| `GENE_CURATOR_FRONTEND_URL` | `http://localhost:5193` | Web app origin that serves `/oauth/consent` |

## Production deployment

Release tags `vX.Y.Z` publish `ghcr.io/berntpopp/gene-curator/{backend,frontend,migrate}`
(`.github/workflows/docker.yml`, with provenance and SBOM). Run them behind a reverse proxy with
`docker-compose.yml` plus `docker/docker-compose.npm.yml` and a third file that pins the images by
digest; copy `.env.docker.example` to `.env.docker` first. The overlay publishes no ports, joins
the external `npm_default` network, gives its internal network the subnet `10.251.10.0/24` and
starts the backend only after the one-shot `migrate` service applied `database/sql` (idempotent,
recorded in `schema_migrations`). Production gets no seeded logins: 004 keeps a disabled seed owner
only. Create the first platform admin once (the password stays in your environment):

```bash
ADMIN_PASSWORD='<12+ characters>' docker compose -f docker-compose.yml -f docker/docker-compose.npm.yml \
  --env-file .env.docker run --rm -e ADMIN_EMAIL=you@example.org -e ADMIN_PASSWORD \
  backend python scripts/create_default_user.py
```

The web image calls `/api/v1` on its own origin: proxy `gene-curator.org` to
`gene_curator_frontend:80`, nothing else. Its nginx forwards `/api`, `/mcp` and the MCP OAuth
endpoints (`/authorize`, `/token`, `/.well-known`, `POST /register`) to the backend, which stays
on the internal network and trusts forwarded client addresses only from it. With `ENVIRONMENT=production` the API refuses a
`SECRET_KEY` shorter than 32 characters or a placeholder.

## Documentation

- [docs/CURATOR-GUIDE.md](docs/CURATOR-GUIDE.md): curating and reviewing, one page
- [docs/ADMIN-GUIDE.md](docs/ADMIN-GUIDE.md): setting up scopes, methodologies and permissions, one page
- [docs/releases/](docs/releases/): release notes and upgrade steps per version
- [AGENTS.md](AGENTS.md): developer and coding-agent guide (setup, commands, architecture, rules)
- [CONTRIBUTING.md](CONTRIBUTING.md): how to propose changes
- [docs/MCP_CONNECTION_GUIDE.md](docs/MCP_CONNECTION_GUIDE.md): connecting MCP clients with a token
- API reference: http://localhost:8051/docs (interactive OpenAPI) while the backend runs
- [docs/METHODOLOGY-IMPORT.md](docs/METHODOLOGY-IMPORT.md): importing a methodology bundle (schemas, pairs, scope default)
- [docs/POINT-MODEL.md](docs/POINT-MODEL.md): point-model scoring format
- [docs/EXPORT.md](docs/EXPORT.md): exporting curations
- [docs/schemas/](docs/schemas/): methodology bundles (ClinGen SOP v11, kidney genetics)
- [docs/examples/export-page.json](docs/examples/export-page.json): a generated example export page and its JSON Schema

## License

MIT, see [LICENSE](LICENSE).

## Acknowledgments

The [ClinGen](https://clinicalgenome.org/) Gene-Disease Validity working group for the SOPs this
platform implements, and the [Gene Curation Coalition (GenCC)](https://thegencc.org/) for its
harmonised standards.
