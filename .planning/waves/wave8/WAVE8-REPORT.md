# Wave 8 report

## Owner decisions (2026-10-30)

- LLM second view (#464/#465): real eval. Provider not named; orchestrator default Anthropic `claude-sonnet-5-5`,
  key entered via the admin LLM console at the Step 4 eval (no key in the orchestrator env). Tests use MockProvider.
- MCP OAuth 2.1/DCR: Claude Code + Claude.ai; PATs kept alongside.
- Rate limiting: per-worker buckets documented as a known limit; drop the unused curator tier.
- Evidence-item endpoints: remove now. PAT self-list/revoke: keep.
- The real eval ran through OpenRouter (`openai_compatible`, `anthropic/claude-sonnet-5.5`) because the owner supplied an OpenRouter key; no Anthropic key was used.

## Releases

- v0.10.0: [#542](https://github.com/berntpopp/gene-curator/pull/542), notes `docs/releases/v0.10.0.md`.
- v0.10.1: release branch `release/v0.10.1` (this PR), notes `docs/releases/v0.10.1.md`.

## Issues

| Status | Issue | PR |
|---|---|---|
| Closed | #462 MCP OAuth 2.1 + DCR (phase 2) | [#528](https://github.com/berntpopp/gene-curator/pull/528) |
| Closed | #465 advocate vs skeptic | [#529](https://github.com/berntpopp/gene-curator/pull/529) |
| Closed | #496 recompute for every engine | [#527](https://github.com/berntpopp/gene-curator/pull/527) |
| Closed | #277 My work, #273 palette classification | [#525](https://github.com/berntpopp/gene-curator/pull/525) |
| Closed | #530 split disease entities | [#537](https://github.com/berntpopp/gene-curator/pull/537), [#541](https://github.com/berntpopp/gene-curator/pull/541), [#543](https://github.com/berntpopp/gene-curator/pull/543) |
| Closed | #531 MOI XL / Undetermined (migration 070) | [#545](https://github.com/berntpopp/gene-curator/pull/545) |
| Closed | #532 export of reviewed curations | [#547](https://github.com/berntpopp/gene-curator/pull/547) |
| Closed | #535 require_variant | [#544](https://github.com/berntpopp/gene-curator/pull/544) |
| Closed | #538 url fields | [#548](https://github.com/berntpopp/gene-curator/pull/548) |
| Partial | #464 blind skeptic (no auto-queue on submit) | [#529](https://github.com/berntpopp/gene-curator/pull/529) |
| Partial | #278 curation workspace (flagged rows excluded) | [#527](https://github.com/berntpopp/gene-curator/pull/527) |
| Partial | #539 parts a+b (schema verdicts, MONDO susceptibility); relationship type and vocabulary open | [#546](https://github.com/berntpopp/gene-curator/pull/546) |
| Partial | #466 epic MCP + LLM second view | #526, #528, #529 |
| Not started | #533 curator/final classification, #534 LLM runs drop custom-schema fields | - |
| Out of scope | #447 #453 #282 #284 #216 #218 #219 #86 #104 #105 | - |

## Gates per PR (from each PR body)

| PR | Title | Gates stated |
|---|---|---|
| #524 | Wave 8 small items | targeted pytest (+ postgres direct add), `make check`, `make ci` (incl. test-postgres, diff-cover) |
| #525 | W8E My work, palette, direct add UI | `make check`; `make ci` (two runs, port clash; test-postgres/ci-frontend/ci-repo/diff-cover re-run on 55475); `make test-postgres`; diff-cover 100% / 95% |
| #526 | MCP leaner output | targeted MCP pytest, `make check`, `make ci`, diff-cover 100%, `make test-postgres` |
| #527 | engine recompute, evidence endpoints removed | `make check`, `make ci`, `make test-postgres`, diff-cover 100%; re-run after review and rebase; `make api-types` no diff |
| #528 | MCP OAuth 2.1 + DCR | `make check`, `make ci` (incl. test-postgres, diff-cover 93% / 100%), `make api-types` |
| #529 | LLM skeptic + advocate | `make check`, `make ci` (incl. test-postgres, diff-cover 99% / 94%) after rebase |
| #536 | monkey round 1 fixes | targeted pytest + Vitest, `make check`, `make ci` (55479, incl. test-postgres), diff-cover 100% / 92% |
| #537 | split disease entities | `make check`, `make ci` (55478, incl. test-postgres, diff-cover 100%) |
| #540 | logger foreign loop | targeted pytest (`-W error`), `make check`, `make ci` (55481, incl. test-postgres), diff-cover 100% |
| #541 | monkey round 2 fixes | `make ci` (55480, incl. test-postgres, diff-cover 98% / 100%), `make check` |
| #542 | release v0.10.0 | `uv sync --frozen`, local `npm ci`, `uv lock --check`, `make check`, `make ci` (55482, diff-cover 100%) |
| #543 | monkey round 3 fixes | targeted pytest + Vitest, `make check`, `make ci` (55483, incl. test-postgres), diff-cover 100% / 97% |
| #544 | require_variant | targeted pytest, `make ci` (55484, incl. test-postgres), diff-cover 100% |
| #545 | MOI XL / Undetermined | `make ci` (55485, incl. test-postgres), diff-cover no coverable lines |
| #546 | schema verdicts, MONDO susceptibility | targeted pytest (313), `make check`, `make ci` (55487, incl. test-postgres), diff-cover 100% |
| #547 | export | `make ci` (55486, all lanes incl. test-postgres, api-types-check, zizmor), diff-cover 100% |
| #548 | url fields | targeted pytest + Vitest, `make ci` (55484, incl. test-postgres), diff-cover 90% / 91% |
| #549 | leave guard and status after approval | targeted Vitest, `make check`; comment: `make ci` (55488, incl. test-postgres), diff-cover 100% |
| this PR | release v0.10.1 | see the PR body |

## Monkey results

- Round 1 ([#536](https://github.com/berntpopp/gene-curator/pull/536)): LLM prompt missed disease/MONDO/MOI from the nested shape; two parallel second views could both queue; failed reruns hid status; HTML-escaped prompt data mangled `c.1000C>T`; MockProvider output did not match the schema; My work offered "Start precuration" for a gene someone else started; ScorePanel reasons, audit-trail 404, revoke label, 422 logged as database error; 068 MONDO lookup on seeded schemas.
- Round 2 ([#541](https://github.com/berntpopp/gene-curator/pull/541)): RLS defeated the reviewer `FOR UPDATE` lock (advisory lock instead); empty proposals failed mock runs; gene page conflict banner, scope count, MOI labels; several-entity palette cap and entity chooser; legacy blocker message; 069 XLD = HP:0001423.
- Round 3 ([#543](https://github.com/berntpopp/gene-curator/pull/543)): database logging never wrote to `system_logs`; entity choice on a plain new curation; second-view links for reviewers; leave prompt on untouched forms; raw UUID in the approval notice; MCP `curation_created: false` wording.
- Chrome pass on master f2a3138d ([#549](https://github.com/berntpopp/gene-curator/pull/549), W8L): add-then-delete of a table row prompted "Leave without saving?"; the precuration form had no leave guard, so an unsaved MONDO pick could be lost; the header said Submitted after approval. The Unsaved changes label on untouched new forms is unchanged (#470 pending).

## Real LLM eval

OpenRouter `anthropic/claude-sonnet-5.5`. `make llm-eval` on the synthetic golden cases: skeptic 1/4 and
advocate 2/4 agreement. A real second view on VHL took 12.6-13.4 s. Total spend about 0.18 USD.

## Follow-ups

- `asyncio.run` in sync services: `publication_service.py`, `ontology_service.py`, `gene_verification.py`, `api/v1/endpoints/scopes.py` (#540 only made the logger safe).
- Second view auto-queue on submit (#464).
- Legacy open curations without an entity link do not appear in the entity chooser.
- Curation evidence can change `mondo_id` after creation, so `entity_key` can drift from the evidence.
- The export page scans all visible rows.
- Rate limiting is off by default.
- #533, #534 and the rest of #539 (relationship type, classification vocabulary) with owner defaults.
- "Unsaved changes" label: owner decision pending.
- Model ids for `openai_compatible` providers are not checked for pinning.
- Export known limits: anonymous `methodology.version` null; soft-deleted curations show as archived with `archived_at` null for members; a required url of only spaces passes.
- GeneFoundry public `/mcp` returns 403 (ops).
- Fleet release-control ledger expires about 2027-01-26: commit a fresh control-audit artifact to genefoundry-router and re-pin the fleet before then.
- Regenerate `.planning/codebase` with `/gsd-map-codebase`.
- Claude.ai custom connector over MCP OAuth not tested (needs a public HTTPS URL; owner deferred, no tunnel).

## Wave 9 prompt

```text
You are the Wave 9 orchestrator for Gene Curator (/home/bernt-popp/development/gene-curator, GitHub berntpopp/gene-curator,
master at v0.10.1). Ponytail full for you and every agent: smallest complete change, deletion beats addition, no
speculative abstractions. Orchestrate only: you dispatch, review, merge, release. You write no product code and do not
pull source files, issue bodies or full diffs into your own context; agents do that and report in 15 lines.

Read first (only these): `.planning/waves/wave8/WAVE8-REPORT.md`, `.planning/waves/wave8/WAVE8-PROMPT.md` (rules and
steps carry over unless this prompt says otherwise), `docs/releases/v0.10.1.md`.

## Step 0: owner decisions (one AskUserQuestion, max 4 questions, recommended option first)
1. #533 final classification: curator-set final classification next to the computed verdict, published and exported,
   reviewer must confirm (Recommended) / computed verdict only, documented.
2. #539 rest: `relationship_type` on the entity (disease, risk, susceptibility) plus a schema-defined classification
   vocabulary (Recommended) / relationship type only.
3. #534 LLM fields: build the prompt from the schema's field definitions so custom and derived schemas keep every
   field (Recommended) / refuse runs on schemas the prompt cannot map.
4. "Unsaved changes" label and second-view auto-queue on submit (#464): keep the label, auto-queue behind a scope
   setting that defaults off (Recommended) / no auto-queue.
Record the answers at the top of WAVE9-REPORT.md. Do not ask anything else; pick sensible defaults and say so.

## Step 1: workstreams (dispatch in parallel; file ownership is disjoint; migration numbers fixed up front)
| WS | Scope | Owns | Migration | Review |
|---|---|---|---|---|
| W9A classification | #533 final classification (model, API, UI, export field, MCP) with D1 and the 4-eyes rule | curation endpoints/schemas for the field, export crud/schema, curation UI | 071 | full Opus, Postgres tests as app_user |
| W9B entity | #539 rest: relationship type, schema classification vocabulary; `entity_key` drift when evidence changes `mondo_id` | precuration/entity code, `database/sql/072_*` | 072 | full Opus |
| W9C llm | #534 schema-driven prompt fields; #464 auto-queue on submit per Step 0; pinning check for `openai_compatible` model ids; re-run `make llm-eval` and report agreement | `app/services/llm*`, LLM admin UI | none | full Opus |
| W9D async | remove `asyncio.run` from sync services (`publication_service.py`, `ontology_service.py`, `gene_verification.py`, `scopes.py`): async endpoints or sync clients, one approach throughout | those services and their callers | none | full Opus |
| W9E small | legacy open curations without entity link in the chooser; export: required url of only spaces fails, soft-deleted rows excluded, anonymous `methodology.version`; rate limiting default decision documented | chooser UI, `core/schema_rules.py`, `crud/curation_export.py` | none | quick delta |

Rules for agents (put them in every brief via setup.sh):
- One worktree each: `.planning/orchestration/setup.sh WS BRANCH "OWNS" "ISSUES" "NOTE"`, run setups one after another;
  no backticks inside double-quoted notes. First command: `cd backend && uv sync --extra dev --frozen`. Backend gates
  need `SECRET_KEY=x DATABASE_URL=postgresql://u:p@localhost/x`.
- Fix bugs with a failing test first. Any change to RLS, triggers, auth/OAuth, saves, workflow transitions or
  lock_version adds a `backend/tests/postgres/` test of the real API flow as app_user.
- Before pushing: `make ci` (includes `make test-postgres`) and `make diff-cover` (changed lines >= 90%); check
  `pgrep -c -f '^make (ci|test-postgres)'` first and wait while it reports 2 or more. Report exactly which gates ran.
- Open DRAFT PRs; mark ready only when local CI is green. Never `continue-on-error`, `|| true`, `.skip`; never
  Prettier `api.generated.ts`; regenerate types with `make api-types`.
- Secrets (PATs, OAuth tokens and client secrets, LLM keys) never reach the browser or logs; a test asserts it.
- Stay in your owned files. If you must touch another stream's file, stop and report instead.
- Every PR gets a `ponytail:ponytail-review` before merge; merges run serially with
  `set -o pipefail; .planning/orchestration/merge.sh N | tail` in one loop ending `echo ALL-DONE`, never red.

## Step 2: machine safety
At most 5 implementers, at most 2 heavy gates at once (`pgrep -c -f '^make (ci|test-postgres)'`). Poll at 60 s.

## Step 3: review and merge
Order: W9E -> W9D -> W9C -> W9B -> W9A. `ponytail:ponytail-review` full Opus for W9A-W9D, quick delta for W9E and fix
rounds. Serial merge loop with `.planning/orchestration/merge.sh N`, ending `echo ALL-DONE`. Checkpoint `make ci` and
`make test-postgres` on fresh master after W9D and after W9A.

## Step 4: verify end to end
Fresh-stack monkey test (`.planning/orchestration/monkey-stack.sh up origin/master`, ports 5455/8052/5190) early, after
W9D merges, and again before the release: every role, final classification with review, a susceptibility entity,
export as anonymous and as member, LLM second view (MockProvider and one real run), D1 on every route. Then a Chrome
pass on the real UI. Claude.ai custom connector over MCP OAuth against a public HTTPS URL (tunnel or staging host;
ask the owner for it). One fix PR per round.

## Step 5: release v0.11.0 and report
`release/v0.11.0`: release notes (every claim cites a merged PR, fact-checked with `gh pr view`), README upgrade
section (`make db-migrate` 071-072), version bump in every file holding `0.10.1`. Quick review, merge, signed tag,
`gh release create`. Cleanup worktrees and branches. WAVE9-REPORT.md as in Wave 8, carrying: GeneFoundry public `/mcp`
403 (ops), fleet release-control ledger expiry about 2027-01-26 (fresh control-audit artifact in genefoundry-router,
re-pin the fleet), `.planning/codebase` regeneration (/gsd-map-codebase).

Out of scope unless the owner says otherwise: #447, #453, #282, #284, #216, #218, #219, #86, #104, #105.
End every reply with what you skipped or did not check, in one line.
```
