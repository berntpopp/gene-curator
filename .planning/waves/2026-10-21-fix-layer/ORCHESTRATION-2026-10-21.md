# Orchestration prompt: fix-layer sprint (written 2026-10-21)

Paste everything below the line into a fresh Claude Code session (Opus 5.5) started in the repo root.

---

You are the orchestrator for a parallel bug-fix sprint on Gene Curator. Use `/ponytail full` for yourself and
every implementer. Your job is to dispatch, review and merge. You do not write product code and you do not read
source files or issue bodies into your own context. Scripts and agents do that.

## Goal

Close as many open issues as possible with small, correct, tested PRs. Do Wave 0 and Wave 1 completely, then
Wave 2 if budget allows. Waves 3 and 4 are out of scope and listed only so nobody starts them by accident.
Ground truth: `AGENTS.md`, `docs/design/redesign-2026-10/README.md`, and the issue bodies (fetched by script).

## 1. Decisions to confirm once at start (one AskUserQuestion, then run without asking)

1. **#159 Redis.** Remove the service, `REDIS_URL` and the port (the default), or keep it?
2. **Superseded issues.** Close these with a "superseded by #N" comment? #66→#172/#173, #67→#275, #75→#273,
   #77→#267, #95→#275, #118→#282, #119→#281, #120→#282, #19→#278. Leave #116 (empty) open and ask the owner
   whether 4-eyes review already covers it.
3. **#164 Vuetify 4.** Run it as the first step of Wave 2, before the theme work, so the theme is only built once?
   The other option is to defer it.

## 2. Model routing (cheapest that is reliably correct)

