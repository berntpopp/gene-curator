You are the Wave 5 orchestrator for Gene Curator (/home/bernt-popp/development/gene-curator,

> The monkey-stack wrapper mentioned below is operator-local and ignored, not shipped tooling. Fresh checkouts require explicit isolated-stack provisioning; see [local browser notes](wave5-evidence/LOCAL-BROWSER-NOTES.md).

> Historical planning snapshot. The current status, final gates and remaining blockers are recorded in [WAVE5-REPORT.md](WAVE5-REPORT.md).
> GitHub berntpopp/gene-curator, master at v0.6.0). Orchestrate only: dispatch, review, merge. Write no
> product code; do not read source files, issue bodies or full diffs into your own context.
> Use /ponytail full for yourself and every implementer.

Context: v0.6.0 shipped the methodology epic (#264) except the frontend score-trace work (W4S, #266).
Read `.planning/WAVE4-REPORT.md` (decisions, lessons) and the Wave 4 follow-up issues filed after the release
(label/title "Found in Wave 4"). Before planning, ASK the owner:

1. Scope: finish #266/#264 (W4S) plus which follow-ups? Offer the data-loss and correctness ones first
   ("Restore unsaved changes?" overwrite, multi-reviewer Approve visibility, condition-semantics parity,
   catalogue disease filter), then UI polish.
2. The open OWNER DECISION issue: AR blank-row defaults per variant (SOP v11 p.17/p.20).
   Out of scope unless the owner says otherwise: #282, the editable part of #284, #216, #218, #219, #105, #86, #104,
   #373-#381, #386, #390-#394, #399, #403, #406.

Rules (Waves 3, 4 and v0.5.0/v0.6.0):

- At most 6 implementers at once; one worktree each via .planning/orchestration/setup.sh (BASE=<ref> for
  stacked branches); run setups sequentially. NEVER put backticks inside double-quoted setup.sh notes.
- Every PR gets an Opus ponytail:ponytail-review; fix rounds re-review only the delta.
- Merge one PR at a time through merge.sh, always as `set -o pipefail; merge.sh N | tail` so a failure stops
  the chain; if it reports an empty CI gate right after a PR leaves draft, re-run it. Never merge red; no
  continue-on-error, `|| true`, .skip; never Prettier api.generated.ts; draft PRs only.
- Migrations start at 048, numbered in merge order, idempotent, self-recording.
- D1 holds: nobody approves their own work, admins included; no platform-admin RLS bypass.
- Any PR touching RLS, triggers, workflow transitions, saves or lock_version adds a backend/tests/postgres/ test
  running the real API flow as app_user. Published methodology versions are immutable; in-place corrections
  only with an explicit owner decision (046/047 pattern).
- Clinical scoring changes: the reviewer checks the ClinGen SOP v11 PDF, not memory; golden cases change only
  with per-case reasoning.
- Monkey test on a fresh stack (`.planning/orchestration/monkey-stack.sh up origin/master`; Postgres 5455 /
  API 8052 / Vite 5190, never the dev stack 5454/8051/5193) after each slice merges: every role, two review
  rounds, re-curation, in the UI. After every fix, a NARROW re-check of only that flow in a real browser
  (reload paths, lazy tabs and click timing found 3 bugs in Wave 4 that reviews missed).
- Start stack servers with the lock fd closed (9>&-); unique scratch filenames per agent.
- Release when done: release/vX branch with docs/releases/vX.md (every claim cites a PR, fact-checked),
  README upgrade section, version bump in all files (grep the old version), then tag + gh release.
- End with a report: issues closed/partial/not started with PR links, gates per PR, decisions, follow-ups,
  and the Wave 6 prompt.
