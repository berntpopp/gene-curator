# Wave 5 orchestration status

> Historical planning snapshot. The current status, final gates and remaining blockers are recorded in [WAVE5-REPORT.md](WAVE5-REPORT.md).

## Current checkpoint (supersedes historical notes below)

- Owner requested generatedscreenshots/JSON cleanup: narrow.gitignore rules inroot/R;
  all54current filesignored,none tracked/staged; local artifacts preserved, applicationJSON unaffected.

- Master synced to 7496d366, PR441 confirmed MERGED; required CI green and actual
  Opus delta SHIP. Fresh postmerge browser core59/59+narrow27/27 PASS; actual fonts loaded.
- PR440 merged, full browser58/59 (known430 only), narrow28/28 passed.
- PR441 candidate full59/59 and narrow25/25 passed before merge.
- A442/H443/F444/D445 remain drafts awaiting mandatory Opus review/delta review.
  D refreshedab050e58 (master441 + fixture) local CI/check green; F final5968924 CI green.
- E draft446 at01e85d7 pushed clean; full CI/check passed, frontend2530, E-only diff96%.
- J stablee35ae58 includesG/H/Aguard;12targetedfreshPGmigration/app_user tests pass,
  fullCIgreen65d4a25,2545FE; J-onlydiff99/100%. ImergedJ; readonly/table/stickywork.
  Opscombinedcore found configuredfalse default absent on untouchedsave; Dfix4e7cf155
  fullCIgreen2538FE, fix-onlydiff100/100%; Iintegrating beforefreshbrowser.
  Backendmissingboolean rejection preserved; readonly/explicitvalues preserved.
- W5R release/v0.7.0 setup BASEJ65d4a25 complete; docs/versionprep pending Iintegration.
- G draft449 pushedcleancdc199c; fullCI/check green2536frontend; G-onlydiff95/96%.
  J merged finalG includingfixtures; Istarts independent UI files.
  Targeted app_user PostgreSQL15 passed, including
  save-during-PMID-I/O concurrency regressions for all three entry paths.
- Shared B fixture compatibility commit f9c05f3 lives in E, cherry-picked7b23b86 in G.
  D incorporated current master+fixture atab050e58 and reran full CI/check successfully.
- Candidate E editable recovery23/23PASS; extra readonly display-mutation found.
  Ops Aguard6cdc7ee fullCI/check green, PGsave409/reopen/restore passed;
  freshnarrowbrowser12/12PASS (readonly + laterauthorizedrestore); draft442pushed6cdc7ee.
  J/I already incorporatedguard.
- Candidate E recovery narrow PASS; qualitative live/stored mismatch reproduced and
  privately matched to explicitly excluded386 (baseline save dispatch). E parity not claimed.
- I451 latest62fe62e fullCI/check green2561FE, I-onlyFEdiff100%; finalfreshcore59/59PASSwithoutworkarounds; clinical/UI matrix complete; finalcandidate171/171PASS.
  J450 latest6fbddc40 fullCIgreen2547FE corrects successor-only untouchedsegregationdefault.
  Gbrowser16/16PMID+5/5pagination, H6/6, historicalpin6/6; originals preserved.
  wave5_plan switchesW5R releaseprep; clinical_research ownsDinitializerfix.
- Clinical full segregation automation follow-up447 filed; no expansion of J scope.
- Remaining implementation sequence: E/G drafts, immutable clinical successor J,
  then UI polish I, aggregate verification and release/report preparation.
- Mandatory Opus unavailable due account monthly spend cap. No unreviewed merges,
  tag or release; continue implementation and testing without further user questions.

## External blocker (2026-10-22)

Claude Code account monthly spend limit reached. CLI outputs is_error=true and
reports weekly reset Oct27 05:00 Europe/Berlin. Do not change billing, alternate
authentication, retry-loop, or substitute a native review for required Opus review.
A review2 and H review2 stopped without verdict. D/F fix1 stopped. Browser Opus
stopped; wave5_ops continues native Playwright. Root told user and continues authorized
implementation/tests with native agents. Unreviewed PRs remain drafts; no release
until required review gates can pass. B already has genuine Opus delta SHIP and is
eligible after440 fresh browser gate. No user questions requested.

