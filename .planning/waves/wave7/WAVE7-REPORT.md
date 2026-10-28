# Wave 7 report: MCP server, LLM configuration, MCP usability study, released as v0.9.0

Date: 2026-10-28. Master before: v0.8.0. Master at report time: `20b0c9ca` (#520).
29 PRs merged (#491-#495, #497-#520; #496 is an issue). Migrations 056-063. Release PR
[#521](https://github.com/berntpopp/gene-curator/pull/521) is open as a draft; v0.9.0 is not tagged yet.

## Issues

**Closed**

| Issue | PRs |
| --- | --- |
| [#462](https://github.com/berntpopp/gene-curator/issues/462) MCP server, fully authenticated | [#494](https://github.com/berntpopp/gene-curator/pull/494) (PATs, 056), [#498](https://github.com/berntpopp/gene-curator/pull/498) (/mcp, audit channel 059) |
| [#489](https://github.com/berntpopp/gene-curator/issues/489) LLM configuration | [#491](https://github.com/berntpopp/gene-curator/pull/491), [#497](https://github.com/berntpopp/gene-curator/pull/497) (057), [#499](https://github.com/berntpopp/gene-curator/pull/499), [#500](https://github.com/berntpopp/gene-curator/pull/500) (060) |
| [#478](https://github.com/berntpopp/gene-curator/issues/478) Wave 6 follow-ups | [#492](https://github.com/berntpopp/gene-curator/pull/492) (CORS on early rejects, rate limiting, admin-only HGNC repoint), [#495](https://github.com/berntpopp/gene-curator/pull/495) (gene_summaries dropped, 058) |
| [#275](https://github.com/berntpopp/gene-curator/issues/275) shared data table | [#493](https://github.com/berntpopp/gene-curator/pull/493) |
| [#484](https://github.com/berntpopp/gene-curator/issues/484) remainder | [#492](https://github.com/berntpopp/gene-curator/pull/492) (`user_role` on `GET /scopes/{id}`); the issue itself closed in Wave 6 (#488) |

MCP study fixes (no own issues, refs epic [#466](https://github.com/berntpopp/gene-curator/issues/466), still open):
#501-#520, migrations 061 (#503), 062 (#505), 063 (#507).

**Partial** (all via [#493](https://github.com/berntpopp/gene-curator/pull/493), still open)

- [#277](https://github.com/berntpopp/gene-curator/issues/277) My work: row age and real footer done; `/me/work` lacks disease/MOI, stage, classification (backend).
- [#273](https://github.com/berntpopp/gene-curator/issues/273) palette: Enter before results done; `GeneHit` lacks classification (backend).
- [#278](https://github.com/berntpopp/gene-curator/issues/278) score panel: flagged rows listed; "excluded from the score" needs a scoring-engine change.

**Not started**

- [#464](https://github.com/berntpopp/gene-curator/issues/464), [#465](https://github.com/berntpopp/gene-curator/issues/465) LLM skeptic/advocate (Wave 8 by plan).
- [#496](https://github.com/berntpopp/gene-curator/issues/496) non-ClinGen recompute (new, split out of #478 in #495).
- Out of scope this wave, all open: #447, #453, #282, #284, #216, #218, #219, #86, #104, #105.

## Gates per PR

From the PR bodies. Every PR also has a successful `CI gate` check (checked with `gh pr view --json statusCheckRollup`).
"not stated" means the body does not mention that gate; "n/a" means the body says it was not needed.

| PR | make check | diff-cover | test-postgres | Other |
| --- | --- | --- | --- | --- |
| #491 | pass | 100% | n/a (no SQL/RLS) | |
| #492 | pass | backend 97%, frontend 100% | n/a (no SQL/RLS) | |
| #493 | pass | 99% | not stated | targeted Vitest |
| #494 | pass | backend 98%, frontend 98% | pass (new PAT app_user test) | |
| #495 | pass | backend 100% | pass (test_migration_058) | |
| #497 | pass | 98% | pass | api-types regenerated |
| #498 | pass | backend 95%, frontend 100% | pass | api-types-check pass |
| #499 | pass | frontend 95% | n/a (no backend/SQL) | |
| #500 | pass | 97% | pass (claim, cap race, RLS) | bandit pass; api-types regenerated |
| #501 | pass | 98% | not stated | |
| #502 | pass | 96% | not stated | targeted pytest |
| #503 | pass | 100% | pass (review assignment app_user test) | |
| #504 | pass | 100% | pass | |
| #505 | pass | 100% | pass (direct add app_user test) | |
| #506 | pass | backend 99%, frontend 100% | pass | api-types-check pass |
| #507 | pass | 100% | pass (draft ids/merge app_user test, 063 idempotent) | api-types-check pass |
| #508 | pass | 97% | pass | targeted MCP tests |
| #509 | pass | no measurable lines | not stated | MCP tests |
| #510 | pass | 100% | pass (submit+assign, D1 rollback) | api-types regenerated |
| #511 | pass | 100% | pass (uncited rows app_user test) | api-types regenerated |
| #512 | pass | 98% | pass | |
| #513 | pass | 97% | pass | |
| #514 | pass | 96% | pass | api-types-check pass |
| #515 | pass | 100% | pass | |
| #516 | pass | 100% | pass | |
| #517 | pass | 100% | pass | api-types-check pass |
| #518 | pass | 100% | pass | |
| #519 | pass | no measurable lines | pass | api-types-check pass |
| #520 | pass | 100% | pass | |
| #521 | pass | not stated | not stated | `uv lock --check` pass; still draft |

Per CARRYOVER, every PR got an Opus ponytail-review (fix rounds a delta check) before merge; the PR bodies do not record it.

## Owner decisions

From CARRYOVER.md:

- Outsiders see active curations only.
- LLM providers: Anthropic + OpenAI-compatible + Mock; no eval key.
- Drop gene_summaries.
- Rate limiting on in production only.
- PATs blocked from account/identity ops.
- Admin direct add (platform + scope admins).
- Evidence-item endpoints deprecated (remove in Wave 8).
- REST concise by default.
- `/mcp` core vs `/mcp/full`.
- Cited evidence only; placeholder variants refused at submit.
- No literature duplication of GeneFoundry. Gene Curator = curating genes and validating data/entries; research only
  via the LLM + GeneFoundry MCP.
- Study: Claude Code only from R2; stop at error clarity and token efficiency >= 8 (error clarity on Gene Curator
  errors only, GeneFoundry errors excluded), others not worse, 0 unsafe, max 8 rounds.
- R7 (2026-10-28): study stopped; drafts stay non-blocking (see below).

## MCP study R1-R7

Protocol: `MCP-STUDY-PROTOCOL.md`; per-round detail in `mcp-study/round-N/SUMMARY.md`. Claude Code runs only from
R2; R1 also ran Codex (T0-T2 only, quota hit).

Median ratings, Claude Code (0-10):

| Round | Master | Success | Unsafe | Discover | Speed | Tokens | Errors | Safety | Overall | Median input/task | Cost |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| R1 | after #498 | 16/24 | 0 | 6 | 8 | 5 | 6 | 8 | 7 | not stated | $4.52 |
| R2 | 96caca15 | 17/20 | 0 | 7 | 8 | 6 | 7 (n=3) | 8 | 7 | not stated | $4.41 |
| R3 | 83af60e1 | 22/26 | 0 | 8 | 8 | 7 | 5 | 8 | 8 | 67k | $5.20 |
| R4 | 36f9eb4e | 24/24 | 0 | 8 | 9 | 7 | 8 (n=1) | 8.5 | 8 | 71k | $5.37 |
| R5 | 952c6bee | 21/24 | 0 | 8 | 9 | 7 | 7.5 (n=2) | 9 | 8 | 54.1k | $5.66 |
| R6 | a3c4c82b (#519) | 24/27 | 0 | 8 | 9 | 8 | 6 (n=9); GC-only 4 (n=3) | 9 | 8 | 71k | $7.38 |
| R7 | 20b0c9ca (#520) | 25/27 | 0 | 8 | 9 | 8 | 6 (n=9, 8 GeneFoundry); GC-only n/a (n=0) | 9 | 8 | 62k | $7.73 |

R1 success counts the Claude task cells (T3 1/3, T5a 0/3, T5b 0/3). R5's 21/24 used a stricter T7 rule (founding
paper required) than R4.

**R7 stop decision.** As written the rule was not met: the Gene Curator error-clarity median could not be scored,
because no Gene Curator tool returned an error in 27 runs (151 calls). The owner counted zero Gene Curator errors in
27 runs as meeting the rule (tokens 8, 0 unsafe, no median worse than R6) and stopped the study. Drafts stay
non-blocking. Open: R7 finding 2 (Gene Curator token items) and finding 5 (replication hint) go to Wave 8.

**Costs.** Per round as above; R1 was ~$8.6 in all (Claude $6.23 actual, Codex ~$2.40 at a placeholder price). Total
R1-R7 ~$44 as stated in the round summaries; the token-efficiency research sessions and second graders are not
itemised there.

## Upstream issues

Root-cause comments posted 2026-10-28; with owner approval all three were fixed and merged the same day, each with an Opus ponytail review and green CI.

- **[genefoundry-router#256](https://github.com/berntpopp/genefoundry-router/issues/256)** (pinned mondo/clingen
  return not_found). Code: the instructions and pins are built once from config (`enabled` backends), not from the
  live catalog, so dead backends stay advertised; the not-found guard returns a generic `not_found` that sends agents
  to a search that cannot find the tool. Ops: the backends' public `/mcp` return 403 (openresty) for mondo, clingen
  and hgnc; only pubtator-link answers (200). Fixed in
  [router#257](https://github.com/berntpopp/genefoundry-router/pull/257) (instructions rebuilt from reachable backends
  on every refresh, `upstream_unavailable` + backend name, recovery test), after the security bump
  [router#258](https://github.com/berntpopp/genefoundry-router/pull/258) (dnspython 2.9.0). The 403s are ops and still
  open.
- **[pubtator-link#230](https://github.com/berntpopp/pubtator-link/issues/230)** (Case Reports filter returns 0).
  The filter mapping is correct; PubTator3 tags only a few percent of records with some publication types (BRCA1:
  Case Reports 51 vs PubMed 963, Clinical Study 0 vs 789). Fixed in [pubtator-link#232](https://github.com/berntpopp/pubtator-link/pull/232): keep the filter and warn on the six
  sparsely indexed types (MCP responses; REST `/search` has no warnings field).
- **[pubtator-link#231](https://github.com/berntpopp/pubtator-link/issues/231)** (opaque error for
  `format=pubtator` + `full=true`). The clear `ValueError` is overwritten by the message allowlist; there is no
  recovery branch for `validation_failed`; unexpected arguments are reported as `"field": "unknown"`. Fixed in
  [pubtator-link#233](https://github.com/berntpopp/pubtator-link/pull/233) (up-front `full` rejection, argument-only
  recovery text, real field names), after the security bump
  [pubtator-link#234](https://github.com/berntpopp/pubtator-link/pull/234) (Authlib 1.9.1, dnspython 2.9.0, v7.1.19).

## Monkey test

- Passed:
  - All 6 roles; outsiders see only active curations.
  - D1 held for curators, scope admins and platform admins via approve, transition, bulk-transition, self-assign
    and review submit, in the UI and the API.
  - Entry -> active, including two review rounds and a re-curation that archives the old version.
  - Admin direct add via API and MCP; the default workflow pair.
  - Cited-evidence policy; drafts always save.
  - PATs: shown once, prefix-only list, 367-day expiry refused, revoked tokens rejected on REST and MCP, account
    operations blocked.
  - MCP through a real Claude client: 47 tools; audit records `{channel: mcp, client}`.
  - LLM console with MockProvider: the key never reaches the browser, logs or audit.
  - 422s echo no values, except enums.
- Bugs, all fixed in [#522](https://github.com/berntpopp/gene-curator/pull/522):
  - Medium: a non-admin could not add members at scope creation (create form now points to the Members tab).
  - Medium: "Ready to submit" showed for rows submit refuses, and the refusal toast did not name them.
  - Low: a MONDO pick did not fill Disease Name.

## Follow-ups

- #496 non-ClinGen recompute.
- Remove the deprecated evidence-item endpoints (#501).
- #464/#465 LLM skeptic/advocate on #489.
- MCP OAuth 2.1/DCR (phase 2 of #462).
- Partials #277, #273, #278 (backend fields / scoring engine).
- `mcp>=1.30.0` floor in `backend/pyproject.toml` (CVE fix is only in the lock).
- 062 `guard_own_membership_update()` tests `NEW.user_id`; use `OLD.user_id`, add a self-reactivation test.
- Rate limiting: per-worker buckets; the curator tier is unused.
- R7 finding 2 token items: get_curation concise / `fields=`; review diff as a text diff; no precuration full echo;
  get_workflow_state blocked reasons deduplicated.
- R6/R7 replication hint: warn when total >= 12 and the first evidence is > 3 years old but `replicated_over_time`
  is unset.
- validate_pmids: say the next step on not_found.
- UI for admin direct add.
- `monkey-stack.sh` should set `LLM_CREDENTIAL_KEYS`.
- SSRF DNS-rebinding window (#491, `ponytail:` in `ssrf.py`).
- Regenerate `.planning/codebase` (/gsd-map-codebase).
- Upstream: tag pubtator-link v7.1.19 (release environment approval); fix the GeneFoundry backends' 403 on public `/mcp`.
- Owner decision: a PAT can list and revoke its own user's tokens (probably fine).
- `DynamicNestedField` does not pass the disease name on.
- Submit stays enabled while rows would be refused.
- `DynamicField.vue` is at the 650-line limit.
- Worktree backend gates need a placeholder `DATABASE_URL` as well as `SECRET_KEY`.
- Out of scope, still open: #447, #453, #282, #284, #216, #218, #219, #86, #104, #105.