| Work | Runner | Why |
| --- | --- | --- |
| Mechanical edits, sweeps, issue/PR housekeeping, commits, rebases | Agent `model: haiku` | Cheap and enough for pattern edits |
| Frontend Vue fixes with clear acceptance criteria | Agent `model: sonnet` | Good Vue/TS quality per token |
| Backend logic, SQL migrations, cross-cutting backend+frontend contracts, perf bundling | Codex CLI `gpt-6-astra`, `model_reasoning_effort=high` (the `~/.codex/config.toml` default) | Fast, low Claude token use |
| Hardest items (#229, #156) | Codex `-m gpt-6.1-sol -c model_reasoning_effort=high`. Probe the id once; if rejected, fall back to astra | Deepest reasoning |
| Merge-point review, conflict resolution, security sign-off | Agent `model: opus` running the `ponytail:ponytail-review` skill | Highest judgement, only at merge points |

Codex call. Run it in the background; Bash `run_in_background: true` notifies you when it finishes:

```bash
codex exec -C "$WT" -s workspace-write -c model_reasoning_effort=high \
  --add-dir "$(git -C "$MAIN" rev-parse --git-common-dir)" \
  -o "$SCR/$WS.result.md" "$(cat "$SCR/$WS.brief.md")"
```

- `--add-dir` lets Codex commit inside a worktree. If the flag is unsupported, tell Codex not to commit; a Haiku
  agent commits afterwards.
- The Codex sandbox has no network. Briefs therefore carry the issue bodies, and all dependencies are installed
  before launch.

## 3. Setup (orchestrator, scripted, once per workstream)

```bash
MAIN=$PWD; SCR=<your scratchpad>; WT=$MAIN/../gc-wt/$WS
git worktree add "$WT" -b "$BRANCH" master
ln -s "$MAIN/frontend/node_modules" "$WT/frontend/node_modules"   # valid while package.json is unchanged
(cd "$WT/backend" && uv sync --frozen -q)
# brief = template (section 6) + owned files + issue bodies, built without reading them yourself:
for n in $ISSUES; do gh issue view $n --json number,title,body -q '"## #\(.number) \(.title)\n\(.body)\n"'; done >> "$SCR/$WS.brief.md"
```

Worktrees only run tests (SQLite, Vitest). Nobody starts dev servers in a worktree. Visual checks happen on
master at merge points, using the already-running dev stack (API 8051, UI 5193).

## 4. Rules every implementer follows (put them in each brief)

- **File ownership is exclusive.** Edit only the files listed for your workstream, plus new test files next to
  them. If you need a change in a file you don't own, write it under "Follow-ups" in your report; do not make it.
  - Exception: `frontend/src/router/index.ts` may receive add/remove edits of your own route entries. Guards and
    `meta` belong to WS-B.
- **One PR per workstream.** One commit per issue:
  `fix(<area>): <what> (#N)` + blank line + `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
  The PR body says `Closes #a, closes #b`, lists the gates run, and ends with
  `🤖 Generated with [Claude Code](https://claude.com/claude-code)`. Open PRs as **drafts**.
- **TDD for bugs.** Write a failing test first. Changed lines need 90% coverage (`make diff-cover`). Never use
  skip, xit, `|| true` or weakened asserts.
- **Gates before reporting:** targeted tests, then `make check` in the worktree. Run `make test-postgres` if you
  touched `database/sql` or RLS.
- **Migrations use reserved numbers only:** 028 = #234, 029 = #198, 030 = #158 (schema_migrations),
  031 = #156 (RLS app role). They must be idempotent and mirrored in `models.py`.
- **#199 is decided:** delete the `/scope-selection` wizard (see the decision comment on #199).
- **Partial fixes.** If an issue cannot be fully fixed inside your owned files, fix what you can, write
  `Refs #N` instead of `Closes`, and state what remains.
- **Report in at most 15 lines:** branch, PR number, issues closed / partial, gates run with results, files
  touched, follow-ups. No diffs, no file dumps.

## 5. Waves and workstreams

### Wave 0: unblockers (one Haiku agent, one PR, merge before any Wave 1 branch is cut)

- Fix the time-dependent test `frontend/src/components/dashboard/__tests__/PendingInvitations.spec.ts` (it
  expects "in 5 hours"). Use fake timers or a fixed `now`. It breaks the pre-push `make check` at some hours.
- **#252:** blank icons (Home, WorkflowManagement, GeneCatalogueView.utils, Disputed rows). Use names that exist
  in `@mdi/font`.
- **#256:** undefined `gap-N` classes in the four admin views.
- **#250:** status maps use `under_review`; the API uses `in_review`. Align them in one place.
- Close the superseded issues if confirmed in section 1.

Then run a short Opus review, merge, and pull master.

### Wave 1a: six in parallel

| WS | Runner | Issues | Owns (exclusive) |
| --- | --- | --- | --- |
| **D1 workflow backend** | Codex sol/astra | #229 (backend), #237 (backend: commit after notifications, surface approve errors), #196 (backend role check), #262, #87 | `crud/precuration.py`, `endpoints/precurations.py`, `crud/workflow_engine.py`, `endpoints/workflow.py`, `core/schema_validator.py`, their tests |
| **D2 data correctness** | Codex astra | #157 (one SOP v11 rule: backend + `clingen/scoring.ts` + `curation/curationScores.ts`), #193, #220 (backend), #221, #234 (migration 028) | `crud/curation.py`, `crud/gene_catalogue.py`, `endpoints/gene_catalogue.py`, `services/validators/hgnc_validator.py`, `scoring/`, those two TS files, `028_*.sql` |
| **I infra** | Codex sol (for #156) | #158 (migration 030 + `make db-migrate` with no args), #156 (non-superuser app role, migration 031; Opus security sign-off required), #159 if confirmed | `Makefile` db targets, `docker-compose*.yml`, `.env*`, `core/config.py` (Redis only), `005_rls_setup.sql` comment, `030_*`, `031_*`, docs lines in AGENTS.md/README |
| **A auth** | Sonnet | #181, #184 (one password rule shared with backend `auth.py`), #186, #188 (UserMenu/Profile only) | `views/Login.vue`, `views/Register.vue`, `views/UserProfile.vue`, `components/**/UserMenu.vue`, `api/client.ts`, `stores/auth.ts` (not the init function: WS-B #174), backend auth endpoint/password validation |
| **C1 scope** | Sonnet | #175, #189, #191 (atomic assign), #195, #197, #198 (migration 029) | `views/scope/*` (ScopeDashboard, ScopeOverview, ScopeCreate, ScopeSettings, ScopeList), `GeneList.vue`, `GeneRowActions.vue`, `AddGeneModal.vue`, `AssignCuratorModal.vue`, `EditGeneAssignmentModal.vue`, `useAddGenes.ts`, `useScopeGenes.ts`, `assignmentDisplay.ts`, `crud/scope.py`, gene-assignment crud/endpoint/schema, `029_*` |
| **E1 curation forms** | Sonnet (#232 perf: Codex astra if Sonnet's first attempt does not reach < 50 ms per keystroke) | #227 (store keeps response wrapper), #232, #239, #240, #241, #243, #246, #263, then #229 (frontend) last, after D1 merges | `ClinGenCurationForm.vue`, `EvidenceDataTable.vue`, `PMIDInput.vue`, `SchemaDrivenCurationForm.vue`, `SchemaDrivenPrecurationForm.vue`, `CurationFormView.vue`, `PrecurationFormView.vue`, `DynamicForm.vue`, `FormRecoveryDialog.vue`, `useCurationSubmission.ts`, `useSchemaScoring.ts`, the schema/validation store holding #227 |

**Merge point 1** (section 7) merges in this order: D1, D2, I, A, C1, E1.

### Wave 1b: start each workstream as soon as its blocking Wave 1a PR is merged

| WS | Runner | Issues | Owns | Waits for |
| --- | --- | --- | --- | --- |
| **B shell and feedback** | Sonnet | #247 (render toasts), #248 (BaseDialog focus/Escape; per-modal fixes become follow-ups), #185, #183, #187, #192, #194, #210, #236 (delete ValidationDashboard), then #174 last | `App.vue`, `router/index.ts` (guards, meta), `AppBar.vue`, `MainNavigation.vue`, `BaseNavigationItem.vue`, `FooterBar.vue`, `LogViewer.vue`, `MessageSnackbar.vue`, `BaseDialog.vue`, `NotFound.vue`, `NotAuthorized.vue`, `Home.vue`, `DisclaimerDialog.vue`, `ValidationDashboard.vue`, `stores/notifications.ts`, `useNotifications.ts`, auth-store init (#174) | A (for #174 only; start the rest at once in 1a if there is capacity) |
| **C2 my work** | Sonnet | #199 (delete wizard + CreateAssignment stub), #226, #235, #225 | `GeneAssignments.vue`, `GeneAssignmentManager.vue`, `ScopeSelection.vue`, `CreateAssignment.vue` (+ spec), `AssignmentDetail.vue`, `Dashboard.vue`, `useGeneWorkflowStatus.ts`, `GenesTable.vue`, `GeneDetail.vue` (error state only) | C1 |
| **E2 review and detail** | Sonnet | #231 (approve/reopen precuration screen), #238 (read-only evidence for reviewers), #242, #237 (frontend: visible errors) | `CurationDetailView.vue`, `ReviewQueueView.vue`, `CurationHeader.vue`, `CurationList.vue`, `api/precurations.ts`, review stores | D1, E1 |
| **G schema admin** | Codex astra | #207, #208, #209, #213, #217, #212 (minimal: platform admin required for schema writes, so #284 can widen it later) | `SchemaManagement.vue`, `SchemaEditor.vue`, `WorkflowManagement.vue`, `schemaTransformer.ts`, `stores/schemas.ts`, `api/schemas.ts`, `endpoints/schemas.py`, `schema_validators.py`, seed/schema SQL only if #207 needs it (then a new migration, not edits to 004/020) | D1 (#262 validator) |
| **H users admin** | Sonnet | #211 (no `prompt()`, no self-demote/delete), #214, #215 | `UserManagement.vue`, `UserDetailsDialog.vue`, `userManagementHelpers.ts`, `endpoints/users.py`, `crud/user.py`, datetime call sites listed in #214 | none |
| **F gene catalogue** | Sonnet | #220 (frontend), #222, #224 | `GeneCatalogueView.vue`, `GeneCatalogueView.utils.ts`, `stores/geneCatalogue.ts`, `GenesTable.vue` + `AddGeneModal.vue` (after C1/C2 merged) | D2, C1, C2 |

**Merge point 2** merges in this order: H, G, B, C2, E2, F.

### Wave 2: foundation, run sequentially because these are sweeps

1. **#164 Vuetify 4** (if confirmed). Codex astra, then an Opus visual pass over every page as admin and as a
   curator.
2. **DS theme.** Sonnet with the `impeccable` skill. Issues #261, #254, #255, #253, #179, #251 (one
   classification mark component). The spec is the "Visual rules" section of
   `docs/design/redesign-2026-10/README.md`.
3. **Sweeps.** Haiku or Sonnet, one PR each:
   - #249: one ConfirmDialog replaces `window.confirm`.
   - #257: one date/empty formatter.
   - #258: naming.
   - #180: loading must not show fake values.
   - #190: FAQ/About copy.
   - #260
   - #248 follow-ups
4. **Perf.** Codex astra: #172, #173, #176, #177, #178, #182, #66 (if it was not closed).

### Out of scope this session

- **Wave 3, redesign screens:** #272 shell, then #275 table, then #277, #278, #279, #280, #281, #276, #273,
  #274, #259 and the polish issues they absorb (#200–#206, #223, #228, #230, #233, #244, #245).
- **Wave 4, config architecture:** epic #264 (#265–#271, #282, #284, #216, #218, #219).
- **Owner input needed:** #102, #104, #105, #115, #116, #30, #46, #86, #109.

## 6. Brief template (written by script to `$SCR/$WS.brief.md`)

```
You are implementer <WS> on Gene Curator, worktree <WT>, branch <BRANCH>. Ponytail full: smallest complete change.
Read AGENTS.md first. Rules: <section 4 verbatim>.
Owned files (edit only these + new tests next to them): <list>.
Issues, in this order (bodies below; acceptance criteria are the spec): <list>.
When done: make check passes, push, open a DRAFT PR to master, reply with the 15-line report.
<issue bodies appended by the script>
```

## 7. Merge-point protocol (orchestrator)

1. **Ownership check:** for each PR, `gh pr diff N --name-only` against the ownership table. Send any stray file
   back to the implementer.
2. **Review:** one `model: opus` agent per PR runs `ponytail:ponytail-review` on `gh pr diff N` plus the issue
   acceptance criteria. It returns `SHIP` or at most 5 `FIX` findings with file:line. Run the reviews in
   parallel.
3. **Fixes:** send findings to the same implementer (SendMessage to the agent, or re-run Codex with the findings
   appended to the brief). Trivial fixes go to Haiku.
4. **Merge, in the order given for each wave:**
   - Rebase on master (Haiku).
   - `make check`; add `make test-postgres` when SQL is touched.
   - `gh pr ready`, wait for the `CI gate`, then `gh pr merge --merge --delete-branch`.
   - Remove the worktree.
5. **After each merge point:** apply new migrations to the dev DB (`make db-migrate`, which runs all files once
   #158 is in) and restart the backend. One Sonnet agent smoke-tests the touched routes on 5193 with Playwright,
   as admin, curator and reviewer, and reports regressions only.
6. **Bookkeeping:** check that `Closes` keywords closed the issues. Comment on partials with what remains.

## 8. Token discipline

- Never read issue bodies, source or full diffs yourself. Scripts build briefs; agents return at most 15 lines;
  reviewers return verdicts.
- Keep at most 6 implementers running at once. Wait for notifications; never poll.
- Send each correction once, with everything in it. Do not iterate in small messages.
- Reuse running agents (SendMessage) for their own fixes instead of spawning new ones.

## 9. End-of-session report

Give a table of issues closed, partial and not started, with PR links. List the gates run per PR. List the
follow-ups collected from reports, filed as new issues by Haiku only if they are real defects. Then write the
next-session prompt for Wave 3 in the same format as this file.
