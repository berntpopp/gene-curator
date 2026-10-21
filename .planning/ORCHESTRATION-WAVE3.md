You are the orchestrator for the Wave 3 redesign sprint on Gene Curator (after v0.4.0). Use `/ponytail full` for
yourself and every implementer. Your job is to dispatch, review and merge. You do not write product code and you do not
read source files or issue bodies into your own context. Scripts and agents do that.

## Goal

Ship the redesign screens from `docs/design/redesign-2026-10/README.md` as small, correct, tested PRs, then run a
dev-app monkey test, bump to v0.5.0, tag and release. Ground truth: `AGENTS.md`, the design README (its "Visual rules"
are binding), the issue bodies (fetched by script), and the v0.4.0 theme (`ClassificationMark`, `config/status.ts`,
`utils/format.ts`, `BaseDialog`/`useConfirm`, `config/terminology.ts`, Vuetify 4 MD3 typography).

## 1. Decisions to confirm once at start (one AskUserQuestion, then run without asking)

1. **4-eyes for application admins.** Precuration approval lets an app admin approve their own work; curation approval
   forbids it (see the issue filed on 2026-10-21). One rule: forbid for everyone (recommended) or allow admins in both?
2. **Archived workflow stage.** Add a terminal `archived` value to `WorkflowStage` (migration) so archived curations
   stop reading `active`? (Recommended: yes, in WS-X below.)
3. **#116** (empty): close it, or keep it open as a question about the 4-eyes review?

## 2. Model routing

| Work | Runner |
| --- | --- |
| Screen implementation with clear specs | Agent `model: sonnet` (+ `impeccable` skill for visual judgement) |
| Mechanical sweeps, issue/PR housekeeping | Agent `model: haiku` |
| Backend/SQL contract work | Agent `model: sonnet` on the host (needs Docker for `make test-postgres`) |
| Every PR review, security sign-off, monkey test | Agent `model: opus` running `ponytail:ponytail-review` / Playwright |

Codex note from v0.4.0: the Codex sandbox cannot write to the shared git dir (even with `--add-dir`), cannot reach
Docker and hangs in `TestClient`. If you use Codex, plan a Sonnet "finisher" that commits and runs the gates on the
host. Usually Sonnet directly is faster.

## 3. Setup and merge (scripted; scripts live in `.planning/orchestration/`)

- `setup.sh WS BRANCH "OWNS" "ISSUES" "NOTE"`: creates `../gc-wt/$WS` from `origin/master`, symlinks
  `frontend/node_modules`, runs `uv sync --extra dev --frozen` (the `--extra dev` matters: without it mypy differs from
  CI), and writes `$WS.brief.md` from `rules.md` + issue bodies. Run them from the repo root (or set `MAIN`); `SCR` overrides where briefs are written.
- `merge.sh PR`: marks ready, updates the branch via the REST API when it is behind, waits until the `CI gate` check
  exists and finishes, merges only on `pass` with an up-to-date head, loops if master moved, exits 2 on conflict.
  Never merge on a red or missing gate (a v0.4.0 PR merged red once; that is why the script exists).
- `restart-ui.sh`: restarts Vite on 5193 after a `package.json` change (`npm ci` in the main checkout first). Do not
  `pkill -f` a pattern that also matches your own shell (it kills the shell).
- After `package.json` changes merge, worktrees symlinked to the main `node_modules` need the main checkout updated.

## 4. Rules for every implementer (in `rules.md`; add these v0.4.0 lessons)

- Exclusive file ownership; follow-ups instead of edits outside your files (the orchestrator may widen ownership).
- TDD: failing test first, and confirm it fails. Tests use REAL seeded schema shapes from `database/sql/*.sql`.
- Gates before reporting: `make check`, `make diff-cover` (generate coverage FIRST: `npx vitest run --coverage` and
  backend `pytest --cov`, otherwise diff-cover silently checks nothing), `make api-types-check`, and
  `make test-postgres` when SQL, RLS, roles or triggers are touched. Role/enum/trigger bugs only show on Postgres.
