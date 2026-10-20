# AGENTS.md

Canonical guide for anyone changing Gene Curator: coding agents (Codex reads this file, Claude Code
reads `CLAUDE.md`, which imports it) and humans. Keep it short and current. Rules that tooling
enforces are only pointed to here; if a rule matters, make a tool check it.

## Project

Methodology-agnostic platform for gene-disease curation (ClinGen SOP v11, GenCC, custom) with
configurable schemas, scope-based teams and a multi-stage, 4-eyes review workflow.

| Layer | Stack |
| --- | --- |
| Backend | Python 3.12, FastAPI, SQLAlchemy 2.0, Pydantic 2, uv |
| Frontend | Vue 3.5, TypeScript 6 (migration from JS in progress), Vite 7, Pinia, Vuetify 3, Node 24 |
| Database | PostgreSQL 15 with row-level security; schema in `database/sql/*.sql` |
| Quality | ruff, mypy (strict), bandit, pytest; ESLint 10 + typescript-eslint, Prettier, vue-tsc, Vitest, Playwright |

Ports (source of truth `.env.dev`): API 8051, Vite 5193, Docker UI 3051, Postgres 5454, Redis 6399.
Seeded dev logins (`004_seed_data.sql`): `admin@genecurator.org`, `alice.smith@genecurator.org`
(curator), `bob.jones@genecurator.org` (reviewer), all `admin123`. Local frontend needs `frontend/.env.local` with
`VITE_API_BASE_URL=http://localhost:8051` and `VITE_ENABLE_DEV_LOGIN=true`; without it login fails silently.

## First steps

1. Read this file and the code your task touches. Check `git status` first; never overwrite others' work.
2. `make install` once: backend + frontend deps and git hooks (`.githooks`).
3. `make hybrid-up`, then `make backend` and `make frontend` in two terminals.
4. Keep changes scoped. Do not modernize unrelated code in the same change.

## Commands

The Makefile is the command surface; `make help` lists every target.

| Goal | Command |
| --- | --- |
| Iterate on one test | `cd backend && uv run pytest tests/api/test_x.py -k name` / `cd frontend && npx vitest run src/x` |
| Fast gate (also the pre-push hook) | `make check` |
| Everything CI runs | `make ci` |
| Auto-fix format + lint | `make format` |
| Backend RLS/scope tests on a fresh Postgres | `make test-postgres` (Docker) |
| Regenerate frontend API types after backend schema changes | `make api-types` |
| Dependency vulnerability scan | `make audit` |
| Apply one SQL migration to the dev DB | `make db-migrate FILE=database/sql/0NN_x.sql` |

## Verification and CI

Verify locally; CI only confirms. `.github/workflows/ci.yml` calls the same make targets, so a green
`make ci` means a green PR. Report exactly which gates you ran.

- Gates: ruff, ruff format, mypy, bandit, pytest (SQLite) and the PostgreSQL lane; ESLint, Prettier,
  vue-tsc, Vitest, production build; file-size limit, generated API types up to date, zizmor.
- Required check: the `CI gate` job. Never use `continue-on-error`, `|| true`, `.skip`, `xit` or
  commented-out tests to get green; fix the cause.
- Cost: open PRs as drafts while iterating (drafts run no CI), mark ready once `make ci` passes,
  batch pushes. Do not add workflow triggers, cron jobs or matrix legs without an owner decision.
- Workflow changes: run `make workflows`. Actions stay pinned to a commit SHA with the version in a comment.

## Rules enforced by tools

- **File size:** source files stay at or below 650 lines (`scripts/check_file_size.py`). Files that
  were already larger are in `scripts/file-size-allowlist.txt` and may only shrink; after splitting
  one, run `python3 scripts/check_file_size.py --update`. Split by responsibility (child component,
  composable, service), not by arbitrary cut.
- **Coverage:** changed lines need at least 90% coverage (`make diff-cover`). Global floors
  (`fail_under` in `backend/pyproject.toml`, `thresholds` in `frontend/vite.config.js`) only go up:
  raise them when coverage rises, never lower them. Target is 90% overall.
- **Logging:** backend uses `from app.core.logging import get_logger`; `print` and
  `logging.getLogger` fail ruff (T201, TID251). Frontend uses `useLogger()` in components and
  `logService` elsewhere; `console.*` fails ESLint. Log structured fields
  (`logger.info("Saved", gene_id=...)`), not f-strings.
