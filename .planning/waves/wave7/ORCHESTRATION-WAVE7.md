You are the Wave 7 orchestrator for Gene Curator (/home/bernt-popp/development/gene-curator, GitHub
berntpopp/gene-curator, master at v0.8.0). Orchestrate only: dispatch, review, merge. Write no product code; do not read
source files, issue bodies or full diffs into your own context. Use /ponytail full for yourself and every implementer.

Context: read `.planning/waves/wave6/WAVE6-REPORT.md`, plus the design comments on #462 (MCP plan, compared with
../genefoundry-router and ../pubtator-link) and the body of #489 (LLM configuration, compared with agde-api and
hum-clinical-reporting).

Scope (owner-approved direction, 2026-10-27). Confirm once with the owner, then run:
1. **#462 MCP server, fully authenticated.** It does everything the logged-in user may do, no less and no more.
   - FastMCP 3.x `from_fastapi` with in-process ASGI calls, mounted at /mcp.
   - Per-user personal access tokens (hashed, expiring, revocable, with a token UI).
   - The Authorization header must be re-injected on every internal call (FastMCP strips it). NEVER use a service
     token: that would bypass RLS and D1.
   - Every MCP call is audited with channel=mcp and the client name. Destructive tool hints.
   - Parity test: MCP vs API status codes per role.
   - Postgres tests as app_user. OAuth 2.1/DCR is phase 2.
   - Likely 2 slices: (a) PAT model + auth plumbing + token UI; (b) MCP mount + tool generation + parity/audit.
2. **#489 LLM configuration.** Providers, encrypted write-only keys (MultiFernet key ring, separate from
   SECRET_KEY), immutable prompt versions (042 pattern, no Jinja), scope opt-in with caps that fail closed, the
   llm_runs table, the /admin/llm console, the SSRF validator, MockProvider, the background worker.
   - Likely 2-3 slices: (a) DB + crypto + admin API; (b) admin console UI; (c) runtime adapter + worker + MockProvider.
   - #464/#465 (skeptic/advocate) are Wave 8 and build on this.
3. **#478 follow-ups:** CORS on the early 400/414 responses, wire rate limiting (MCP inherits it), drop or reuse
   gene_summaries (owner call), admin-only HGNC repoint. Plus the #484 remainder (user_role on single-scope GET).
4. **If capacity allows:** redesign partials #277 (My work row fields), #275 (My work/review queue on DataTable),
   #273 (palette Enter), #278 (excluded rows in score panel).

Ask the owner before planning:
- **Open decision (Wave 6):** should logged-in non-members see draft curations in a public scope's list, or only active ones?
- **LLM providers:** which to support first (Anthropic, OpenAI-compatible, both), and whether a model/API key is available for `make llm-eval`.
- **#478:** drop gene_summaries, or read from it again?

Out of scope unless the owner says otherwise: #464, #465, #447, #282, #284, #216, #218, #219, #86, #104, #105,
the #453 correction path.

Rules (Waves 3-6):
- **Implementers:** at most 6 at once.
  - One worktree each via `.planning/orchestration/setup.sh` (`BASE=<ref>` for stacked branches); run setups sequentially.
  - Never put backticks inside double-quoted setup.sh notes.
  - Each worktree runs `cd backend && uv sync --extra dev --frozen` first.
- **Reviews:** every PR gets an Opus ponytail:ponytail-review; fix rounds re-review only the delta.
- **Merging:**
  - Merge one PR at a time through merge.sh: `set -o pipefail; merge.sh N | tail`. merge.sh judges the non-skipped CI
    run on the exact head SHA, reopening the PR if none exists.
  - Run serial merges in ONE loop that ends with ALL-DONE; never chain waiters on `tail -2`.
  - Never merge red. No continue-on-error, `|| true`, .skip. Never Prettier api.generated.ts. Draft PRs only.
- **Migrations:** start at 056, numbered in merge order; one workstream owns SQL per batch; idempotent and self-recording.
- **D1** holds: nobody approves their own work, admins included; no platform-admin RLS bypass.
- **Postgres tests:** any PR touching RLS, triggers, workflow transitions, saves, sessions, auth or lock_version adds a
  backend/tests/postgres/ test that runs the real API flow as app_user. Published versions (methodology, prompt) are
  immutable.
- **Secrets:** never returned to the browser or logged; tests assert it. Admin changes write audit_log first and fail
  closed.
- **Monkey test** on a fresh stack (`.planning/orchestration/monkey-stack.sh up origin/master`; Postgres 5455 /
  API 8052 / Vite 5190; never the dev stack 5454/8051/5193) after the wave merges: every role, two review rounds,
  re-curation, MCP via a real client (`claude mcp add --transport http`), and the LLM admin console with MockProvider.
  Rename or preserve any monkey DB container you still need before `up`.
- **Hygiene:** start stack servers with the lock fd closed (`9>&-`); give each agent unique scratch filenames. Delete
  remote branches via `gh api -X DELETE`, not `git push --delete`. Check `git status --ignored` before `worktree remove --force`.
- **Release when done:**
  - Create a release/vX branch with docs/releases/vX.md. Every claim cites a PR and is fact-checked.
  - Add a README upgrade section and bump the version in all files (grep the old version).
  - Tag and create the gh release.
  - Then clean up worktrees and branches.
- **Final report:** issues closed/partial/not started with PR links, gates per PR, decisions, follow-ups, and the
  Wave 8 prompt.
