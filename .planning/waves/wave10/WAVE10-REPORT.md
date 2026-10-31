# Wave 10 report

## Owner decisions (2026-10-30)

Step 0 is answered; do not ask again.

- #558 export evidence, scores, summary: configurable per scope. New scope setting (migration 076), off by default:
  off means scope members only and anonymous rows keep today's fields; on exposes the new fields to anonymous callers
  for that public scope.
- #453 legacy disease gaps: scope admins correct the disease entity through an audited correction (migration 077 if
  needed).
- Closed #466, #278 (done) and #104 (covered by FAQ.vue).
- Wave 10 also takes #276 small part (sticky gene column, Disagreements preset), #216 polish and #218 (scope roles in
  User Management).
- Mid-wave: Wave 10 also delivers full KGDB readiness end to end (no Wave 11): KGDB genes fully curatable, the KGDB
  schema buildable in the UI without raw JSON and importable through the API. Gap analysis in KGDB-READINESS.md;
  workstreams W10F onwards; monkey test and v0.12.0 release follow after them.
- KGDB owner decisions (2026-10-30): susceptibility uses a second workflow pair the curator picks by hand (no
  routing code); the KGDB bundle reaches databases by API import only (no SQL seed); draft-4 row rules become native
  point-model rules (points_when, step); methodology import is platform-admin only (UI, REST, /mcp/full, not core /mcp).
- Step 4 addition (owner): the UI monkey test also rates the user experience as a senior product designer (KGDB schema
  builder, import, curation flow, intake, roles), then improvements are made with the impeccable skill based on the
  monkey findings and the review, followed by a narrow re-check.
- Orchestrator call (monkey round 1): the hotspot review flag means recurrence: the top max_variants variants carry at least
  min_share of proband points and one of them appears in 2+ scoring probands. L6 (400 vs 403/409 for 4-eyes refusals) left as
  is pending an owner decision; 12 tests and several views depend on 400.

## Releases

