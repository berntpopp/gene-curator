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
  min_share of proband points and one of them appears in 2+ scoring probands.
- L6 (owner, 2026-10-31): 4-eyes refusals return 403 when the actor may not act (own work, disease corrector) and 409
  when the workflow state forbids it; tests and views updated (fix/l6-review-status-codes).

## Releases

- v0.12.0: [#588](https://github.com/berntpopp/gene-curator/pull/588), notes `docs/releases/v0.12.0.md` (signed tag v0.12.0 on d602d747, published).

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
  [#589](https://github.com/berntpopp/gene-curator/pull/589). Left: B20 (follow-up); L6 fixed after the release (403/409).
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

## Open issue triage (2026-10-31, after v0.12.0 and #592)

All 7 open issues are in Wave 11; the goal is zero open feature issues and an empty follow-up list (v1.0.0).

| Issue | State | Wave 11 | Size | Kidney |
|---|---|---|---|---|
| #591 move curations to a new methodology version | none yet | W11A | M | yes (#439 changes) |
| #105 adopt ClinGen | schema guidance only | W11B: adopted marker + bulk adopt, no fetch | M | yes (#439 step 0, ~60% of top tier) |
| #593 provenance (sources, agent attribution) | humans and LLM runs covered; agents and sources not | W11C | M | yes (export) |
| #282 admin builders | point model and fields done | W11D: table builders incl. workflow stages, nested groups, and-conditions, import diff; canvas per Step 0 | L | low |
| #284 granular permissions | delete slice, review roles done | W11E: allowed pairs + capability matrix per Step 0 | L | medium |
| #447 segregation by family/method | step rule only | W11F per Step 0 | L | low (KGDB uses LOD step) |
| #276 catalogue matrix | sticky column, Disagreements done | W11G: drag reorder, With results, server-saved view | S/M | low |

KGDB side (berntpopp/kidney-genetics-db, not this wave): #472 key fix, #448 import, #473 susceptibility, #474 diagnostics.

## Wave 11 prompt

```text
You are the Wave 11 orchestrator for Gene Curator (/home/bernt-popp/development/gene-curator, GitHub
berntpopp/gene-curator, master at v0.12.0 plus #592). Goal: finish development. Every open issue ends closed by a
merged PR or an owner won't-do, every follow-up below is fixed or ticketed, and the wave ships v1.0.0 (or v0.13.0 per
Step 0). Ponytail full for you and every agent: smallest complete change, deletion beats addition. Orchestrate only:
dispatch, review, merge, release; agents report in 15 lines; you do not pull source files or full diffs into your
context. Do not park fixable items as "owner decision" when the right answer is clear; fix them in this wave.

Read first (only these): .planning/waves/wave10/WAVE10-REPORT.md (triage, follow-ups), docs/releases/v0.12.0.md,
.planning/orchestration/rules.md, issues #591 #105 #593 #282 #284 #447 #276 with comments (gh issue view --comments); #593 and the #105
design comment hold the researched standards (GA4GH VA-Spec, ClinGen SEPIO roles, PROV-O, ID formats) to implement.

## Step 0: owner decisions (one AskUserQuestion, max 4 questions, recommended option first)
1. Release: v1.0.0 feature-complete (Recommended) / v0.13.0.
2. #284: allowed pairs plus the full capability matrix with scope-owned methodologies and workflows (Recommended) /
   allowed pairs only, close the rest won't-do.
3. #282 canvas: drop it; close #282 after the table builders (Recommended) / build the canvas too.
4. #447: build SOP v11 family/method-aware segregation (pp.28-35, Figure 6) with a clinical spec agent reading the
   PDF first (Recommended) / close won't-do (the step rule stays).
Already decided, do not ask: L6 done (#592); allowed pairs yes; #105 = adopted marker + bulk adopt, no fetch
(GeneFoundry rule); #591 and #593 as their issues say; per-row import diff yes. Record answers at the top of
WAVE11-REPORT.md. Ask nothing else.

## Step 1: workstreams (two batches; migrations fixed up front, an unused number stays unused)
Batch 1 (start together):
| WS | Scope | Owns | Mig | Review |
|---|---|---|---|---|
| W11A version move #591 | admin Move to version per schema: dry run (fields kept/dropped, new required empty, old->new score/class), apply in one transaction, rescore, audit per row, active curation whose class changes or misses a required field goes back to review; REST, /mcp/full, Schema Management dialog | new services/version_move.py, endpoint, MCP tool, dialog component | 078 | full Opus, Postgres test as app_user |
| W11B ClinGen adoption #105 | adopted marker storing the GeneFoundry clingen_get_gene_validity fields verbatim (cggv_id, permalink, classification, moi, mondo, expert_panel, classified_date, retrieved_at, record_sha256, citation; see the #105 design comment); bulk adopt API + MCP with the same rows, checked against the entity (gene, MONDO, MOI) and the schema's classes, creating curations in review with the #105 auto comment; reviewer confirms (4-eyes); badge "Adopted from ClinGen" with the permalink; export as a VA-Spec-style statement (reportedIn the CGGV permalink; contributions: GCEP organization, curator, approver); never fetch | new services/clingen_adoption.py, endpoint, MCP tool, badge component, export additive | 079 | full Opus, Postgres test |
| W11C provenance #593 | follow the standards in #593 (GA4GH VA-Spec 1.0 Contribution/Agent/Document/EvidenceLine, ClinGen SEPIO contributory roles, PROV-O SoftwareAgent): `source` field type (kind pmid/doi/clinvar/clingen_allele/clingen_validity/url/database, id validated per kind, url, title, retrieved_at, tool, record_sha256, citation verbatim from GeneFoundry) as cell and list, optional direction supports/disputes/neutral; contributions {agent person/organization/software, SEPIO activityType, date} per curation and evidence row; MCP write tools accept an optional agent block {model, agent, tools_used} stored in audit change_metadata, client-reported, on behalf of the token's user; software never counts for 4-eyes; row added/changed by in UI; export contributions[] and sources[] in VA-Spec field names with a JSON Schema snapshot; new KGDB and ClinGen bundle versions with source cells (frozen ids untouched) | core field-type validator, mcp/audit.py additive, history UI, bundle files, docs/EXPORT.md | 080 | full Opus, Postgres test |
| W11D builders #282 | workflow-stage builder (table view), nested groups and plain objects, and-conditions in the row-rule UI, per-row import diff, Tests from Preview widgets, schema save conflict (409 on stale lock_version) and validate-unsaved-draft endpoint, required_when cross-check, URL max_length enforced, Text/String and Choice duplicates merged | components/schema-editor/*, SchemaManagement.vue import dialog, crud/schema_repository.py, endpoints/validation.py, core/schema_rules.py | 081 | full Opus |
| W11H follow-ups | every "This wave" and carried item in WAVE10-REPORT.md Follow-ups not owned above: B20, B21, R3-1, R3-2, due_date in My work, removed-user invite message, trimmed-length messages, test-order flake, corrector plus real reviewer test, hotspot group_by, point_model.py docstring, matrix labels from the pinned version, signed-out gene 404, anonymous export methodology.version, MCP instructions under 4096, #587 skipped polish (import file chooser, resolve flags genes already in scope, phone empty state) | those files only; one commit per item | none | quick delta |
Batch 2 (start each as soon as batch 1 merges free the files; B2 rebases on batch 1):
| W11E permissions #284 | allowed pairs per scope (picker lists only allowed, create refuses others); per Step 0 the capability matrix as data, owner_scope_id on methodologies, versions and workflows, every write endpoint via require(...), capability x role API tests, RLS matches the matrix | core/capabilities.py, deps, scope schemas, endpoints (additive require lines), RLS migration | 082 | full Opus, Postgres lane |
| W11F segregation #447 (if yes) | first a clinical spec agent writes .planning/waves/wave11/SEGREGATION-SPEC.md from the SOP v11 PDF (eligibility, inheritance, methods, published vs estimated LOD, summed eligible-family LOD, method weighting, worked examples); orchestrator checks it; then the engine rule, family table in the ClinGen bundle as a new version, per-family rationale, save/preview parity; old pins never rescored | scoring/point_model.py rule, ClinGen bundle, tests | 083 | full Opus + clinical check against the PDF |
| W11G catalogue #276 | drag reorder columns, With results preset, server-saved view per user | catalogue view/store, user prefs endpoint | 084 | quick delta |

Rules for agents (in every brief via setup.sh): as in Wave 10. One worktree each via .planning/orchestration/setup.sh,
setups one after another, no backticks in double-quoted notes, local npm ci (never symlink node_modules). Backend gates
need SECRET_KEY=x DATABASE_URL=postgresql://u:p@localhost/x. Failing test first. Any change to RLS, triggers, workflow
transitions, saves or permissions adds a backend/tests/postgres/ test of the real API flow as app_user. make ci
(unique PGTEST_PORT per agent) and make diff-cover before ready; pgrep -c -f '^make (ci|test-postgres)' under 2 first.
Draft PRs; never continue-on-error, || true, .skip; make api-types after schema changes. D1: nobody approves their own
work; 4-eyes refusals are 403 (actor) / 409 (state). Stay in owned files; shared files get additive edits only.
Literature, variant and ClinGen lookups stay in GeneFoundry; Gene Curator records and checks, never fetches.

## Step 2: machine safety
At most 5 implementers, at most 2 heavy gates at once. Poll at 60 s.

## Step 3: review and merge
ponytail:ponytail-review on every PR (full Opus for A-G, quick delta for H and fix rounds); must-fix goes back to the
same agent. One serial merge loop (.planning/orchestration/merge.sh N); if it reports no CI run on the head, watch the
run and merge by hand when green and behind_by is 0. Stop the loop on a must-fix (TaskStop + gh pr ready --undo).
Checkpoint make ci on fresh master after each batch.

## Step 4: verify end to end (finish line)
Fresh stack (.planning/orchestration/monkey-stack.sh up origin/master; 5455/8052/5190; never 5454/8051/5193). UI tester
and API/MCP tester in parallel, findings via Bash heredoc:
- KGDB journey: import bundle, intake 10 genes, bulk adopt 5 ClinGen-curated kidney genes (tester looks them up with
  GeneFoundry clingen_get_gene_validity), curate 3 Mendelian and 1 Susceptibility with source cells (ClinVar, PMID,
  DOI), an MCP-written curation with an agent block visible in history, two-reviewer approval, version move with an
  active curation, export checked against docs/schemas/kidney-genetics/README.md.
- Permissions: viewer, curator, reviewer, scope admin of own and other scope, platform admin on the key writes.
- Builders: workflow-stage builder, nested groups, and-conditions, import diff, two admins editing one schema (409).
- Segregation (if built): the SOP worked examples score as the spec says.
- Forms at 390 px; second approval activating a curation; review through MCP.
UI tester also rates UX as a senior product designer per flow (score, top friction); then one impeccable polish PR
from the findings and reviews; then a narrow re-check of exactly those findings. Repeat fix + re-check until no
critical/high/medium remains.

## Step 5: release and report
release/v1.0.0 (or v0.13.0): notes (every claim cites a merged PR, fact-checked), README and docs current (EXPORT.md,
METHODOLOGY-IMPORT.md, POINT-MODEL.md, a short curator and admin guide), version bump in every file holding 0.12.0
(not history). Merge, git pull, confirm HEAD is the release merge, signed tag, gh release create --verify-tag. Cleanup
worktrees and branches (GitHub API). WAVE11-REPORT.md: owner decisions, issues, migrations, reviews, monkey and UX
scores, KGDB readiness, remaining follow-ups (target: none), and a maintenance-mode prompt if anything is left.
Comment the release on kidney-genetics-db #448 with the export changes (adoption, sources, agent).

Out of scope: KGDB repo work (#472, #448, #473, #474 run there), GeneFoundry ops.
End every reply with what you skipped or did not check, in one line.
```