Native takeovers: wave5_plan implements D from dirty partial integration;
clinical_research implements F remaining review1 fixes; wave5_ops owns browser gates.

Owner: end-to-end, no more questions; consult Claude Code CLI Opus 5.5. Scope W4S
(#429/#266/#264) and #430–438. Original exclusions remain. Root orchestrates only;
no source, issue bodies, full diffs or product-code edits in root context.

Base: origin/master a7538d1 (v0.6.0); root synchronized, pre-existing planning
changes preserved. Claude CLI 2.1.308 confirms claude-opus-5-5 firstParty.

## Active slice A

| Worker | Issue | Branch | State |
| --- | --- | --- | --- |
| W5A | #436 recovery | fix/wave5-restore | PR442 draft528822c; fix1 CI green97% diff; delta review2 running |
| W5B | #430 approval visibility | fix/wave5-review-visibility | PR441 draftc51ad81; fix1 CI green100% diff; delta review2 SHIP; queued behind440 UI |
| W5C | #431 catalogue | fix/wave5-catalogue | PR440 MERGED 4fe8b6d; Opus ship; local CI + GH CI green; diff100% |
| W5D | #433 condition parity | fix/wave5-conditions | PR445 draft31720ab CI green98/100%; integration fix1 running |
| W5F | #434 scoring robustness | fix/wave5-scoring-robustness | PR444 draft5968924; all5 fixes+CI green97%; mandatoryOpus delta pending |
| W5H | #432 derive/race | fix/wave5-derive | PR443 draftfad565a; fix1 CI green100%; mandatoryOpus delta pending |
| W5E | #429/#266 score trace | feature/wave5-score-trace | nativeclinical_research implementing, BASE F5968924 + merge A/B |

Worktrees: /home/bernt-popp/development/gc-wt/W5A (and B/C). Briefs in
.planning/orchestration/W5?.brief.md contain issue bodies: root must not read.
CLI JSON results /tmp/w5-W5?-implement.json; print only final result/model metadata.
Progress /tmp/w5-W5?-progress.txt. Each uses Ponytail full, regression-first tests,
targeted checks, make check, make diff-cover, make ci and required app_user API PG tests.
Heavy gates serialized with flock /tmp/gene-curator-wave5-gates.lock.

Planning specialist: wave5_plan; clinical research: clinical_research.
Baseline monkey stack/browser owner: wave5_ops. Ports 5455/8052/5190 only.
Plan: WAVE5-PLAN.md; evidence: WAVE5-CLINICAL-RESEARCH.md. CLI implementation
sessions: A=83480 B=83082 C=59326 D=67416 F=88325 H=82328. Six implementers active.
Monkey servers need retained exec sessions because this harness reaps nohup children:
API=35012 Vite=5722; baseline browser CLI=43662. Agent wave5_ops owns lifecycle.
C review1 session=12168, result /tmp/w5-W5C-review1.json; pinned
head fdc745eae6e63178fce366b05f29c3968d16c3e0, base a7538d1.
A review1 exec23453 result /tmp/w5-W5A-review1.json. B review1 exec69589
found can_review false also hides comments/Request changes; preserve permission and
gate only Approve. Strengthen PG D1 creator admin and pending membership denial;
preserve activation after legacy API approval leaves remaining0. B fix1 exec85222,
resume session e81bdc59-1d58-4a0d-8ad2-49112a77c656, merges new master before gates.
A implementer session3097d880-2d1b-46ad-8e0e-cf8624c1fc5c. Root master now4fe8b6d.
A fix1 exec72637: address all review1 findings1-6, including existing data-loss holes.
B review2 exec92346 reviewer session f5ce24c1-8b30-4d37-9039-f4c8ebd70e00.
F review1 exec49982 pinned0ff7c982; branch rebased to38df48d identical task patch.
H review1 exec78882 pinned e227caf, verified identical task files at95e7991. H fix1
exec23092 resumes817bc869-1fab-40f6-baf6-5a39b6a92928. Reviewer session
a953e0a5-2768-47d9-9517-37a38926b954 for subsequent delta. Fix exact unique violation
handling/null-name input and store-derived actual version return; no #216 workflow-pair work.
D reports required_when still needs curation submit + direct transition integration
outside initial ownership; must extend D ownership before claiming #433 complete.
D fix1 exec61117 resumes b76f7418-dcb7-4fc1-81ba-9654a80f0c42: owns
review_guards/workflow_engine/precuration; central network-free pinned content helper
for review entry; all submit/direct/bulk/complete paths + required-parent recursion.
A review2 exec84979 resumes98bfc166-0239-48b0-9f23-92815e8a7bd9 at528822c.
H review2 exec47340 atfad565a. F fix1 exec85461 resumes
7f4ef71a-1a0c-4968-8a7d-1119253291a4; review1 sessionef53a327-7c16-49b2-b434-d0d0608a854d.
F fixes all review1 findings1-5: legacy invalid rows/nonfinite LOD, empty unknown keys,
nested unmapped evidence guards, flagged-path summary logs. Finite clinical LOD mapping
must NOT change in F. Clinical researcher investigating v2 explicit-points containment
because actual SOP requires family aggregation/method data absent from old heuristic.

## Remaining sequence

Await dependency/ownership plan, then conditions #433, score trace #429,
scoring robustness #434, PMID #435, derive #432, UI polish #437, AR decision #438.
Published versions stay immutable; no automatic rescoring or in-place correction.
Clinical specialist + actual Opus selected a feasible immutable successor v2 for #438:
selector-specific AR defaults, ephemeral new-row auto-default tracking disabled on ANY
manual score edit, loaded rows preserved; v2-only blank-row semantics. No v1 changes.
J must follow F/G shared scoring/evidence table ownership. Migration number assigned later.
E trace follows A/B/F; G PMID follows A/B/D. Detailed next briefs: WAVE5-NEXT-SLICES.md.

Every PR requires independent Opus ponytail-review; delta-only repeat reviews.
Draft PRs only. Local make ci before ready; never merge red. Merge sequentially:
`set -o pipefail; .planning/orchestration/merge.sh N | tail`, then independently
confirm GitHub state MERGED (script can mask gh failure). Retry empty initial CI gate.
merge.sh does not run local gates; if behind, it adds a GitHub merge commit. Before
invocation, have implementer update to current master, rerun local gates, push and
review delta; ensure behind=0 so the reviewed/tested head remains the merged head.
After each slice: fresh monkey stack; every role, two rounds, re-curation in real UI.
Treat EACH functional PR as a slice, not grouped merge batches. No next merge until
prior PR fresh-stack UI gate passes. Ops finishing reusable baseline runner, then
fresh4fe8b6d gate for440. Test-only Vite fs.allow scratch config addresses symlink fonts.
440 browser: core58/59 (only known430); narrow28/28 PASS, no new failures. Actual
catalogue UI has no disease-filter control; browser-origin authenticated filter/API
checks supplement UI case-file/matrix disease and visibility checks. App_user view
numeric scores validated without bypass. Artifacts /tmp/w5-pr440-browser-report.md
and /tmp/w5-pr440-preserved. CandidateB c51ad81 fresh core59/59 PASS; narrowB pending.
Baseline full evidence /tmp/w5-baseline-browser-report.md and preserved directory.
After each fix: narrow real-browser re-check of the affected flow.
Release branch, fact-checked PR-linked release notes, README upgrade section, version
bump, tag and gh release. Final report includes all issue states, PR gates, decisions,
follow-ups and Wave 6 prompt.
