# Wave 9 report

## Owner decisions (2026-10-30)

Step 0 is answered; do not ask again.

- #533 final classification: the curator proposes `curator_classification`, and a rationale is required when it differs
  from `computed_verdict`. Stored in columns and audited. Every approving reviewer confirms it; a reviewer who
  disagrees uses request changes. Catalogue and export expose `final_classification`; `computed_verdict` is unchanged.
- #534 LLM fields: per-field `llm_share` in `field_definitions`, false by default for new fields, refused on curator
  judgement keys (points, score status, rationale, impact, replication, summaries). Shared keys = `SHARED_EVIDENCE_KEYS`
  plus flagged fields, so seeded schemas need no data migration. Schema validation warns when a derived schema adds
  fields that are not shared.
- #539 rest: `relationship_type` (mendelian | susceptibility, default mendelian) on precuration and curation. It is part
  of `entity_key`, suffixed only when not Mendelian, so existing keys stay unchanged. Also a schema-defined
  classification vocabulary. Built after #533.
- "Unsaved changes" on never-saved new forms: keep (#470/#477).
- Undated model ids for `openai_compatible` providers: keep accepting them (runs record model id and prompt version).
  Only `anthropic` kind requires pinned ids.
- #464 auto-queue on submit: Step 0 default (scope setting, off by default).
- Mid-wave (after the kidney-genetics readiness review): build #560, #556, #557 in this wave; #558 and #559 in Wave 10.
- Monkey findings: fix all, including the lows.

## Releases

- v0.11.0: [#564](https://github.com/berntpopp/gene-curator/pull/564), notes `docs/releases/v0.11.0.md`.

## Issues

| Status | Issue | PR |
|---|---|---|
| Closed | #533 curator/final classification | [#555](https://github.com/berntpopp/gene-curator/pull/555) |
| Closed | #534 llm_share, #464 auto second view on submit | [#553](https://github.com/berntpopp/gene-curator/pull/553), nested fields [#563](https://github.com/berntpopp/gene-curator/pull/563) |
| Closed | #539 relationship type, classification vocabulary, entity_key drift | [#554](https://github.com/berntpopp/gene-curator/pull/554), Standard_Precuration [#566](https://github.com/berntpopp/gene-curator/pull/566) |
| Closed | #556 band section minimum, #557 per-variant cap | [#561](https://github.com/berntpopp/gene-curator/pull/561) |
| Closed | #560 approvals only from a signed-in person | [#562](https://github.com/berntpopp/gene-curator/pull/562), member gates [#563](https://github.com/berntpopp/gene-curator/pull/563), reactivation [#565](https://github.com/berntpopp/gene-curator/pull/565) |
| Done | asyncio.run removed from sync paths (`core/async_bridge.py`) | [#552](https://github.com/berntpopp/gene-curator/pull/552) |
| Done | legacy chooser rows, url of spaces, soft delete archives the active pointer, deleted rows exported as archived with `archive_reason`, rate-limit docs | [#551](https://github.com/berntpopp/gene-curator/pull/551) |
| Open (Wave 10) | #558 evidence rows in export, #559 configurable reviewer flags, #567 duplicate precurations per entity | - |

Migrations: 071 curator classification, 072 relationship type, 073 auto second view, 074 approvals_require_session,
075 relationship type on Standard_Precuration.

## Reviews

Every PR got a `ponytail:ponytail-review`. Must-fix items caught before merge: soft delete left the active pointer live
(#551); `run_blocking` ran sync DB work on the main loop (#552); `llm_share: false` could not withhold a seeded key and
name collisions shared unflagged fields (#553); labels stored instead of class keys, engine fallback refused
qualitative classes, SQL vs Python key mismatch (#555); create bypassed the drift guard, relationship_type disagreed with
the key, catalogue filter missing, frontend/backend key normalisation and case duplicates (#554); a scope-admin token
could mint its own signed-in reviewer (#562); token reactivation of members (#565).

## Monkey results

- Round 1 (fresh stack on 8c3fbddd), API/MCP: nested `llm_share` fields never reached the provider (high); member
  removal bypassed the session gate; custom section totals read as 0/null; matrix filter showed the wrong cell; HPO
  validation did not follow the OLS redirect; rationale message said "(none)"; `/workflow/configuration` stub claimed
  saves; catalogue summary ignored filters. Fixed in [#563](https://github.com/berntpopp/gene-curator/pull/563) and
  [#565](https://github.com/berntpopp/gene-curator/pull/565).
- Round 1, UI: Mendelian and susceptibility entities looked identical (high); seeded Kidney Genetics scope had no
  relationship type; re-curation dropped the proposed class; generic Submit blocker; client-side rationale check;
  checklist reset; one-char chips; band wording; "not in scope" and slug labels; workload counts. Fixed in
  [#566](https://github.com/berntpopp/gene-curator/pull/566).
- Round 2: API 8/8 and UI 10/10 pass. New: #567 (pre-existing since #530).

## Kidney-genetics readiness

Comments on berntpopp/kidney-genetics-db#439 (scoring; fields, workflow and agents), #448 and #437 (export contract).
After v0.11.0 the kidney methodology can be configured and curated in GC end to end. Still open for KGDB: #558 (import as
drafts), #559 (reviewer flags), hand-entered rules (draft segregation table, de novo +0.5, unknown phase, duplicates
across papers), and KGDB's own sync (#437) absorbing the v0.11.0 contract changes in `docs/EXPORT.md`.

## Follow-ups

- #558, #559, #567.
- Anonymous export callers get `methodology.version` null and never see archived rows (retraction needs a member token
  or a periodic full sync).
- MCP server instructions are at the 4096-character limit; MCP tool list budget raised to 36,000 bytes.
- Matrix class labels come from the live schema of each scope's default pair, not the pinned version.
- No `llm_share` toggle in the schema editor (JSON only).
- Signed-out gene page logs a 404 for genes with no public curation (page handles it).
- `make llm-eval` not re-run (no OpenRouter key in the orchestrator env).
- Orchestration: chained merge waiters that `pgrep -f merge.sh` match their own command line; run merges in one serial
  loop. `merge.sh` misses an in-progress CI run right after update-branch; re-run or watch the run.
- GeneFoundry public `/mcp` returns 403 (ops).
- Fleet release-control ledger expires about 2027-01-26: commit a fresh control-audit artifact to genefoundry-router and
  re-pin the fleet before then.
- Regenerate `.planning/codebase` with `/gsd-map-codebase`.
- Claude.ai custom connector over MCP OAuth still untested (needs a public HTTPS URL).

## Open issue triage (2026-10-30, master v0.11.0)

| Issue | Verdict | Size | Kidney |
|---|---|---|---|
| #466 epic MCP + LLM second view | done, closable (#462/#489/#464/#465 closed) | - | yes, shipped |
| #278 curation workspace | done, closable | - | yes, shipped |
| #374 UI leftovers | one gap: `views/AccessTokens.vue:5` h1 lacks `page-title` | S | no |
| #104 instructions | `FAQ.vue` covers the flow; owner call | S | low |
| #558 export evidence/scores/summary | not started; raw rows would be public for public scopes | S | high (KGDB #448) |
| #559 reviewer flags | not started; pass model into `evidence_warnings` (`evidence_lint.py:102`) | M | yes (#439) |
| #567 duplicate precurations | not started; helper in `crud/precuration_entity.py`, no migration | S | yes (integrity) |
| #284 granular permissions | partial; `delete_precuration` lets any curator archive another's draft (S); rest L, split | S+L | indirect |
| #281 scope page / intake | partial; `due_date` in summary, curator picker in paste dialog, delete `AddGeneModal.vue` | M | medium |
| #218 scope roles in User Management | partial; backend exists, UI missing | M | low-medium |
| #276 catalogue matrix | partial; sticky gene column, Disagreements preset (S); reorder + server-saved view later | S/M | low |
| #216 workflow management polish | partial; static stage grid, fixed version, duplicate-pair warning, links | S | no |
| #105 adopt ClinGen | partial; schema route works; marker field + help text, no fetch (GeneFoundry rule) | S | yes (#439 step 0) |
| #86 backup | partial; `make db-backup` exists; script with integrity check + retention, README restore | S | prod |
| #453 legacy disease gaps | partial; needs owner decision who corrects | M | low |
| #447 segregation by family/method | not started; needs clinical design (SOP v11 pp.28-35) | L | medium |
| #282 admin builders, #219 schema field editor | not started | L | no |

## Wave 10 prompt

```text
You are the Wave 10 orchestrator for Gene Curator (/home/bernt-popp/development/gene-curator, GitHub
berntpopp/gene-curator, master at v0.11.0). Ponytail full for you and every agent: smallest complete change, deletion
beats addition. Orchestrate only: dispatch, review, merge, release; agents report in 15 lines; you do not pull source
files or full diffs into your context.

Read first (only these): .planning/waves/wave9/WAVE9-REPORT.md (triage table, follow-ups), docs/releases/v0.11.0.md,
.planning/orchestration/rules.md.

## Step 0: owner decisions (one AskUserQuestion, max 4 questions, recommended option first)
1. #558 export evidence: members only, anonymous rows keep today's fields (Recommended) / public for public scopes.
2. #453 legacy disease gaps: scope admins correct the disease entity through an audited correction (Recommended) /
   close as won't fix (legacy only).
3. Close #466, #278 now and #104 as covered by the FAQ (Recommended) / keep #104 open with named topics.
4. Wave 10 also takes #276 small part, #216 and #218 (Recommended) / kidney items only.
Record the answers at the top of WAVE10-REPORT.md. Ask nothing else.

## Step 1: workstreams (parallel, disjoint files, migration numbers fixed up front; next free is 076)
| WS | Scope | Owns | Migration | Review |
|---|---|---|---|---|
| W10A export | #558 evidence, scores, summary in the export per Step 0; docs/EXPORT.md; test that row points sum into the trace | schemas/curation_export.py, crud/curation_export.py, docs/EXPORT.md | none | full Opus, privacy focus, Postgres test anonymous vs member |
| W10B flags | #559 configurable reviewer flags (band margin, experimental > genetic, recurrent-variant hotspot reusing the #557 group walk); validator | scoring/evidence_lint.py, scoring/point_model.py, core/schema_rules.py point-model part, ScoreTrace/ScorePanel display | none | full Opus |
| W10C integrity | #567 one open precuration per gene, scope and entity (409 naming it); #284 slice: delete_precuration only by creator or scope admin; #453 per Step 0 | crud/precuration_entity.py, crud/precuration.py create path, endpoints/precurations.py delete, disease-gap correction path | 076 only if #453 needs it | full Opus, Postgres tests as app_user |
| W10D intake | #281 rest: due_date in GeneScopeAssignmentSummary + Due column + bulk due date, curator picker in PasteGenesDialog via /gene-assignments/bulk, delete AddGeneModal.vue; #218 scope roles column + editor in User Management (existing direct add) | scope gene list/intake components, schemas/gene_assignment.py, UserManagement.vue | none | full Opus |
| W10E small | #374 AccessTokens h1 class; #86 scripts/backup.sh (pg_dump, pg_restore --list check, retention) + README restore, db-backup removes partial file; #105 classification_source schema field guidance (no fetch); #276 sticky gene column + Disagreements preset; #216 polish | those files only | none | quick delta |

Rules for agents (put them in every brief via setup.sh): as in Wave 9. One worktree each via
.planning/orchestration/setup.sh, run setups one after another, no backticks in double-quoted notes. Backend gates
need SECRET_KEY=x DATABASE_URL=postgresql://u:p@localhost/x. Failing test first. Any change to RLS, triggers,
workflow transitions, saves or permissions adds a backend/tests/postgres/ test of the real API flow as app_user.
make ci (includes test-postgres, unique PGTEST_PORT per agent) and make diff-cover before ready; pgrep -c -f
'^make (ci|test-postgres)' under 2 first. Draft PRs; never continue-on-error, || true, .skip; make api-types after
schema changes. Secrets never reach the browser or logs. Stay in owned files; shared files get additive edits only.

## Step 2: machine safety
At most 5 implementers, at most 2 heavy gates at once. Poll at 60 s.

## Step 3: review and merge
ponytail:ponytail-review on every PR (full Opus for A-D, quick delta for E and fix rounds); must-fix goes back to the
same agent. Review may run while GitHub CI runs; stop the merge on a must-fix. One serial merge loop
(.planning/orchestration/merge.sh N, never chained pgrep waiters). If merge.sh reports no CI run on the head, watch the
run and merge by hand when green and behind_by is 0. Checkpoint make ci on fresh master in its own worktree after the
last feature merge.

## Step 4: verify end to end
Fresh-stack monkey test (.planning/orchestration/monkey-stack.sh up origin/master; 5455/8052/5190) with two testers in
parallel: UI (Playwright: intake with due dates and assignment, scope roles from User Management, reviewer flags in the
score panel, duplicate precuration refused, catalogue sticky column) and API/MCP (export evidence anonymous vs member,
flags on a kidney-like schema, #567 and delete permissions via token and MCP, backup script on the monkey DB). Genes
split A-M / N-Z. One fix PR per tester, then a narrow re-check of exactly those findings.

## Step 5: release v0.12.0 and report
release/v0.12.0: notes (every claim cites a merged PR, fact-checked), README upgrade, version bump in every file holding
0.11.0 (not history), docs/EXPORT.md current. Merge, then git pull and confirm HEAD is the release merge before the
signed tag; gh release create --verify-tag. Cleanup worktrees and branches (GitHub API). WAVE10-REPORT.md as in Wave 9,
carrying the follow-ups listed in WAVE9-REPORT.md that remain open.

Out of scope unless the owner says otherwise: #282, #219, #447, #284 beyond the delete slice.
End every reply with what you skipped or did not check, in one line.
```
