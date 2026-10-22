# Required Opus review queue

Checkpoint2026-10-22: actual Claude Code Opus5.5 completed the reviews below, then hit a
session limit resetting19:00 Europe/Berlin. No retry before reset/new owner signal.
No billing/auth changes. Native fixes, tests and audits do not satisfy mandatory review.
Use ponytail:ponytail-review full; fix rounds review only the new delta and connected code.
Clinical review requires the actual official SOPv11 PDF and per-case golden rationale.

## Remaining functional reviews

| PR / candidate | Completed actual review                                                                                      | Remaining delta and gates                                                                                                                                      |
| -------------- | ------------------------------------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 445 /16b5285   | FIX at4e7cf15, session c01a6d5e-4428-4680-9912-f09d92c1045e                                                  | Native inherited-disease fallback31242e8 plus integration, real app_user submit/direct/bulk/ACTIVE cases; [checkpoint](W5D-INHERITED-DISEASE-FIX.md)           |
| 446 /b85d8e0   | FIX at01e85d7, session05a8493c-5865-449e-b94e-01ead94c8a8f                                                   | Native stable pending layout3659fa1, fixture completionb85d8e0; debounce/request/superseded response lifecycle, mounted checklist and no stale numeric display |
| 449 /32b77d7   | SHIP atcdc199c, sessione2d6733c-aa33-4c18-b2c8-9a4b2867637e                                                  | Native lifecycle28f3608, race regression57c76f8 and D integration; [checkpoint](W5G-LIFECYCLE-FIX.md)                                                          |
| 450 /547392d   | SHIP, session6a3bf1ae-0a73-4e10-94ee-0f4e226d6435; reviewed6fbddc4 and tree-identical547392d; actual SOP PDF | No new J product fix awaiting review; reconcile newer parents/integration, final local/GitHub CI and fresh postmerge gate                                      |
| 451 /d0c87bd   | SHIP at62fe62e, session45f7fe7a-786c-4d1b-a793-5acaf635a108                                                  | Native exact-ID4594ed1, isolated test-fixture74b662c and parent integrations; [checkpoint](W5I-MONDO-FIX.md)                                                   |

Combined R source320a338 passed full CI; fresh browser checks are running. Each functional PR still
needs current-master integration, required local/GitHub CI and fresh per-merge UI gates.
Do not call a parent initial SHIP approval of subsequent native fixes.

## Release and integration review

Draft452 requires an actual initial Opus review. It includes both release changes and
manual product conflict resolutions; a release-only review is insufficient now.
[Exact merge/path ledger](W5R-INTEGRATION-CHECKPOINT.md) identifies schema-validator,
review-guard and EvidenceTableField resolutions. Cover their connected D/G/J/I behavior,
PR-cited claims,048/049 upgrade guidance, active versions, historical references, and
Markdown-only evidence/provenance. Before publication, all functional PRs must be merged;
verify the remaining product diff is only intended versions/docs or explicitly reviewed
integration fixes. Then final CI/review/merge/tag/release gates apply.

## Completed merged reviews

-440 fdc745e actual Opus SHIP; merged4fe8b6d.
-441 c51ad81 actual Opus delta SHIP, sessionf5ce24c1-8b30-4d37-9039-f4c8ebd70e00; merged7496d36.
-442 9e048445 actual Opus delta SHIP, session98bfc166-0239-48b0-9f23-92815e8a7bd9; merged358ce6c.
-443 ccd90aa includes reviewed is_active:null fix; actual Opus delta SHIP, sessiona953e0a5-2768-47d9-9517-37a38926b954; merged7b98416.
-444 62b7c35 actual Opus delta SHIP/SOP PDF, sessionef53a327-7c16-49b2-b434-d0d0608a854d; merged785e573.

All five have local/GitHub CI and fresh postmerge evidence. Do not repeat their reviews
absent new changes. Tool errors, missing model usage and partial output are not SHIP.
CLI review JSONs remain local under/tmp; substantive verdicts/session/model provenance
are recorded here and in evidence reports.