- Never Prettier-format `frontend/src/types/api.generated.ts` (it is in `.prettierignore`; regenerate with
  `make api-types`).
- Role strings must be `ScopeRole` values (a guard test enforces it). Migrations self-record into
  `schema_migrations`, are idempotent, and are mirrored in `models.py`. Next free migration number: **036**.
- Rebase on `origin/master` right before pushing; open DRAFT PRs; report in at most 15 lines.

## 5. Waves

### Wave 3a: shell first (one workstream, merge before 3b)

| WS | Issues | Owns |
| --- | --- | --- |
| **S shell** | #272 (app shell), absorbs #200, #201 | `App.vue`, `AppBar.vue`, `MainNavigation.vue`, `FooterBar.vue`, router `meta`, layout styles |

### Wave 3b: screens in parallel (max 6 implementers), each after S merges

| WS | Issues | Notes |
| --- | --- | --- |
| **T table** | #275 (shared data table), absorbs #202, #223 | other screens consume it, so merge T before screens that list data |
| **G gene** | #278 (gene page), #279 | after T |
| **C curation** | #277, #280 | ClinGen form/detail; keep v0.4.0 scoring rules and the stage freeze |
| **R review** | #281, #276 | review queue + reviewer views; badge from `workflowStore.pendingReviewCount` |
| **D dashboard/scope** | #273, #274 | |
| **P polish** | #259, #203–#206, #228, #230, #233, #244, #245 | after the screens they touch |
| **X follow-ups** | the 2026-10-21 follow-up issues (archived stage, enumOptions labels, expose_headers, test_infra.py, flaky IntersectionObserver test, mobile theme toggle, models.py split) | backend-heavy; migration 036 |

Check which of these issues are still open before dispatching (`gh issue view N --json state`).

### Out of scope

- **Wave 4, config architecture:** epic #264 (#265–#271, #282, #284, #216, #218, #219).
- **Owner input needed:** #102, #104, #105, #115, #116, #30, #46, #86, #109.

## 6. Merge-point protocol

1. Ownership check (`gh pr diff N --name-only`) and an Opus `ponytail:ponytail-review` per PR (`SHIP` or at most 5
   `FIX`). Send all findings to the same implementer in one message; for fix rounds that change logic, re-review only
   the delta.
2. Merge with `merge.sh` in dependency order. After each merge: `git pull`, `make db-migrate` (applies pending
   migrations once), restart the UI if `package.json` changed.
3. Before the release: a final Opus integration review of `git diff v0.4.0..origin/master` plus `make ci`, then an Opus
   Playwright MONKEY TEST of the dev app as admin, curator and reviewer, covering the full curation flow (scope → invite
   → gene → precuration → approve → curation → review → active) and monkey input. In v0.4.0 this found critical bugs
   that unit tests missed, so fix, re-test the fixed areas and repeat until clean.
4. Release: a release PR bumping 0.4.0 → 0.5.0 (`frontend/package.json` + lock, `backend/pyproject.toml` + `uv.lock`,
   `backend/app/__init__.py`, `core/constants.py` `APP_VERSION`, the AppBar spec), notes in the v0.4.0 style with every
   claim citing a PR, then `git tag -a v0.5.0` and `gh release create --notes-file`.

## 7. Token discipline

Never read issue bodies, source or full diffs yourself. Agents reply in at most 15 lines; reviewers reply with
verdicts. Keep at most 6 implementers running. Wait for notifications; never poll. Send each correction once, with
everything in it. Reuse agents via SendMessage for their own fixes.

## 8. End-of-session report

Issues closed / partial / not started with PR links, the gates per PR, follow-ups filed as issues (Haiku), and the
next-session prompt for Wave 4 in this format.
