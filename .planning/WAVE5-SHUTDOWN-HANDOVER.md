# Wave5 shutdown handover — stopped at owner request

**STOP is active.** The owner requested shutdown, checkpoint and handover only. Do not
resume implementation, reviews, merges or release merely because this file is read.
Continue only after the owner explicitly resumes. No v0.7.0 tag or GitHub release exists.
Release PR [452](https://github.com/berntpopp/gene-curator/pull/452) remains draft.

## Exact state

- Root and origin/master: `121592011fe387e6a83faffe8eaaae543f8ddea5`.
- Eight functional PRs are merged:440/441/442/443/444/445/446/449. G449 merged at1215920
  from final reviewed/tested head `d0d4088a9ebffbec4833ff02d3d8988d18e784f6` before the
  stop check. Its required fresh postmerge browser gate **HAS NOT RUN**. This is the
  first gate on any future resume; do not merge J before it passes.
- J450, I451 and R452 remain unmerged. No new source code was written for shutdown.
- R integrated G master ancestry at `0def9343903983f26624bb4d6c7f701cd61af008`.
  Complete tree `79a449fecdcda1b6d8371730bc1730e12b7d1a66` equals f599a60 exactly;
  `git diff f599a60 0def934` is empty. The remaining checkpoint changes are Markdown only.
- Final tested R product source: `06761a7063cf491bd04188608edc30b037d88a84`. Relative to
  reviewed I, backend/frontend/database/scripts differ only in eight0.7.0 version files.
  The feature-template option and bug-template example are separate text updates.

| Remaining PR | Verified pushed source head | Tested tree / evidence |
| --- | --- | --- |
| [450 J](https://github.com/berntpopp/gene-curator/pull/450) | f1549c43c64ad930c1bcb458c27a9d7d3b5beab9 | 467809e89e95074deb84b52a431772759f41454a; fullCI2565 FE/backend94.72%, fullPG, J-only99/100%; actual Opus SHIP |
| [451 I](https://github.com/berntpopp/gene-curator/pull/451) | fb244082654ed1ce6340ad271b37652613cb838f | e13717fcd16d29302261340aba76b4cc96101ce5; fullCI2572 FE/backend94.72%, fullPG, I-only100/100%; actual Opus SHIP |
| [452 R](https://github.com/berntpopp/gene-curator/pull/452) | Final shutdown commit linked by the PR handover comment | Source06761a7 fullCI2572 FE/backend94.71%, fullPG, diff97/99%; later repository/workflow/YAML checks passed |

Normal pre-push hooks remain enabled. GitHub PR-head metadata has lagged verified remote
branches during a PR/Actions incident. Use `git ls-remote` to verify delivery, then wait
for GitHub's exact head and required gate before any future merge. Do not manufacture
empty commits, force-push or merge stale metadata. Recheck [GitHub status](https://www.githubstatus.com/)
on resume; this handover does not assert the incident has subsequently resolved.

## Reviews and gates already completed

Actual Opus5.5 is working again; the earlier session-limit blocker is superseded.
Native implementation/audits do not substitute for these independent actual verdicts.

- J: session `6a3bf1ae-0a73-4e10-94ee-0f4e226d6435`, SHIP atf1549c4. Prior actual SOPv11
  PDF review stands; migration049, clinical scoring and goldens remain unchanged.
- I: session `45f7fe7a-786c-4d1b-a793-5acaf635a108`, SHIP atfb24408, including exact-ID
  lookup and the exact R-reviewed readonly/PMID watcher composition.
- R: session `b09f17b0-07b0-4e07-bb88-b14dedb9c10b`, SHIP at453a49b, cleanup e02479b and
  final integration/docs01b6c77/source06761a7. **The later f599 wording/bug-template and
  shutdown/final-release-facts delta still needs narrow actual Opus review.** No review
  was run after STOP. Final publication gates remain incomplete.
- D/E and all five earlier merged slices have fresh postmerge evidence. E passed59+17+1;
  accepted-scope epic264 and W4S266 are CLOSED. #268 is closed with accepted broader cuts.
- Combined R320a338 candidate passed226/226 browser checks with identical product behavior.
  It does not replace G/J/I individual fresh postmerge gates.

See [review queue](WAVE5-REVIEW-QUEUE.md), [integration ledger](W5R-INTEGRATION-CHECKPOINT.md),
[J gates](W5J-RESUMED-GATES.md), [I gates](W5I-RESUMED-GATES.md) and
[epic closure audit](W5-EPIC-CLOSURE-AUDIT.md). Local Opus JSONs and CI logs under/tmp
are provenance; durable summaries are tracked Markdown. No tokens/auth-state dumps are tracked.

## Newly completed upgrade evidence

[Populated v0.6.0 upgrade rehearsal](wave5-evidence/upgrade-v060/REPORT.md) passed on the
same isolated database, from actual tagv0.6.0/a7538d1 through048/049 to source06761a7.
Eleven original published-version/snapshot fingerprints plus pinned curation/precuration
records remained identical. Baseline4/4, migration6/6, upgraded UI/API16/16 and final
fingerprint/idempotence6/6 passed; both migrations self-record once. This fills the
previous missing real populated-upgrade path; no product changes or clinical reinterpretation.
G's separate fresh postmerge gate is still not run.

## Services stopped and evidence retained

Owned monkey API/Vite processes555034/555101 were terminated and `docker stop gc-monkey-db`
completed successfully. No listeners remain on8052/5190/5455; dev services were untouched.
The stopped container, populated upgrade volume and monkey checkout06761a7 are preserved.
No OS shutdown command was issued. The [upgrade report](wave5-evidence/upgrade-v060/REPORT.md#owner-requested-shutdown-checkpoint)
records exact restart/reset and ordered G browser commands. Starting the preserved database
for inspection and resetting it for the required fresh G gate are distinct operations.

## Exact next actions — only after an explicit resume

1. Read this file, inspect root/worktree status, and verify remote heads without changing
   unrelated dirty work:

   ```bash
   cd /home/bernt-popp/development/gene-curator
   git status --short
   git fetch origin
   git rev-parse HEAD origin/master
   git ls-remote origin refs/heads/feature/wave5-clingen-successor refs/heads/fix/wave5-ui-polish refs/heads/release/v0.7.0
   gh pr view 450 --json state,isDraft,headRefOid
   gh pr view 451 --json state,isDraft,headRefOid
   gh pr view 452 --json state,isDraft,headRefOid
   ```

2. **Run G's missing fresh gate first**, using only isolated DB5455/API8052/Vite5190:

   ```bash
   cd /home/bernt-popp/development/gene-curator
   flock /tmp/gene-curator-wave5-gates.lock bash .planning/orchestration/monkey-stack.sh up origin/master 9>&-
   ```

   This wrapper is retained operator-local and ignored, not shipped tooling. A fresh clone
   must explicitly provision that isolated stack. Never use dev5454/8051/5193. Close fd9
   when starting retained API/Vite servers. Restore the ignored local browser runners to
   /tmp as described in [local browser notes](wave5-evidence/LOCAL-BROWSER-NOTES.md).
   Run a fresh bootstrap and canonical core59 (every role, two rounds, re-curation), then
   G original PMID flow16 plus lifecycle7 and font check, using the exact ordered commands
   in the upgrade report; distinguish UI actions from
   fixture/read-back APIs and unit-only concurrent cancellation coverage. Do not reuse the
   upgrade fixture or call combined-candidate evidence a G postmerge pass.

3. Only after G passes, update J in its existing worktree and compare the tested tree:

   ```bash
   cd /home/bernt-popp/development/gc-wt/W5J
   git status --short
   git merge --no-edit origin/master
   git rev-parse 'HEAD^{tree}'
   ```

   Expected tree467809e89e95074deb84b52a431772759f41454a. If identical, retain the exact
   tested-tree/actual-review evidence and run normal push hooks/GitHub CI. If content
   differs, inspect the delta, preserve049/goldens and obtain justified tests plus actual
   Opus delta review before merge. Heavy gates use the canonical flock. Verify PR450's
   exact final head and required CI gate, then root merges only via:

   ```bash
   cd /home/bernt-popp/development/gene-curator
   set -o pipefail; .planning/orchestration/merge.sh 450 | tail
   ```

   Independently verify MERGED; run J's fresh full core plus clinical19/old-pin6 before I.
4. Repeat current-master integration in W5I, expecting treee13717fcd16d29302261340aba76b4cc96101ce5
   if ancestry-only. Preserve normal hooks/GitHub/exact-head gates, merge451 sequentially,
   then fresh core plus readonly/responsive/PMID/exact-ID/pointer flows. No self-approval,
   including admins; no RLS bypass. Do not merge slices ahead of their fresh browser gate.
5. Reconcile R with final master. Its remaining product diff must be only intended version
   updates or explicitly reviewed integration fixes. Refresh issue states, release claims,
   gates and this handover; obtain the pending actual R narrow review. Reuse exact source
   CI only when content matches; run required repo/static/diff/GitHub gates on final head.
   Only after all gates and an explicit resumed task may root merge452, tagv0.7.0 and create
   the GitHub release. None of those publication actions has happened at shutdown.

## Preserved workspace and backup safety

Root is on1215920 with six pre-existing dirty tracked paths: .gitignore,
.planning/ORCHESTRATION-WAVE3.md, archived scripts README and ClinGen INDEX,
.planning/orchestration/rules.md and setup.sh. Task reports and the local monkey wrapper
remain locally untracked there. Preserve these and all worktrees; do not reset/clean/stash
whole directories. Planning-only checkpoint copies may be reconciled deliberately.

[Root-sync preservation plan](W5-ROOT-SYNC-PRESERVATION.md) records verified external backups:

- `/tmp/gc-wave5-root-preservation-lpdnftfn`
- `/home/bernt-popp/.local/state/gene-curator/backups/gc-wave5-root-preservation-lpdnftfn`

The original snapshot contains70 files/16,147,612 bytes with verified hashes:15 release
untracking deletions, six dirty tracked files,48 Markdown files and the local wrapper.
Refresh new/changed Markdown into a new external manifest before final sync; retain this
older backup. The fifteen raw/helper files remain local in both trees now. A future root
fast-forward will remove their tracked copies: restore only absent files from the verified
latest backup, verify hashes and precise ignores, never overwrite newer local copies or
restage them. Raw backups and credentials are not release assets.

## Scope and unresolved follow-ups

- [386](https://github.com/berntpopp/gene-curator/issues/386): excluded qualitative persistence
  dispatch mismatch; no qualitative save parity claimed.
- [447](https://github.com/berntpopp/gene-curator/issues/447): full family/method-aware automatic
  segregation. Successor explicit points are containment; old pins stay unchanged.
- [448](https://github.com/berntpopp/gene-curator/issues/448): workflow-pair default selection.
- [453](https://github.com/berntpopp/gene-curator/issues/453): legacy missing own+linked disease
  leaves readonly evidence without a supported correction path. Correct refusal remains;
  no implicit backfill, pin rewrite or data repair was performed.

All original exclusions remain:282, editable284,216,218,219,105,86,104,373–381,386,
390–394,399,403,406. No new scope or clinical interpretation is authorized by this handover.