- **Types:** mypy strict on `backend/app`; vue-tsc on the frontend. No `any`, no `@ts-ignore`.

## Architecture

**Two independent role systems.** `users.application_role` is `admin` or `user` (platform access).
`scope_memberships.role` is `admin`, `curator`, `reviewer` or `viewer` (per-scope). "Curator" is a
scope role, never an application role. Test users: `role="user"` on `UserNew`, scope role on the membership.
A membership with `accepted_at IS NULL` is a pending invitation and grants nothing.

**Backend** (`backend/app`): routers in `api/v1/endpoints/` (registered in `api/v1/api.py`;
`invitations`, `evidence` and `gene_summaries` have no prefix), Pydantic schemas in `schemas/`,
data access in `crud/` (generic `CRUDBase`), business logic in `services/`. Auth chain in
`core/deps.py`: `get_db -> get_current_user -> get_current_active_user -> get_current_admin_user`,
plus `RequireScopeMember/Reviewer/Curator/Admin`. `set_rls_context()` sets `app.current_user_id`
for the RLS policies in `database/sql/005_rls_setup.sql`. Models use SQLAlchemy 2.0 style with UUID
keys and the legacy `New` suffix (`UserNew`, `CurationNew`).

**Schema-driven curation.** Field definitions, validation, scoring and UI layout live in the
`curation_schemas` table, not in code. Workflow pairs link a precuration schema to a curation
schema. Scoring engines subclass `ScoringEngine` and register with `scoring_registry`.
Workflow: Entry -> Precuration -> Curation -> Review (4-eyes) -> Active, backwards transitions
allowed, one active curation per gene and scope (`crud/workflow_engine.py`).

**Frontend** (`frontend/src`): axios client in `api/client` (token refresh on 401, correlation IDs),
one module per resource in `api/`, Pinia stores in `stores/` (components never call `api/` directly),
composables in `composables/`, lazy-loaded routes in `router/` whose `meta` drives auth and menus.
Backend contract types come from `src/types/api.ts` (`Schema<'GeneResponse'>`), generated from
OpenAPI; never hand-write API response types. New and touched files are TypeScript
(`<script setup lang="ts">`).

**Database.** `database/sql/NNN_*.sql` run in order when Postgres initialises an empty volume.
New migrations are a new numbered file, idempotent (`IF NOT EXISTS`, `CREATE OR REPLACE`), and must
pass `make test-postgres`, which builds a fresh database from all files. Mirror schema changes in
`backend/app/models/models.py`. There is no migration bookkeeping yet: apply new files to existing
databases with `make db-migrate`.

## Testing

- Backend tests run on in-memory SQLite (`backend/tests/conftest.py`, compatibility types in
  `app/models/db_types.py`). Anything that depends on RLS, triggers or views goes in
  `backend/tests/postgres/` (marker `postgres`).
- Test behaviour through the public surface: endpoints via the `client` fixture with each scope role,
  CRUD/services for edge cases. External APIs (HGNC, PubMed, HPO) are mocked; tests never hit the network.
- Frontend: Vitest + Vue Test Utils on happy-dom, tests next to code in `__tests__/`. Mock at the
  `@/api/*` boundary. E2E: Playwright (`make test-e2e`).
- Fix a bug with a failing test first. Never weaken an assertion to pass.

## Pitfalls

- SQLAlchemy booleans: `filter(Model.is_active)` or `== True`; never `is True` (always false).
- Backend config has three tiers: `core/constants.py` (immutable), `core/config.py` (env),
  `config/api.yaml` (CORS, rate limits; env override `GENE_CURATOR_API__...`).
- `main.ts` plugin order matters: pinia, logger, router, vuetify.
- Recent FastAPI includes routers lazily: inspect routes via `app.openapi()["paths"]`, not `router.routes`.

## Git and PRs

- Branches `feature/...` or `fix/...`; [Conventional Commits](https://www.conventionalcommits.org/).
- Hooks: `pre-commit` checks staged files (ruff, ESLint, Prettier, size); `pre-push` runs `make check`.
- A PR is ready when `make ci` passes; describe what changed, why, and which gates ran.
- Planning documents live in `.planning/` (GSD); `plan/` is legacy. User-facing docs in `README.md`.

## Tool notes

- Claude Code: `CLAUDE.md` imports this file; private preferences go in `CLAUDE.local.md` (gitignored).
- Codex reads `AGENTS.md` directly; keep it well under its 32 KiB limit.
