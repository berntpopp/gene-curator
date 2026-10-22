# W5J closure audit

J product commit 5ec0326; A readonly integration e35ae58; historical fixture-only commit65d4a25.
Migration049 creates immutable successor versions for unchanged stock definitions, never mutating old snapshots, pins, evidence or scores. Custom/derived/changed stock definitions are preserved. Exact historical golden expectations remain unchanged.

Clinical acceptance: two-null3, mixed1.5 (explicit1.6 preserved), two-other0.2; ID/selector/status/default-only rows score0; loaded rows untouched; all manual edits including same-value opt out. Segregation nested and legacy uses explicit points only under successor pin; missing versus0 distinct; category cap3 unchanged. Full automatic pedigree/method scoring deferred explicitly to #447.

Targeted evidence: 29 table/default/PMID tests, 24 schema default validation tests, successor clinical cases plus existing flags/goldens; 12 real app_user/migration PostgreSQL cases;14 historical fixture compatibility cases;31 combined A/E form flows. make check passed before A integration (2544 frontend tests). Final full CI, slice-only diff coverage and ops browser evidence pending.

Historical fixture rationale: 046 replay tests restore historical working copies before replay, leaving its immutable v1 assertions intact; 047 now separately verifies unchanged v1 and working/latest equality. F invalid-LOD API tests publish historical v1 model explicitly, preserving original expected totals and flags. Redundant overwritten form mock removed to resolve combined A/E652-line test to648 without assertion changes.

Mandatory Opus review remains pending because the account spend limit is exhausted. Draft only; do not treat #438 as closed before merge/acceptance. Excluded #386 qualitative persistence dispatch remains unchanged. Fresh-stack browser ownership belongs to wave5_ops.

Final gates at65d4a25: canonical-lock make ci PASS,2545frontend tests,backend global94.69%; per-slice changed lines99%backend/100%frontend against4e8f896,combined master97%/98%. Logs /tmp/W5J-ci-final.log and /tmp/W5J-diff-cover-slice.log. Native product ownership released toI at e35ae58;fixture65d4a25 handed off separately. Push/draft and ops browser evidence pending.

Published draft #450: https://github.com/berntpopp/gene-curator/pull/450 at65d4a25b2583fb09d21cea26379dcf6c71939367. Standard pre-push make check passed; worktree clean. Opus review and independent browser acceptance remain pending. No issue manually closed.

Browser-found follow-up6fbddc40c99ad416b873754b04f3d11f0017d42f: successor segregation rows now start points=null, distinguishing untouched from curator-assigned0. Only product delta is unpublished049 field-default patch; v1 fielddefault0/snapshots and saved rows remain unchanged. Three new PG cases failed before the fix;15 PG and10 table cases pass afterward. Full CI and fresh narrow browser pending; candidate must be reset, never mutate its published snapshots.

Final correction gates at 6fbddc4: canonical-lock make ci PASS, 2,547 frontend tests, backend94.69%, full fresh PostgreSQL lane and all static/build/repo gates; standard pre-push make check PASS. Origin draft450 now points to6fbddc40c99ad416b873754b04f3d11f0017d42f, worktree clean. I integrated as62fe62e; independent fresh browser/Opus delta remain pending. SQL-only product delta is validated by real migration/API tests, not an instrumented changed-line coverage claim.

Resumed independent review: actual Claude Opus5.5 session6a3bf1ae-0a73-4e10-94ee-0f4e226d6435 returned SHIP for J commits5ec0326/65d4a25/6fbddc4 at6fbddc40 and identical-tree master integration547392df41d375e04ab82f3cfbd1d4c2a41e9c31. It excludes Aguard e35ae58 and stacked parents. Reviewer inspected/rendered actual official SOPv11 PDF, ran54 backend tests,10 table tests and edge probes; no actionable findings. Review JSON /tmp/W5J-opus-initial-review.json. Native canonical-lock fullCI exit0 at547392d: backend94.71%,2547frontend tests, freshPG/static/build/repo gates; slice coverage99%BE/100%FE versus4e8f896, combined97%/98%. Ops confirmed candidateI62fe62e clinical19/19 and old-pin6/6 in .planning/wave5-evidence/candidateI/REPORT.md; these are not postmerge gates. Draft450 remains open for parent merges and fresh postmerge acceptance. Prior spend-cap/pending notes above are historical and superseded by this entry.
