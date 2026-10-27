You are the orchestrator for the Wave 3 sprint on Gene Curator (after v0.4.1, master 164b07c+). Use `/ponytail full`
for yourself and every implementer. Your job is to dispatch, review and merge. You do not write product code and you do
not read source files, issue bodies or full diffs into your own context. Scripts and agents do that.

## Goal

Ship the redesign foundations and screens from `docs/design/redesign-2026-10/README.md` plus the open backend hygiene
issues as small, correct, tested PRs, then run a dev-app monkey test, bump to **v0.5.0**, tag and release. Ground truth:
`AGENTS.md`, the design README ("Visual rules" are binding), issue bodies (fetched by `setup.sh`), and the v0.4.x theme
(`ClassificationMark`, `config/status.ts`, `utils/format.ts`, `BaseDialog`/`useConfirm`, `config/terminology.ts`,
Vuetify 4 MD3 typography).

The config-driven methodology epic (#264–#271, #282, the editable part of #284) is **out of scope**; it is Wave 4.

## 1. Owner decisions (ONE AskUserQuestion at start, then run without asking)

| # | Question | Recommended |
| --- | --- | --- |
| D1 | #324 4-eyes: one rule for precuration and curation approval? | Forbid self-approval for everyone, platform admins included |
| D2 | Legacy issues: close #30, #46 (superseded by #277/#281), #102, #109 (stale), #115, #116 (single-reviewer 4-eyes is enough); keep #86, #104, #105 open? | Yes, as listed |
| D3 | #278 workspace / #279 review: ship the parts that do not need the epic now (workspace header, save state, Ctrl+S, score panel; per-item review comments + diff against the audit-log snapshot), and leave ClinGen form internals untouched because #267 replaces them? | Yes, Wave 3c |
| D4 | My work (#277) replaces the dashboard at `/` for signed-in users; Home stays for signed-out users? | Yes |

Defaults that need no question (state them in the report): saved table views live in `localStorage` (no new table);
#281 includes the Members and Settings tabs (#203, #204); palette search (#273) covers genes, curations and scopes
the user can see (RLS-scoped), not users; #196's remaining backend checks go into the capability slice (WS-K).

## 2. Model routing

| Work | Runner |
| --- | --- |
| Screens with clear specs | Agent `model: sonnet` + `impeccable` skill for visual judgement |
| Backend endpoints, migrations, RLS | Agent `model: sonnet` on the host (needs Docker for `make test-postgres`) |
| Issue/PR housekeeping, mechanical sweeps | Agent `model: haiku` |
| Every PR review, security sign-off, monkey test | Agent `model: opus` running `ponytail:ponytail-review` / Playwright MCP |

Do not use Codex for work that must commit, reach Docker or run `TestClient` (its sandbox cannot). Sonnet is faster.

## 3. Setup and merge (scripts in `.planning/orchestration/`, run from the repo root)

- `setup.sh WS BRANCH "OWNS" "ISSUES" "NOTE"`: worktree `../gc-wt/$WS` from `origin/master`, `frontend/node_modules`
  symlink, `uv sync --extra dev --frozen`, writes `$WS.brief.md` (rules.md + issue bodies). `SCR` sets the brief dir.
- `merge.sh PR`: marks ready, updates the branch via REST when behind, waits for the `CI gate` check, merges only on
  `pass` with an up-to-date head, deletes the branch, loops if master moved, exits 2 on conflict. Never merge red.
- `restart-ui.sh`: restarts Vite on 5193 after a `package.json` change. Never `pkill -f` a pattern matching your shell.
- After each merge: `git pull`, `make db-migrate`, `npm ci` in the main checkout if `package.json` changed.

## 4. Implementer rules (in `rules.md`; repeat the critical ones in every brief)

- Exclusive file ownership. Anything outside your files becomes a follow-up note, not an edit.
- TDD: failing test first, confirm it fails. Tests use REAL seeded shapes from `database/sql/*.sql`.
- Gates before reporting: `make check`; coverage FIRST (`npx vitest run --coverage`, `pytest --cov`) then
  `make diff-cover`; `make api-types-check` (backend schema changed → `make api-types`); `make test-postgres` when SQL,
  RLS, roles, triggers or enum values are touched (those bugs only show on Postgres).
- Never Prettier `frontend/src/types/api.generated.ts`. Role strings are `ScopeRole` values. Migrations are idempotent,
  self-record in `schema_migrations`, mirror `models.py`; next free number **036**, claim numbers in order of merge.
- A shared component's PR (DataTable, shell) never edits the screens that will adopt it.
- PR body: `Closes #N` for every issue fully solved, `Part of #N` otherwise. Rebase on `origin/master` before
  pushing; DRAFT PRs; report in at most 15 lines (PR, gates run with result, follow-ups).

## 5. Waves (max 6 implementers at once)

Check state first: `gh issue list --state open --limit 200 --json number,title`. Skip anything already closed.

### Wave 3a: foundations + hygiene (6 parallel)

| WS | Issues | Owns | Notes |
| --- | --- | --- | --- |
| **H backend hygiene** | three PRs in order: H1 #321 + #329; H2 #330 + #331 + #332; H3 #320 + #333 + #334 | H1 `app/main.py`; H2 `schemas/logs.py`, `schema_repository.py`, `endpoints/schemas.py`, `auth.py`, `endpoints/workflow.py`, `crud/gene*.py`, `crud/logs.py`; H3 `tests/conftest.py`, `core/security.py`, `test_infra.py`, `pyproject.toml` | #332 needs a count test that fails first; #334 needs a test that old hashes still verify |
| **K capabilities** | #196 (rest), #324 (D1), #284 first slice only | new `core/capabilities.py`, `core/deps.py`, write checks in `endpoints/curations.py` / `precurations.py`, `crud/workflow_engine.py`, `stores/scopes.ts` role chip, `GeneRowActions.vue` gate | one `require(capability, scope)` backed by a hard-coded dict + a test per role × capability; no DB matrix (Wave 4). `make test-postgres` |
| **S shell** | #272, absorbs #325 | `App.vue`, `components/navigation/*`, `AppBar.vue`, `FooterBar.vue`, router `meta` | split: S1 rail + layout, S2 phone bottom tabs + theme toggle, S3 badge counts store (uses `/me/work` from B1 when merged, else existing counts) |
| **T table** | #275; also #250 (gene status maps) and #322 (flake) as separate small PRs | new `components/common/DataTable.vue`, `composables/useTableUrlState.ts`; #250: `GeneList.vue`, `geneDisplay.ts`; #322: `src/test/setup.ts`, the spec | DataTable must not edit any screen; run the #322 spec 20× to prove it |
| **L sign-in** | #274, Home/About part of #259 | `Login.vue`, `Home.vue`, `About.vue` | About still says "Vuetify 3" |
| **B backend for screens** | one PR per endpoint, in order: B1 `GET /me/work` (#277, #272 badges); B2 `gene_summaries` + curation_id/disease/stage/score per scope, member-aware (#280, #230); B3 HGNC batch resolve: exact → previous symbol → alias → HGNC ID, ambiguities returned (#281, #193); B4 `GET /search?q=` RLS-scoped (#273) | new endpoint/crud/schema files per item; `api/v1/api.py` registration | each runs `make api-types`; B2/B4 need Postgres tests for RLS |

### Wave 3b: screens (after S1 and T merge; each also after its B endpoint)

| WS | Issues | Absorbs | Depends on |
| --- | --- | --- | --- |
| **W my work** | #277 | #228 | B1, D4 |
| **C scope page** | #281 (C1 stage strip + bulk bar, C2 paste-a-list intake, C3 workload, C4 Members/Settings tabs) | #200, #202, #203, #204, #205, #206, #201 (scope list on DataTable) | B3, existing `/gene-assignments/bulk` |
| **G gene page** | #280 (merge GeneDetail + GeneSummaryView) | #230, #233 | B2 |
| **M catalogue matrix** | #276 (M1 backend `scope_ids[]` matrix endpoint, M2 matrix table, M3 scope picker + saved view in localStorage) | #223 | T |
| **P palette** | #273 | — | S1, B4 |
| **X backend structure** | serial: X1 #326 split `models.py` (alone, no other open PR touching `models.py`), X2 #323 `archived` stage (migration 036), X3 #327 labelled `enumOptions` | — | X1 before X2 |

`router/index.ts` is touched by S, W, G and M: each edits only its own route entries; S's `meta` changes merge first.

### Wave 3c: workspace and review (only after 3b merges; D3 must be yes)

| WS | Issues | Notes |
| --- | --- | --- |
| **E workspace** | #278a: header, breadcrumb, stage line, save state, Ctrl+S, score panel with band bar; #245; #319 | do not restructure `components/clingen/**` (#267 replaces it) |
| **V review** | #279a backend: per-item review comments table (migration + RLS policy per command) and a diff endpoint against the audit-log snapshot; #279b diff view; #279c approve checklist | absorbs #244. `make test-postgres` |

If the session runs long, release v0.5.0 after 3b and hand 3c to the next session.

### Out of scope

- Wave 4: epic #264 (#265–#271), #282, editable #284, #216, #218, #219, #105. Recommended first slice for Wave 4:
  `methodology_versions` with immutable publish + pinned `methodology_version_id` on curations (M). YAGNI candidates
  to ask about then: custom language #269 and three-way upstream merge #271.
- Owner input: #86 (backup schedule/target), #104 (user guide after the redesign settles).

## 6. Housekeeping (Haiku, at start, in parallel with 3a)

Apply D2 (close with a one-line reason each). Comment "absorbed by #N" on each absorbed issue (tables above) so the
screen PR's `Closes` list is obvious. Do not close absorbed issues by hand; the merging PR closes them.

## 7. Merge-point protocol

1. Ownership check (`gh pr diff N --name-only` against the brief) and an Opus `ponytail:ponytail-review` per PR
   (`SHIP` or at most 5 `FIX`). All findings go to the same implementer in one message; for fix rounds, re-review only
   the delta. Security-relevant PRs (K, B2, B4, V) get an explicit authorization/RLS check in the review prompt.
2. Merge with `merge.sh` in dependency order: H, L, T, K any time; S1 before S2/S3 and all 3b screens; B1 before W and
   S3; X1 before X2.
3. Before the release: an Opus integration review of `git diff v0.4.1..origin/master` plus `make ci`, then an Opus
   Playwright MONKEY TEST of the dev app as admin, curator and reviewer (seeded logins in `AGENTS.md`), at desktop and
   phone width: full flow (scope → invite → gene intake → precuration → approve → curation → review → active), every new
   screen, the palette, deep links with URL table state, role gating, and monkey input (empty, huge, unicode, double
   submit, back button). In v0.4.0 this found critical bugs unit tests missed: fix, re-test the fixed areas, repeat
   until clean.
4. Release PR bumping 0.4.1 → 0.5.0 (`frontend/package.json` + lock, `backend/pyproject.toml` + `uv.lock`,
   `backend/app/__init__.py`, `core/constants.py` `APP_VERSION`, the app-bar version display + spec), notes in the
   v0.4.0 style with every claim citing a PR, then `git tag -a v0.5.0` and `gh release create --notes-file`.

## 8. Token discipline

Never read issue bodies, source or full diffs yourself. Agents reply in at most 15 lines; reviewers reply with
verdicts. At most 6 implementers. Wait for notifications; never poll. Send each correction once, with everything in it.
Reuse an implementer via SendMessage for its own fixes and its next PR in the same workstream (it keeps its context).

## 9. End-of-session report

Issues closed / partial / not started with PR links, gates per PR, decisions taken (D1–D4 and defaults), follow-ups
filed as issues (Haiku), and the Wave 4 prompt in this format, starting from the epic's first slice.
