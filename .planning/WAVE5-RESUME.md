# Wave 5 resume checkpoint

2026-10-22: five functional PRs merged, five functional drafts plus release452 remain.
Master7b984161db6bbf1b678d881990c4bdd711e84fa1 includes440/441/442/443/444; all five
have completed actual Opus/local+GitHub CI/fresh postmerge gates.

Combined release source320a33835f847cb135714089858bedb0accc6bcc includes final
D16b5285, Eb85d8e0, G32b77d7, J547392d lineage and Id0c87bd. Focused84 backend and
156 frontend tests pass. Combined full CI passed at320a338 (2572 FE, backend94.71%, full PostgreSQL, diff97/98%);
fresh browser checks are running.
See [report](WAVE5-REPORT.md), [review queue](WAVE5-REVIEW-QUEUE.md) and
[integration ledger](W5R-INTEGRATION-CHECKPOINT.md) for precise gates and pending work.

Actual Opus5.5 resumed successfully, then hit its session limit; reset19:00 Europe/Berlin.
Do not retry before reset/new owner signal or alter billing/auth. D/E initial reviews
returned FIX; native fixes are complete. G/I initial SHIP verdicts predate their native
follow-up fixes. J SHIP is valid, with parent/integration checks still required. D/E/G/I
actual delta reviews and R integration/release review remain mandatory. Native factual
review is supplementary. No v0.7.0 tag or GitHub release exists;452 stays draft.

## Continue without restarting completed work

1. Read the report/queue and verify remote metadata. Preserve every worktree and unrelated
   root Wave3/4/tooling/ignore changes; reconcile only verified duplicate task-owned reports.
2. Complete combined candidate gates and record actual head/results. Ops owns isolated
   stack5455/8052/5190; never dev5454/8051/5193. Source is frozen after browser handoff
   except a real test/browser finding. Only Markdown evidence is tracked; raw artifacts
   and generated runners remain local and ignored.
3. Once service access is restored, obtain required actual Opus delta/integration reviews.
   Fix actual findings regression-first and re-review only the delta. Clinical reviews
   inspect the actual SOPv11 PDF; preserve published snapshots and historical goldens.
4. For each remaining functional PR, integrate current master, run required local gates,
   push, ensure behind=0, then use `set -o pipefail; merge.sh N | tail`. Never merge red;
   retry the initial empty CI gate after draft promotion and independently verify MERGED.
5. After EACH functional merge reset the fresh monkey stack and exercise every role,
   two review rounds and re-curation in real UI. Fixes also require narrow real-browser
   reload/lazy-tab/pointer checks. Do not batch merges ahead of their fresh gate.
6. After all functional merges, inspect R versus master: only intended versions/docs or
   explicitly reviewed integration fixes may remain. Complete R actual Opus/CI gates,
   update release facts, then release/tag only when all required gates pass.

Owner authorized end-to-end continuation without more questions. All exclusions and
accepted Wave4 scope reductions persist; #264/#266 remain open until their accepted
scope is merged/verified. #268 is already GitHub-closed, with broader cuts documented.
