# W5R combined candidate checkpoint

Source candidate: `320a33835f847cb135714089858bedb0accc6bcc`, release/v0.7.0, draft452.
Source is frozen after handoff to ops; only a real browser/test finding permits a product fix.
Native integration is not an Opus approval. Full combined CI passed at320a338; fresh browser checks are running.
Focused checks passed84 backend+156 frontend tests, file-size and diff whitespace checks.

## Integration and manual resolution ledger

| Merge commit                             | Input         | Manual resolution                                                                                                                                                                                                                                                |
| ---------------------------------------- | ------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 5db91a904114bd50f489ff6c5d84783b3278af4c | master7b98416 | Test-only SchemaDrivenCurationFormFlows.spec.ts retained both A cancel assertions and existing fixtures                                                                                                                                                          |
| 79c980bb528aa9633fc077d2166d5208818efac0 | D16b5285      | backend/app/core/schema_validator.py retained description/default/default_by union; backend/app/services/review_guards.py used exact finalG32b77d7 composition of D inherited-disease fallback and G network-free checks                                         |
| 496cfaef99aba287fa58cc0208afe317552f88e6 | Eb85d8e0      | Automatic merge, no manual product resolution                                                                                                                                                                                                                    |
| d85ad13ddd8277e2385f97a0e588abd572c47db7 | G32b77d7      | frontend/src/components/dynamic/EvidenceTableField.vue combined sorted-unique-PMID watch with disabled-or-readonly editability; preserves G no retry on unrelated score/reorder and I readonly suppression/editable retry; J automatic-default tracking retained |
| 320a33835f847cb135714089858bedb0accc6bcc | Id0c87bd      | Automatic merge, no manual product resolution                                                                                                                                                                                                                    |

The G merge removed two redundant test comments to keep the existing form-flow test at650
lines; every assertion remains. Initial hook correctly rejected652 lines, then normal hooks
passed. Root's intentional dirty planning Markdown was preserved in f660714 before merges.
No workflow, script, historical golden, migration-number or unrelated product change was added.

Actual Opus must cover the manual product resolutions and connected behavior above in
addition to D/E/G/I fix deltas. A release-only review is insufficient while product changes
remain relative to master. After functional PRs merge, inspect the remaining R product diff;
backport/review any necessary integration fix explicitly rather than silently releasing it.

Full canonical-lock CI passed at320a338: 2572 frontend tests, backend94.71%, full fresh
PostgreSQL and static/type/security/build/repository gates. Standard changed-line coverage
is97% backend/98% frontend. Full CI log: /tmp/W5R-combined-ci.log. Focused logs:
/tmp/W5R-focused-backend.log and /tmp/W5R-focused-frontend.log. Logs/artifacts are local only.
