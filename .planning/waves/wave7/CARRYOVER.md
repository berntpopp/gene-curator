# Wave 7 carry-over (2026-10-28)

Orchestrator role: dispatch, review (Opus ponytail-review; quick delta checks for fix rounds), merge one PR at a time via
`set -o pipefail; .planning/orchestration/merge.sh N | tail` (serial loops ending ALL-DONE). No product code by the orchestrator.
Ponytail full for every agent. Owner wants speed with no errors.

## State
- Master: 29 Wave 7 PRs merged (#491-#519, no #496 which is an issue). Migrations 056-063. Closed: #462, #489, #478, #275.
  Partial: #277, #273, #278 (need backend data). New follow-up issue: #496 (non-ClinGen recompute).
- MCP study (protocol: .planning/waves/wave7/MCP-STUDY-PROTOCOL.md, rounds in mcp-study/round-1..6/SUMMARY.md):
  - Round 6 (lean 47-tool /mcp core, GeneFoundry attached for T2b/T3/T7/T8): 24/27, 0 unsafe; discoverability 8, speed 9,
    tokens 8 (met), error clarity 6 overall / 4 Gene Curator-only (n=3; one bad message), safety 9, overall 8.
  - OWNER STOP RULE: done when error clarity >= 8 (Gene Curator errors only; GeneFoundry errors excluded) and token
    efficiency >= 8, others not worse, 0 unsafe. Max 8 rounds.
  - Owner scope rule: Gene Curator = curating genes + validating data/entries. Research only via the LLM + GeneFoundry MCP.
    Never rebuild literature/variant lookup here (memory: no-genefoundry-duplication).
- In flight:
  - W7M9 (worktree ../gc-wt/W7M9): final error/token PR (field+limit+received in all length/enum/required errors incl. the
    MCP pre-check; 2037-char comment test; precuration create shows required fields; plain "PMID X not found" save message;
    collapsed warnings; get_curation evidence once; assigned reviewer in get_curation). On push: quick ponytail check, merge.
  - Upstream debugging (comments only, no PRs): genefoundry-router#256 (pinned mondo/clingen tools advertised but "tool not
    available"), pubtator-link#230 (Case Reports filter -> 0), #231 (opaque error). Relay root causes to the owner.
- GeneFoundry for the study: run claude -p from the scratchpad cwd with --strict-mcp-config and one --mcp-config holding
  gene-curator (Bearer PAT) and genefoundry-study {"type":"http","url":"https://genefoundry.org/mcp"} (owner OAuth stored),
  and --allowedTools for the genefoundry-study tools. Scratchpad:
  /tmp/claude-1000/-home-bernt-popp-development-gene-curator/2d9da0ff-7aea-4381-a0a7-64dddc961bab/scratchpad

## Remaining steps
1. Merge W7M9's PR. Rebuild the study stack: `.planning/orchestration/monkey-stack.sh up origin/master` (API 8052, never the
   dev stack 5454/8051/5193).
2. Round 7: fresh independent runner, Claude Code only, /mcp core, GeneFoundry for T2b/T3/T7/T8, error clarity scored on
   Gene Curator only, write round-7/SUMMARY.md (write it yourself if the runner is blocked). If the stop rule is met, stop the
   study; else one small fix round aimed only at errors/tokens, then round 8.
3. Monkey test on a fresh stack (`monkey-stack.sh up origin/master`): every role, two review rounds, re-curation, MCP via a
   real client (`claude mcp add --transport http`), LLM admin console with MockProvider, PAT UI, direct add, default pair,
   cited-evidence/placeholder-variant refusals in the UI. Fix findings (one PR, review, merge).
4. Release v0.9.0: branch release/v0.9.0; docs/releases/v0.9.0.md from .planning/waves/wave7/v0.9.0-DRAFT.md (move #511/#512
   out of pending; add #513-#519 and the final PRs; every claim cites a merged PR, fact-check with gh). Breaking/upgrade
   notes: make db-migrate 056-063; REST concise by default (detail=true); calculated_score removed; evidence-item endpoints
   deprecated; search_pubmed never released; cited-evidence policy (no PMID/unknown PMID/no or placeholder variant/blank
   score_status -> 0, submit refuses); legacy rows score 0 on recompute unless active/archived; rate limiting on in prod,
   FORWARDED_ALLOW_IPS behind a proxy; LLM_CREDENTIAL_KEYS/LLM_CREDENTIAL_ACTIVE_KID; migration owner superuser/BYPASSRLS;
   gene_summaries dropped; /mcp core vs /mcp/full; PATs (365-day max, account ops blocked). README upgrade section; bump
   "0.8.0" in the 11 files listed in the draft (not the node>=0.8.0 lines in package-lock). Also commit the uncommitted
   planning files (.gitignore mcp-study rule, protocol, round summaries, audits, this file). PR, merge.sh, tag v0.9.0,
   gh release create.
5. Cleanup: for each ../gc-wt/W7* and monkey worktree check `git status --ignored` before `git worktree remove --force`;
   delete remote branches with `gh api -X DELETE repos/berntpopp/gene-curator/git/refs/heads/<b>`.
6. Final report .planning/waves/wave7/WAVE7-REPORT.md (issues closed/partial/not started with PR links, gates per PR,
   owner decisions, MCP study results R1-R7, follow-ups) and the Wave 8 prompt (.planning/waves/wave8/ORCHESTRATION-WAVE8.md):
   #496, remove deprecated evidence-item endpoints, #464/#465 (LLM skeptic/advocate on #489), MCP OAuth 2.1/DCR, partials
   #277/#273/#278, mcp>=1.30.0 floor in pyproject, 062 trigger OLD.user_id, upstream GeneFoundry/PubTator issues, rate limit
   per-worker buckets, curator rate tier.

## Owner decisions this wave (for the report)
Outsiders see active curations only; LLM providers Anthropic + OpenAI-compatible + Mock, no eval key; drop gene_summaries;
rate limiting on in production only; PATs blocked from account/identity ops; admin direct add (platform + scope admins);
evidence-item endpoints deprecated (remove Wave 8); REST concise by default; /mcp core vs /mcp/full; cited evidence only;
placeholder variants refused at submit; no literature duplication of GeneFoundry; study: Claude Code only from R2, stop at
errors and tokens >= 8.
