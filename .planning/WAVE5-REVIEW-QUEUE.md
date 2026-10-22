# Required Opus review queue

> **12:31 UTC update:** actual Opus reviews resumed successfully, then the CLI hit its session usage limit (reset 19:00 Europe/Berlin). Completed SHIP verdicts remain valid; no further calls before reset. Native fixes and already-reviewed merge/browser gates continue.

Every entry requires actual Claude Code Opus5.5 using ponytail:ponytail-review.
Owner resumed on 2026-10-22. Actual Opus5.5 is available again; do not substitute native approval.
Review the latest pushed head and reconcile merge-only parent changes. Fix rounds
review only the task delta plus connected behavior, not every already-reviewed line.
No unreviewed draft becomes ready or merges. Actual SOPv11 PDF required for clinical work.

| PR | Last substantive head | Required review |
| --- | --- | --- |
|442 recovery|9e04844515da90e5fe08b11cb92bab9d3b8007b3|Actual resumed Opus delta SHIP after readonly precuration restore, readonly discard and late-save resurrection fixes; fullCI/check/diff97%, fix100% passed. Candidate browser36/36 expanded +23/23 replay passed; merged358ce6c with GitHub CI pass; fresh core running. Session98bfc166-0239-48b0-9f23-92815e8a7bd9.|
|443 derive|f312c08fef8bbd33f92f12305b61f41488c75442|Actual Opus delta SHIP after is_active:null guard and app_user regression. Full CI/check/diff100% passed; pushed draft; narrow browser and current-master integration pending. Sessiona953e0a5-2768-47d9-9517-37a38926b954.|
|444 robustness|62b7c35ab1a7f0d1f1d03d96469d4f7a8e8ce1b5|Actual Opus delta SHIP; all five findings resolved, SOP PDF checked. Locked full CI/check passed, diff97%. Merged at785e573 with GitHub CI gate pass; fresh post-merge core59/59, narrow9/9, font1/1 passed. Sessionef53a327-7c16-49b2-b434-d0d0608a854d.|
|445 conditions|4e7cf15519d51d2c8360895141756df9e88cb2d4|Actual Opus FIX sessionc01a6d5e-4428-4680-9912-f09d92c1045e: readonly disease fields missing on historical/direct-created curations must use legitimate linked-precuration fallback; add real app_user route matrix and ACTIVE rejection.|
|446 score trace|01e85d7abd3ffe82adb3c40365a1d73a1c9aabbc|Actual Opus FIX session05a8493c-5865-449e-b94e-01ead94c8a8f: stale-score clearing unmounts sidebar/checklist every edit; preserve stable pending layout through debounce.|
|449 PMID/workflow|cdc199c6f937022b590ccbb7663a0eeb071c3c42|Actual Opus SHIP sessione2d6733c-aa33-4c18-b2c8-9a4b2867637e; two scoped nonblocking client lifecycle observations queued; integration/gates/browser pending.|
|450 immutable successor|6fbddc40c99ad416b873754b04f3d11f0017d42f|Actual Opus SHIP session6a3bf1ae-0a73-4e10-94ee-0f4e226d6435 at547392d (identical tree to6fbddc4), actual SOP PDF inspected; full CI/check and diff99/100 passed. Future parent-fix integration/browser gates required.|
|451 UI polish|62fe62e (includes D/J browser fixes)|Actual Opus SHIP session45f7fe7a-786c-4d1b-a793-5acaf635a108 at62fe62e; stored susceptibility label resolution regression assigned for scoped fix and delta review.|

|452 release preparation|0bebdb9a1522f5125f08a0ac445d6727ae253d0a (plus report-link follow-up)|Initial release-only Opus ponytail review; PR-cited release notes, immutable upgrade guidance, all active versions, sanitized report provenance and local-only helper/artifact exclusions; parent functional reviews remain required|

Completed:440 actual Opus SHIP atfdc745e;441 actual Opus delta SHIP atc51ad81,
sessionf5ce24c1-8b30-4d37-9039-f4c8ebd70e00. Both merged with local/GitHub CI and
fresh browser evidence. Do not rereview them absent new changes.

Stored CLI results live under /tmp/w5-W5?-review?.json; do not treat tool errors or
partial responses as SHIP. Preserve accurate native versus Opus implementation/review
provenance in reports. Before merge, update against current master, rerun required
local gates, push, check behind=0, then pipefail merge.sh; independently verify MERGED.