- v0.12.0: [#588](https://github.com/berntpopp/gene-curator/pull/588), notes `docs/releases/v0.12.0.md` (tag pending owner go).

## Issues

| Status | Issue | PR |
|---|---|---|
| Closed | #558 export evidence, scores, summary (scope setting) | [#570](https://github.com/berntpopp/gene-curator/pull/570) |
| Closed | #374 AccessTokens title, #86 backup script | [#571](https://github.com/berntpopp/gene-curator/pull/571), partial files [#585](https://github.com/berntpopp/gene-curator/pull/585) |
| Closed | #216 workflow management polish | [#571](https://github.com/berntpopp/gene-curator/pull/571), [#587](https://github.com/berntpopp/gene-curator/pull/587) |
| Closed | #559 configurable reviewer flags | [#572](https://github.com/berntpopp/gene-curator/pull/572), [#584](https://github.com/berntpopp/gene-curator/pull/584), recurrence [#585](https://github.com/berntpopp/gene-curator/pull/585) |
| Closed | #281 intake due dates and curator pick, #218 scope roles in User Management | [#573](https://github.com/berntpopp/gene-curator/pull/573), [#587](https://github.com/berntpopp/gene-curator/pull/587) |
| Closed | #567 one open precuration per entity, #453 audited disease correction | [#574](https://github.com/berntpopp/gene-curator/pull/574), index [#585](https://github.com/berntpopp/gene-curator/pull/585) |
| Closed | #577 list cells | [#578](https://github.com/berntpopp/gene-curator/pull/578) |
| Closed | #219 schema field editor, preview, Advanced JSON, Publish version | [#580](https://github.com/berntpopp/gene-curator/pull/580) |
| Closed | #576 native row rules, step rule, cross-checks | [#582](https://github.com/berntpopp/gene-curator/pull/582) |
| Closed | #575 methodology import (backend, REST, /mcp/full; UI button) | [#579](https://github.com/berntpopp/gene-curator/pull/579), [#581](https://github.com/berntpopp/gene-curator/pull/581) |
| Partial | #282 point-model builder and import UI; form/workflow builders and canvas remain | [#581](https://github.com/berntpopp/gene-curator/pull/581) |
| Partial | #284 delete slice (creator or scope admin) | [#574](https://github.com/berntpopp/gene-curator/pull/574) |
| Partial | #105 `classification_source` guidance, no take-over | [#571](https://github.com/berntpopp/gene-curator/pull/571) |
| Partial | #276 sticky gene column, Disagreements chip | [#571](https://github.com/berntpopp/gene-curator/pull/571), [#587](https://github.com/berntpopp/gene-curator/pull/587) |
| Refs | #447 step rule only; family/method-aware segregation remains | [#582](https://github.com/berntpopp/gene-curator/pull/582) |
| Done | KGDB methodology bundle (KGDB #439) | [#583](https://github.com/berntpopp/gene-curator/pull/583) |
| Done | monkey round 1 API (13) and UI (22) findings | [#585](https://github.com/berntpopp/gene-curator/pull/585), [#586](https://github.com/berntpopp/gene-curator/pull/586) |
| Done | UX polish from the monkey rating and POLISH-LIST | [#587](https://github.com/berntpopp/gene-curator/pull/587) |
| Done | monkey round 2 fixes: R2-1 to R2-8, M4 and B6 rest, B13; `corrected_disease` on curation detail; `due_date` typed date | [#589](https://github.com/berntpopp/gene-curator/pull/589) |

## Migrations

076 `export_evidence_public` (scope setting, off by default); 077 partial unique index
`uq_precurations_open_entity` on (gene_id, scope_id, entity_key) for open statuses; stops with the duplicate ids and the
query that lists them, deletes nothing. Next free number: 078.

## Reviews

Every PR got a `ponytail:ponytail-review`. Must-fix items caught before merge:
- #570: docs promised free-text fields would be hidden; the setting could be turned on with a token.
- #572: band flags fired on empty drafts (noise at 0 points); reviewer page did not show the warnings.
- #573: removed members still listed; due dates shifted one day west of UTC.
- #574: unsaved edits lost when the correction saved; D1 hole: the corrector could peer-review their own correction.
- #579: UI edits to a schema not yet published were overwritten by import; inactive schemas matched by name.
- #580: new fields invisible in tabbed layouts; renames left references in scoring and validation rules.
- #581: clearing one range bound cleared both; numeric option values turned into strings.
- #582: duplicate rows scored; a rule overwrote points the curator entered.
- #583: compound-het with blank phase scored; invented susceptibility tiering now marked provisional; KGDB contract keys,
  `mane_status` blanks and a `url` `max_length` claim GC does not enforce.
- #585: hotspot meant "few variants" instead of recurrence (owner semantics now in POINT-MODEL.md).
- #586: KGDB tables rendered as JSON on the detail page; comma splitting broke URLs with commas.

## Monkey results

- Round 1 API/MCP (fresh stack on 14753262): 13 findings, high 1 (#567 race: parallel creates by different curators
  all passed), medium 4 (export bypass via token flip to public, summaries without a class, hotspot noise, due_date
  dropped on create), low 8. Fixed in [#585](https://github.com/berntpopp/gene-curator/pull/585) except L3 (done in
  #587), L6 (by design) and L8 (noted).
- Round 1 UI: 22 findings, critical 1 (KGDB curation detail crashed, so no reviewer could approve), high 5 (blank
  points scored 0, UI-built sectioned schemas never scored, Susceptibility pair unreachable, duplicate refusal generic,
  user search broken), medium 8, low 8. Fixed in [#586](https://github.com/berntpopp/gene-curator/pull/586) and
  [#587](https://github.com/berntpopp/gene-curator/pull/587), except B20 and B21.
- Round 2 (narrow re-check on afba66c4): 28 fixed, 2 partial (M4 bulk onto an existing gene, B6 cleared search),
  3 still broken (B13 red errors on an untouched precuration, B20, L6 by design), 2 not re-tested (B9, B16). New: 8
  (medium 2: R2-1 cleared search keeps the filter, R2-3 score panel hidden until the first edit; low 6: R2-2, R2-4
  "SOP v11" label on KGDB, R2-5 corrector not told why, R2-6 Escape opens discard, R2-7 raw enums and "none" cells,
  R2-8 validation box on a duplicate draft). KGDB import, flows and the two-reviewer approval pass end to end.
- Round 2 fixes: R2-1 to R2-8, the M4 and B6 rest and B13 fixed in
  [#589](https://github.com/berntpopp/gene-curator/pull/589). Left: B20 (follow-up), L6 (owner decision).
- Round 3 (narrow re-check on ab07af6a, MONKEY-R3.md): 9 of 11 fixed, 2 mostly fixed; Escape in dialogs keeps the form.
  New: R3-1, R3-2 (low). Not checked: second approval activating WT1, phone width of KGDB forms.
- UX scores (senior product designer), R1 -> R2: schema builder 4 -> 7, import 7 -> 8, KGDB curation 3 -> 7, intake
  7 -> 8, User Management 6 -> 7, catalogue/phone 7 -> 8.

## KGDB readiness

Works end to end (round 2): import the bundle in the UI or REST (dry run, idempotent re-import, new version on change,
blocked broken bundle); intake with curator and due date; Mendelian and Susceptibility precurations with the pair picked
by hand; curation with native rules (de novo 1.5, blank points default, compound het phase, recurrent-variant cap, LOD
step), list cells, diagnostics; review flags; disease correction; two-reviewer approval with the corrector blocked;
export with evidence, scores and diagnostics for a member token. Building a KGDB-like schema in the UI needs no JSON.

Open KGDB questions: susceptibility tiering (points, thresholds, protective alleles) and a class for refuted risk
alleles; `verified_via`, `detectability_note` and resource `country_or_scope` are not in KGDB's `Diagnostics`
(extra=forbid). KGDB sync: kidney-genetics-db #448 (import exports as drafts) open, #437 closed; KGDB must add
`relationship_type` to `uq_gda_gene_disease_moi`, pin the contract and map the frozen field ids.

## Follow-ups

Carried from Wave 9 (still open):
- Anonymous export callers get `methodology.version` null and never see archived rows.
- MCP server instructions at the 4096-character limit.
- Matrix class labels come from the live schema of each scope's default pair, not the pinned version.
- Signed-out gene page logs a 404 for genes with no public curation.
- `make llm-eval` not re-run (no OpenRouter key).
- Orchestration: `merge.sh` missed an in-progress CI run again on #570; watch the run.
- GeneFoundry public `/mcp` returns 403 (ops). Fleet release-control ledger expires about 2027-01-26.
- Regenerate `.planning/codebase` with `/gsd-map-codebase`. Claude.ai connector over MCP OAuth untested.

This wave:
- Scope allowed-pairs list: the precuration picker lists all pairs and create accepts any schema id.
- Schema editor is last writer wins; no validate-unsaved-draft endpoint.
- Nested groups and plain objects only in Advanced JSON; `and` conditions only in the Code view.
- B20 reviewer-visible LLM setting (AI second view link with AI off); B21 stale-session 401s on load.
- L6 status codes for 4-eyes refusals (400 vs 403/409): owner decision.
- URL `max_length` not enforced; hotspot `group_by` assumes the variant field; `required_when` targets not cross-checked.
- Test-order flake: `test_review_assignment` after `test_workflow_config`.
- Missing test: corrector plus a real reviewer both approve.
- Invite of a removed user says "already a member".
- `due_date` missing from My work API rows.
- Per-row import diff; trimmed-length messages everywhere.
- R3-1: the MONDO picker shows "MONDO disease is required" before any input on an untouched precuration.
- R3-2: a nested select (diagnostics `mane_status`) shows the raw value, not the label, in Evidence changes.
- Not checked in round 3: second approval activating WT1; phone width of KGDB forms.
- `scoring/point_model.py` module docstring (~13-14) still says the first rule wins and omits `present`;
  a 0-point rule always wins and other rules fill only blank points (#582).
- Skipped polish from #587: Tests still need hand-written evidence JSON; Create stays on the list; Text/String and
  Single choice/Choice (enum) duplicates; raw OS file chooser for import; resolve step does not flag genes already in
  scope; phone empty state off-screen in the catalogue.
- #105, #276, #284, #282 and #447 remainders.

## Open issue triage (2026-10-31, master ab07af6a)

| Issue | Verdict | Size | Kidney |
|---|---|---|---|
| #282 admin builders | partial; point-model builder done; form layout/workflow builders and canvas remain | L | low |
| #284 granular permissions | partial; delete slice done; allowed-pairs list and capability checks remain | M+L | medium (allowed pairs) |
| #105 adopt ClinGen | partial; schema guidance only; native take-over marker (no fetch, GeneFoundry rule) | S/M | yes (#439 step 0) |
| #276 catalogue matrix | partial; drag reorder and server-saved view remain | S/M | low |
| #447 segregation by family/method | step rule shipped; clinical design (SOP v11 pp.28-35) still needed | L | medium |

## Wave 11 prompt

```text
You are the Wave 11 orchestrator for Gene Curator (/home/bernt-popp/development/gene-curator, GitHub
berntpopp/gene-curator, master at v0.12.0). Ponytail full for you and every agent: smallest complete change, deletion
beats addition. Orchestrate only: dispatch, review, merge, release; agents report in 15 lines; you do not pull source
files or full diffs into your context.

Read first (only these): .planning/waves/wave10/WAVE10-REPORT.md (triage table, follow-ups),
.planning/waves/wave10/MONKEY-R2.md, docs/releases/v0.12.0.md, .planning/orchestration/rules.md.

## Step 0: owner decisions (one AskUserQuestion, max 4 questions, recommended option first)
1. L6: 4-eyes refusals stay 400 (Recommended) / move to 403 (self-approval) and 409 (state), updating tests and views.
2. Allowed pairs: a per-scope list of allowed workflow pairs; create refuses others (Recommended) / keep any pair.
3. #105 take-over: a marker field and help text in the KGDB/ClinGen schemas, no fetch (Recommended) / leave open.
4. Per-row import diff: build it in W11C (Recommended) / drop it.
Record the answers at the top of WAVE11-REPORT.md. Ask nothing else.

## Step 1: workstreams (parallel, disjoint files, migration numbers fixed up front; next free is 078)
| WS | Scope | Owns | Migration | Review |
|---|---|---|---|---|
| W11A pairs | allowed-pairs list per Step 0; picker lists only allowed pairs; precuration create refuses another schema id | scope model/schemas/endpoint for the list, crud/precuration.py create check, PrecurationFormView pair picker | 078 | full Opus, Postgres test as app_user |
| W11B schema editor safety | schema save conflict (lock_version or updated_at check, 409), validate-unsaved-draft endpoint used by the editor, required_when cross-check, URL max_length enforced | crud/schema_repository.py, endpoints/validation.py, core/schema_rules.py, SchemaEditor.vue save path | 079 if lock_version | full Opus |
| W11C builder rest | nested groups and plain objects in the field editor, and-conditions in the row-rule UI, per-row import diff, Tests from the Preview widgets | components/schema-editor/*, SchemaManagement.vue import dialog | none | full Opus |
| W11D small | B20 reviewer-visible LLM flag, B21 auth bootstrap 401s, due_date in My work rows, removed-user invite message, trimmed-length messages, test-order flake, corrector plus real reviewer test, hotspot group_by docs | those files only | none | quick delta |

Rules for agents (put them in every brief via setup.sh): as in Wave 10. One worktree each via
.planning/orchestration/setup.sh, run setups one after another, no backticks in double-quoted notes. Backend gates
need SECRET_KEY=x DATABASE_URL=postgresql://u:p@localhost/x. Failing test first. Any change to RLS, triggers,
workflow transitions, saves or permissions adds a backend/tests/postgres/ test of the real API flow as app_user.
make ci (includes test-postgres, unique PGTEST_PORT per agent) and make diff-cover before ready; pgrep -c -f
'^make (ci|test-postgres)' under 2 first. Draft PRs; never continue-on-error, || true, .skip; make api-types after
schema changes. D1: nobody approves their own work. Stay in owned files; shared files get additive edits only.

## Step 2: machine safety
At most 4 implementers, at most 2 heavy gates at once. Poll at 60 s.

## Step 3: review and merge
ponytail:ponytail-review on every PR (full Opus for A-C, quick delta for D and fix rounds); must-fix goes back to the
same agent. One serial merge loop (.planning/orchestration/merge.sh N). If merge.sh reports no CI run on the head,
watch the run and merge by hand when green and behind_by is 0 (it missed one on #570). Checkpoint make ci on fresh
master in its own worktree after the last feature merge.

## Step 4: verify end to end
Fresh-stack monkey test (.planning/orchestration/monkey-stack.sh up origin/master; 5455/8052/5190), UI and API/MCP
testers in parallel: allowed pairs, concurrent schema edits (two admins), validate unsaved draft, builder nested groups
and and-conditions, import diff, B20, approvals_require_session and review through MCP (not tested in
Wave 10), forms at 390 px. One fix PR per tester, then a narrow re-check of exactly those findings.

## Step 5: release v0.13.0 and report
release/v0.13.0: notes (every claim cites a merged PR, fact-checked), README upgrade, version bump in every file holding
0.12.0 (not history), docs/EXPORT.md current. Merge, then git pull and confirm HEAD is the release merge before the
signed tag; gh release create --verify-tag. Cleanup worktrees and branches (GitHub API). WAVE11-REPORT.md as in Wave
10, carrying the follow-ups listed in WAVE10-REPORT.md that remain open.

Out of scope unless the owner says otherwise: #447 clinical design, #284 capability checks beyond allowed pairs, #282
canvas, KGDB repo work (#448 runs there in parallel).
End every reply with what you skipped or did not check, in one line.
```
