# W5R combined candidate checkpoint

Source candidate: `320a33835f847cb135714089858bedb0accc6bcc`, release/v0.7.0, draft 452.
Source is frozen after handoff to ops; only a real browser/test finding permits a product fix.
Native integration is not an Opus approval. Full combined CI passed at 320a338; fresh browser checks passed226/226 without product changes.
Focused checks passed 84 backend+156 frontend tests, file-size and diff whitespace checks.

## Integration and manual resolution ledger

| Merge commit                             | Input         | Manual resolution                                                                                                                                                                                                                                                |
| ---------------------------------------- | ------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 5db91a904114bd50f489ff6c5d84783b3278af4c | master7b98416 | Test-only SchemaDrivenCurationFormFlows.spec.ts retained both A cancel assertions and existing fixtures                                                                                                                                                          |
| 79c980bb528aa9633fc077d2166d5208818efac0 | D16b5285      | backend/app/core/schema_validator.py retained description/default/default_by union; backend/app/services/review_guards.py used exact finalG32b77d7 composition of D inherited-disease fallback and G network-free checks                                         |
| 496cfaef99aba287fa58cc0208afe317552f88e6 | Eb85d8e0      | Automatic merge, no manual product resolution                                                                                                                                                                                                                    |
| d85ad13ddd8277e2385f97a0e588abd572c47db7 | G32b77d7      | frontend/src/components/dynamic/EvidenceTableField.vue combined sorted-unique-PMID watch with disabled-or-readonly editability; preserves G no retry on unrelated score/reorder and I readonly suppression/editable retry; J automatic-default tracking retained |
| 320a33835f847cb135714089858bedb0accc6bcc | Id0c87bd      | Automatic merge, no manual product resolution                                                                                                                                                                                                                    |

The G merge removed two redundant test comments to keep the existing form-flow test at 650
lines; every assertion remains. Initial hook correctly rejected652 lines, then normal hooks
passed. Root's intentional dirty planning Markdown was preserved in f660714 before merges.
No workflow, script, historical golden, migration-number or unrelated product change was added.

Actual Opus must cover the manual product resolutions and connected behavior above in
addition to D/E/G/I fix deltas. A release-only review is insufficient while product changes
remain relative to master. After functional PRs merge, inspect the remaining R product diff;
backport/review any necessary integration fix explicitly rather than silently releasing it.

Full canonical-lock CI passed at 320a338: 2,572 frontend tests, backend 94.71%, full fresh
PostgreSQL and static/type/security/build/repository gates. Standard changed-line coverage
is97% backend/98% frontend. Full CI log: /tmp/W5R-combined-ci.log. Focused logs:
/tmp/W5R-focused-backend.log and /tmp/W5R-focused-frontend.log. Logs/artifacts are local only.

## Final candidate acceptance

[Combined real-browser report](wave5-evidence/R-combined/REPORT.md) records core59,
D16, E17, G16+7, I6, clinical19, old-pin6, responsive57, scope17, pointer5 and font1:
226/226 passed on the exact320a338 product candidate. Actual UI, fixture/read-back API
checks and the unit-only concurrent cancellation race are distinguished. Excluded386
remains unchanged. This candidate gate does not replace fresh gates after each merge.

Independent native factual audit at docs2fa74d7/source320a338 found no corrections in
versions, PR citations, gate/review provenance or exclusions. It is supplementary, not
actual Opus product approval. All required Opus delta/integration/release reviews remain
in [the queue](WAVE5-REVIEW-QUEUE.md); no tag or GitHub release exists.

## J current-master integration preparation

Read-only prep at J547392d/master7b98416: J contains final B/C/F, initial D33fa1b9 via E01e85d7, Gcdc199c, Hfad565a, A readonly guard e35ae58, and clinical successor5ec0326/null-points6fbddc4. Later A cancellation, D defaults/inherited-disease, E pending-panel, G lifecycle, H null-guard and I exact-ID changes are absent. Remaining D→E→G→J→I order is valid; integrate reviewed parents before isolating J's clinical delta. Migration files match accepted R320a338.

Merge-tree simulation against master7b98416 reports only `frontend/src/components/forms/__tests__/SchemaDrivenCurationFormFlows.spec.ts`. Against D820bc70 it additionally reports `backend/app/core/schema_validator.py` and `backend/app/services/review_guards.py`; against G32b77d7 it reports schema_validator and the form-flow test. E64aa666+G32b77d7 merges automatically. These are predictions for those exact heads, not completed integrations; recheck after actual parent merges.

Use the existing ledger resolutions: retain description/default/default_by union; retain final G review guard composition with D inherited disease; preserve A cancel assertions and historical J fixture correction. Later I integration must combine sorted unique PMID watching with disabled-or-readonly editability while preserving J automatic-default tracking in EvidenceTableField.vue. No code/stack changes or duplicate tests were made for this prep.

## Final source integration after resumed reviews

R06761a7063cf491bd04188608edc30b037d88a84 merged reviewed Ifb24408. Only manual conflict
was frontend/src/components/forms/**tests**/SchemaDrivenCurationFormFlows.spec.ts: chose
I's complete reviewed file and retained schemaCurationFormStubs.ts. Every assertion remains.
Product comparison against I across backend/frontend/database/scripts shows exactly the
eight intended0.7.0 version files and no other changes. Treebdfe607ddcb4d17071bced2b20a13396b179c203.
Final canonicalCI passed at06761a7:2572frontend/backend94.71%, fullPG/allgates, diff97/99%; prior candidate226browser evidence remains valid
for identical product behavior, while functional per-merge browser gates are separate.
Actual R integrationSHIP at453a49b/cleanupSHIP ate02479b remain valid. This final fixture
resolution, operator-local wrapper docs/ignore and refreshed facts need a narrow actual
Opus delta review. No newclinical interpretation or product fix was introduced.
