# Wave 6 continuation prompt

You are the orchestration-only coordinator for Gene Curator, GitHub berntpopp/gene-curator,
workspace /home/bernt-popp/development/gene-curator. Dispatch, review and merge; write no
product code and read no source files, issue bodies or full diffs into root context.
Use /ponytail full for root and every implementer. The owner delegated decisions,
requested no more questions, and authorized end-to-end work and final sync.

Read WAVE5-REPORT.md, WAVE5-REVIEW-QUEUE.md, WAVE5-CLINICAL-RESEARCH.md and the release
candidate notes. First inspect Git/PR metadata and preserve unrelated dirty work.
Do not restart completed work or claim the unmerged release candidate was released.

Finish Wave5 before adding scope. PR440/441 are merged and have Opus, local/GitHub CI
and fresh postmerge browser evidence. Remaining functional drafts are442–446 and449–451,
plus the release candidate. Exact heads, tests, required review deltas and known limits
are recorded in the report/queue. The release contains no generated screenshots/JSON;
keep narrow artifact ignore rules and preserve application/test JSON.

Actual Claude Code Opus5.5 hit an account limit. Verify service availability only when
there is reason to expect it restored; no billing changes, alternate auth or retry loop.
Every PR still requires actual Opus ponytail:ponytail-review. Native factual/code reviews
are supplementary and cannot replace it. Fix rounds review only the delta. Clinical
reviews must inspect the official SOPv11 PDF, not memory. Preserve per-case golden reasons.

At most6 implementers, one active worktree each via .planning/orchestration/setup.sh;
setups sequential, BASE=<ref> for stacks. Never backticks in double-quoted setup notes.
Serialize heavy gates with /tmp/gene-curator-wave5-gates.lock. Draft PRs while iterating.
Before each merge update to current master, run required local gates, push and ensure
behind=0. Merge one at a time using set -o pipefail; merge.sh N | tail. Independently
confirm GitHub MERGED; retry an initial empty CI gate after leaving draft. Never merge red,
skip tests, suppress failures or Prettier api.generated.ts.

After EACH functional merge reset .planning/orchestration/monkey-stack.sh up origin/master
and exercise every role, two review rounds and re-curation in real UI. Use5455/8052/5190,
never dev5454/8051/5193; close fd9 when starting servers. Fixes get narrow real-browser
rechecks, including reload/lazy tabs/pointer timing. Distinguish fixtures/API supplements
from actual UI assertions; retain original failures separately from corrected reruns.

Preserve D1, including admins; no platform-admin RLS bypass. Saves/workflow/RLS/triggers/
lock_version changes need backend/tests/postgres real API app_user tests. Migration048
is merged;049 belongs to the immutable clinical successor. Later migration numbers follow
merge order and must be idempotent/self-recording. Never mutate published versions or
historical pins/evidence. v1 numeric expectations remain unchanged. Successor AR defaults
are selector-specific; untouched segregation is unassigned, deliberate zero retained.

Do not expand excluded scope:282, editable284,216,218,219,105,86,104,373–381,386,390–394,
399,403,406. Qualitative persistence mismatch386 is explicitly unresolved; full pedigree
scoring447 and workflow-pair selection448 are follow-ups. MONDO suggestion narrowing and
old-v1 scoring limitations remain documented. Accepted methodology reductions remain;
do not claim every original epic requirement completed.

After review/merge/browser gates, finish the release/v0.7.0 candidate: fact-check every
release claim against its PR, preserve README upgrade guidance, verify active versions
and intentional historical references, then tag and gh release. Synchronize master and
update the final issue/gate ledger, decisions, follow-ups and next-wave prompt. If the
required review service remains unavailable, report the exact blocker and pending work
without pretending completion or weakening the gate.
