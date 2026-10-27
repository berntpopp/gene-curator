# Final integrated candidate browser checks

Fresh isolated stack at `62fe62e5d7d84d942cf783777f52f8c75b4afde5`, Postgres 5455 / API 8052 / Vite 5190. These are draft-candidate checks, not postmerge or release acceptance. No development-stack state was used.

| Flow | Result | Evidence |
| --- | --- | --- |
| Original core lifecycle | 59/59 | Every role, pending invitation denial, two review rounds, independent approvals, re-curation replacement, admin self-approval denial. Untouched required false defaults save and submit in both forms without the earlier workaround. |
| Authentic successor clinical rows | 19/19 | AR defaults/selector changes/manual same-value/zero/reload; blank segregation Points, LOD/counts score zero with missing-score warning, deliberate zero clears warning. |
| Historical immutable pin | 6/6 | API fixture omits points; real UI load/edit/save keeps points absent and score 2/18. |
| Editable/readonly responsive matrix | 57/57 | 1440 and 390 pixels, light and dark. Local table keyboard scroll, long HGVS, description once, focus below sticky header, Save/Submit mid/bottom, one save per blur/pointer gesture, enum labels/false/zero/PMID links, readonly data unchanged, editable return. |
| Scope, review queue, date and contrast | 17/17 | Full long title and review-count chip fit; pending invitation date matches browser-local ISO date. Admin-role chip contrast 13.57:1 light and 9.56:1 dark. |
| Blocker changes between pointer-down/up | 5/5 | Real publication response held, unknown-PMID blocker appears while pointer held, Save coordinates stay fixed, release sends exactly one PATCH; valid PMID restored through UI. |
| Actual font loading | 1/1 | IBM Plex Sans loaded from the restricted scratch Vite allow list. |

The matrix initially stopped because a non-exact row-1 locator also matched rows 10–14. The selector was corrected and the complete matrix replay passed. This was a harness failure, not a product observation. Full-page images can place sticky elements at their current document offset; separate viewport screenshots preserve the actual visible layout.

The original J candidate failures remain in `../candidateJ/REPORT.md`; this run does not erase them. Known excluded #386 remains documented in candidate E: qualitative preview and stored scoring dispatch disagree. No new claim of fixing or replaying that excluded path is made here. First-active-workflow-pair selection is tracked separately as #448; fixtures use unique precuration schema copies.

Screenshots and result JSON are local ignored artifacts in this directory. No tokens, passwords or auth-state files are copied. Reusable runner source is in `../runner/`; external-service calls are real browser requests where described. These checks do not replace mandatory Opus review or a fresh postmerge gate.

F scoring-warning narrow replay passed **7/7**: legitimate authenticated API fixtures supplied a custom capped model with points999, a legacy JSON string `NaN`, and clinical evidence missing a PMID. Actual UI expanded the warning card, displayed the pinned-range and legacy nonfinite-row warnings and correct PMID wording, then saved/reloaded with the custom capped trace intact. String `NaN` is JSON-representable; nonrepresentable numeric NaN/Infinity and structured logging remain unit/PostgreSQL coverage, not browser claims. Earlier harness assumptions forgot the collapsed Show control, expected different warning wording, and expected custom nonclinical rows to trigger the clinical PMID walker; these were corrected without changing product code.
