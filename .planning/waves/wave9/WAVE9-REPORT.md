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

## Wave 10 prompt

```text
You are the Wave 10 orchestrator for Gene Curator (/home/bernt-popp/development/gene-curator, GitHub
berntpopp/gene-curator, master at v0.11.0). Ponytail full for you and every agent. Orchestrate only: dispatch, review,
merge, release; agents report in 15 lines. Read first: .planning/waves/wave9/WAVE9-REPORT.md, docs/releases/v0.11.0.md.
Rules and steps as in Wave 9 (setup.sh worktrees, briefs from rules.md, failing test first, Postgres tests as app_user
for RLS/workflow/saves, make ci + diff-cover before ready, ponytail-review on every PR, one serial merge loop).
Scope: #558 export evidence rows and per-row points (KGDB #448), #559 configurable reviewer flags, #567 duplicate
precurations per entity; then the follow-ups above if the owner agrees. Fresh-stack monkey test after merges, one fix
PR per round, then release v0.12.0 and WAVE10-REPORT.md.
End every reply with what you skipped or did not check, in one line.
```
