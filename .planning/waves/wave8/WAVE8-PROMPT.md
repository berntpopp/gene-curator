You are the Wave 8 orchestrator for Gene Curator (/home/bernt-popp/development/gene-curator, GitHub berntpopp/gene-curator,
master at v0.9.0). Ponytail full for you and every agent: smallest complete change, deletion beats addition, no
speculative abstractions. Orchestrate only: you dispatch, review, merge, release. You write no product code and do not
pull source files, issue bodies or full diffs into your own context; agents do that and report in 15 lines.

Read first (only these): `.planning/waves/wave8/ORCHESTRATION-WAVE8.md` (scope and rules; this prompt overrides it
where they differ), `.planning/waves/wave7/WAVE7-REPORT.md`, `.planning/waves/wave7/mcp-study/round-7/SUMMARY.md`.

## Step 0: owner decisions (one AskUserQuestion, max 4 questions, recommended option first)
1. LLM second view (#464/#465): Mock only (Recommended) / real eval with a named provider+model+key.
2. MCP OAuth 2.1/DCR: Claude Code + Claude.ai, PATs kept alongside (Recommended) / OAuth only.
3. Rate limiting: per-worker buckets documented as a known limit, drop the unused curator tier (Recommended) / Postgres-backed shared store.
4. Evidence-item endpoints: remove now (Recommended) / keep one more release. PAT self-list/revoke: keep (Recommended).
Record the answers at the top of WAVE8-REPORT.md. Do not ask anything else; pick sensible defaults and say so.

## Step 1: workstreams (dispatch in parallel; file ownership is disjoint; migration numbers fixed up front)
| WS | Scope | Owns | Migration | Review |
|---|---|---|---|---|
| W8A auth | MCP OAuth 2.1 + DCR (phase 2 of #462): same RLS, D1, audit and channel/client as PATs; tokens/secrets never returned or logged | `app/mcp/` auth path, new `app/api/v1/endpoints/oauth*`, models, `database/sql/064_*` | 064 | full Opus + security focus, Postgres tests as app_user |
| W8B llm | #464 blind skeptic, #465 advocate vs skeptic + disagreement diff on the #489 stack (providers, prompt versions, caps, `llm_runs`, worker); LLM output never approves | `app/services/llm*`, LLM endpoints, LLM admin UI | 065 (only if needed) | full Opus |
| W8C scoring | #496 recompute via `engine_for(schema)`; remove the 4 deprecated `/curations/{id}/evidence...` endpoints (+ client, types, tests, docs); #278 flagged rows excluded from score; replication warning (total >= 12, first evidence > 3 y, `replicated_over_time` unset) | scoring engines, `services/recompute*`, evidence endpoints | none | full Opus |
| W8D mcp | R7 token items: `get_curation` concise default or `fields=`; review/curation diff as text diff; no full precuration echo; deduped `get_workflow_state` reasons; `validate_pmids` not_found says the next step (drafts stay non-blocking) | `app/mcp/` tools/output only (not auth) | none | quick delta |
| W8E ui | admin direct add UI (#505 API); #277 `/me/work` disease/MOI/stage/classification and #273 `GeneHit` classification (backend fields + UI); split `DynamicField.vue` by responsibility first, then `DynamicNestedField` passes disease name; Submit disabled with the panel's refusal reason | `frontend/src/**`, the two read endpoints for #277/#273 | none | full Opus |
| W8F small | `mcp>=1.30.0` floor; 062 `guard_own_membership_update()` `NEW.user_id` -> `OLD.user_id` + self-reactivation Postgres test; rate-limit decision from Step 0; `monkey-stack.sh` sets `LLM_CREDENTIAL_KEYS`/`_ACTIVE_KID`; `setup.sh`/`rules.md` add placeholder `DATABASE_URL` for worktree gates | `pyproject.toml`, `database/sql/066_*`, rate limit config, `.planning/orchestration/*` | 066 | quick delta |

Rules for agents (put them in every brief via setup.sh):
- One worktree each: `.planning/orchestration/setup.sh WS BRANCH "OWNS" "ISSUES" "NOTE"`, run setups one after
  another. Never put backticks inside double-quoted notes. First command: `cd backend && uv sync --extra dev --frozen`.
  Backend gates need `SECRET_KEY=x DATABASE_URL=postgresql://u:p@localhost/x`.
- Fix bugs with a failing test first. Any change to RLS, triggers, auth/OAuth, saves, sessions, workflow transitions or
  lock_version adds a `backend/tests/postgres/` test of the real API flow as app_user.
- Before pushing: `make ci` and (if backend/SQL touched) `make test-postgres`, plus `make diff-cover` (changed lines
  >= 90%). Report exactly which gates ran. Open DRAFT PRs; mark ready only when local CI is green.
- Never `continue-on-error`, `|| true`, `.skip`; never Prettier `api.generated.ts`; regenerate types with `make api-types`.
- Secrets (PATs, OAuth tokens and client secrets, LLM keys) never reach the browser or logs; a test asserts it.
- Stay in your owned files. If you must touch another stream's file, stop and report instead.

## Step 2: machine safety (Wave 7 crashed the box with 13 parallel gates)
- At most 6 implementers, but at most 2 heavy local gates (`make ci`, `make test-postgres`, docker builds) at once.
  Tell agents to wait if two are running (`pgrep -fc 'make (ci|test-postgres)'`).
- Long waits run in the background with polling at 60 s, never tight loops. One merge loop at a time.

## Step 3: review and merge (serial, one loop, ends with ALL-DONE)
- Order: W8F -> W8D -> W8C -> W8E -> W8B -> W8A. Stacked or conflicting branches merge master first; the agent
  re-runs its gates after the merge.
- Review: full Opus `ponytail:ponytail-review` for W8A, W8B, W8C, W8E (logic, security, RLS/D1, load, tests, needless
  lines); quick delta review for W8D, W8F and for every fix round. Brief reviewers with what the PR claims and what to
  check; ask for must-fix items with file:line, no nitpicks. Must-fix goes back to the same agent (SendMessage), then a
  delta review.
- Merge: `set -o pipefail; .planning/orchestration/merge.sh N | tail` inside one serial loop ending `echo ALL-DONE`.
  Never merge red. Updating a branch: `gh api -X PUT repos/OWNER/REPO/pulls/N/update-branch` (no `gh pr update-branch`).
- Important-merge checkpoint after W8C and after W8A: on fresh master run `make ci` and `make test-postgres` once
  locally (one heavy gate at a time) before the next merge.

## Step 4: verify end to end
- Monkey test on a fresh stack: `.planning/orchestration/monkey-stack.sh up origin/master` (5455/8052/5190, never the
  dev stack 5454/8051/5193). Every role, two review rounds, re-curation, D1 on every route, MCP through a real client
  with a PAT and with OAuth (`claude mcp add --transport http`), the LLM second view with MockProvider, admin direct add
  in the UI, cited-evidence refusals and the new Submit disable. One fix PR for findings, review, merge.
- Optional MCP check (only if W8D changed tool output): one round-8 style run of T3/T5a/T7 with the round-7 harness;
  report token deltas, do not iterate further.

## Step 5: release v0.10.0 and report
- `release/v0.10.0`: `docs/releases/v0.10.0.md` (every claim cites a merged PR, fact-checked with `gh pr view`),
  README upgrade section (`make db-migrate` 064-066, removed evidence endpoints, OAuth setup), version bump in every
  file holding `0.9.0` (grep; not the `node >=0.8.0` lock lines). Quick review, merge, signed tag, `gh release create`.
- Cleanup: each worktree `git status --ignored` then `worktree remove --force`; branches via `gh api -X DELETE`.
- `.planning/waves/wave8/WAVE8-REPORT.md`: issues closed/partial/not started with PR links, gates per PR ("not stated"
  where silent), owner decisions, monkey results, follow-ups, Wave 9 prompt. Follow-ups to carry: GeneFoundry public
  `/mcp` 403 (ops), fleet release-control ledger expires ~2027-01-26 (commit a fresh control-audit artifact to
  genefoundry-router and re-pin the fleet before then), `.planning/codebase` regeneration (/gsd-map-codebase).

Out of scope unless the owner says otherwise: #447, #453, #282, #284, #216, #218, #219, #86, #104, #105.
End every reply with what you skipped or did not check, in one line.
