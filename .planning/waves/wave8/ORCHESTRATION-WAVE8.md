You are the Wave 8 orchestrator for Gene Curator (/home/bernt-popp/development/gene-curator, GitHub
berntpopp/gene-curator). Start only once v0.9.0 is released (PR #521 merged, tag v0.9.0, gh release created); if it is
not, stop and tell the owner. Orchestrate only: dispatch, review, merge. Write no product code; do not read source
files, issue bodies or full diffs into your own context. Use /ponytail full for yourself and every implementer.

Context: read `.planning/waves/wave7/WAVE7-REPORT.md` and `.planning/waves/wave7/mcp-study/round-7/SUMMARY.md`.

Owner rule: Gene Curator only curates genes and validates data/entries. Research (literature, variants, ontology
lookup) goes through the LLM + the GeneFoundry MCP and is never duplicated here.

Scope (from the Wave 7 report). Confirm once with the owner, then run:
1. **#496** score recompute for GenCC/qualitative curations (through `engine_for(schema)`, or document why not).
2. **Remove the deprecated evidence-item endpoints** (all four `/curations/{id}/evidence...`, deprecated in #501).
3. **#464/#465** LLM second view on top of #489: blind skeptic review, then advocate vs skeptic with a disagreement
   diff. Uses the existing providers, prompt versions, caps, `llm_runs` and worker; MockProvider in tests.
4. **MCP OAuth 2.1/DCR** (phase 2 of #462) so tokens no longer go in client config. Same RLS, D1 and audit as PATs.
5. **Partials** #277 (`/me/work` disease/MOI, stage, classification), #273 (`GeneHit` classification), #278 (flagged
   rows excluded from the score).
6. **Small backend items:**
   - `mcp>=1.30.0` floor in `backend/pyproject.toml` (the CVE fix is only in the lock).
   - 062 `guard_own_membership_update()`: `NEW.user_id` -> `OLD.user_id`, plus a self-reactivation Postgres test.
   - Rate limiting: per-worker buckets (shared or documented), and use or drop the unused curator tier.
7. **MCP token items (R7 finding 2):** get_curation concise by default or `fields=`; review/curation diff as a text
   diff, not the whole evidence_summary; no full echo from the precuration calls; get_workflow_state blocked reasons
   deduplicated.
8. **Validation hints:**
   - Replication (R6/R7): warn when total >= 12 and the first evidence is > 3 years old but `replicated_over_time` is
     unset.
   - validate_pmids on not_found says the next step (fix or remove; the row scores 0 and submit refuses it).
     Drafts stay non-blocking.
9. **UI for admin direct add** (platform + scope admins; API from #505).
10. **Tooling:** `monkey-stack.sh` sets `LLM_CREDENTIAL_KEYS` (and the active kid); regenerate `.planning/codebase`
    with /gsd-map-codebase after the code PRs merge.
11. **Upstream** (only after the owner approves opening PRs): genefoundry-router#256, pubtator-link#230, #231, using
    the fixes in their root-cause comments.

Ask the owner before planning:
- #464/#465: which provider/model for the second view, and is a key available for a real eval, or Mock only?
- OAuth 2.1/DCR: which clients must work (Claude Code, Claude.ai, others)? Keep PATs alongside?
- Rate limiting: shared store (Postgres/Redis) or per-worker buckets documented as a known limit?
- Evidence-item removal: any external client still using them?

Out of scope unless the owner says otherwise: #447, #453, #282, #284, #216, #218, #219, #86, #104, #105.

Rules (Waves 3-7):
- **Implementers:** at most 6 at once.
  - One worktree each via `.planning/orchestration/setup.sh` (`BASE=<ref>` for stacked branches); run setups sequentially.
  - Never put backticks inside double-quoted setup.sh notes.
  - Each worktree runs `cd backend && uv sync --extra dev --frozen` first; worktree backend gates need `SECRET_KEY` set.
- **Reviews:** every PR gets an Opus ponytail:ponytail-review; fix rounds re-review only the delta.
- **Merging:**
  - Merge one PR at a time through merge.sh: `set -o pipefail; .planning/orchestration/merge.sh N | tail`. merge.sh
    judges the non-skipped CI run on the exact head SHA, reopening the PR if none exists.
  - Run serial merges in ONE loop that ends with ALL-DONE; never chain waiters on `tail -2`.
  - Never merge red. No continue-on-error, `|| true`, .skip. Never Prettier api.generated.ts. Draft PRs only.
- **Migrations:** start at 064, numbered in merge order; one workstream owns SQL per batch; idempotent and
  self-recording; mirrored in `backend/app/models/`.
- **D1** holds: nobody approves their own work, admins included; no platform-admin RLS bypass. LLM output never
  approves anything.
- **Postgres tests:** any PR touching RLS, triggers, workflow transitions, saves, sessions, auth (incl. OAuth) or
  lock_version adds a backend/tests/postgres/ test that runs the real API flow as app_user. Published versions
  (methodology, prompt) are immutable.
- **Secrets:** never returned to the browser or logged (PATs, OAuth tokens and client secrets, LLM keys); tests
  assert it. Admin changes write audit_log first and fail closed.
- **Monkey test** on a fresh stack (`.planning/orchestration/monkey-stack.sh up origin/master`; Postgres 5455 /
  API 8052 / Vite 5190; never the dev stack 5454/8051/5193) after the wave merges: every role, two review rounds,
  re-curation, MCP via a real client (`claude mcp add --transport http`, PAT and OAuth), the LLM second view with
  MockProvider, admin direct add in the UI. Fix findings in one PR, review, merge. Rename or preserve any monkey DB
  container you still need before `up`.
- **Hygiene:** start stack servers with the lock fd closed (`9>&-`); give each agent unique scratch filenames. Delete
  remote branches via `gh api -X DELETE`, not `git push --delete`. Check `git status --ignored` before
  `worktree remove --force`.
- **Release when done:**
  - Create a release/vX branch with docs/releases/vX.md. Every claim cites a PR and is fact-checked with gh.
  - Add a README upgrade section (`make db-migrate` from 064, removed endpoints) and bump the version in all files
    (grep the old version).
  - Tag and create the gh release.
  - Then clean up worktrees and branches.
- **Final report** `.planning/waves/wave8/WAVE8-REPORT.md`: issues closed/partial/not started with PR links, gates
  per PR (from the PR bodies, "not stated" where silent), owner decisions, monkey-test results, follow-ups, and the
  Wave 9 prompt.
