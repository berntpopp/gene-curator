# Combined R browser acceptance

Exact product candidate `320a33835f847cb135714089858bedb0accc6bcc`, fresh isolated Postgres5455/API8052/Vite5190. This is candidate integration evidence, not a release or postmerge gate. Mandatory actual Opus fix-delta reviews remain pending; browser acceptance does not replace them. No product changes were needed during this run.

| Check | Result | Scope |
| --- | --- | --- |
| Canonical workflow | 59/59 | Every role, untouched required-false defaults, two review rounds, independent approvals, re-curation and D1 |
| D inherited disease | 16/16 | Flat/nested linked disease submits; missing source refused; no inherited evidence copied |
| E pending score panel | 17/17 | Stable aside/checklist, debounce/request skeleton, stale-response protection, error termination |
| G affected flow | 16/16 | Save during lookup, unknown blocker, known-PMID submit, readonly lazy view and return to editing |
| G lifecycle fixes | 7/7 | No retry on score edit; intentional blur retry; completed result survives conditional hide/remount |
| I stored MONDO label | 6/6 | Exact stored susceptibility label restored once, ID/evidence unchanged, free-text suggestions narrowed |
| Clinical successor | 19/19 | AR defaults/manual overrides, empty rows, segregation null warning versus explicit0, save/reload |
| Historical pin | 6/6 | Loaded absent points remain absent, historical scoring retained, save preserves absence |
| Responsive evidence/actions | 57/57 | 1440/390 light/dark, horizontal table scroll, long HGVS, readonly values, stable pointer target |
| Scope/review controls | 17/17 | Full titles, review counts, role contrast, local invitation date |
| Pointer/blocker timing | 5/5 | Blocker appears during pointer-down, Save target stays fixed, exactly one save |
| Actual loaded font | 1/1 | IBM Plex Sans loaded |

D: complete flat/nested linked precurations permit actual UI submit with absent readonly entity_definition in curation evidence. Supplementary authenticated reads verify only own evidence is stored and precuration evidence is unchanged. Missing linked disease returns400. The test awaits the actual successful PUT-save response before POST-submit, then verifies the refused transition preserves that exact lock_version, evidence and workflow state.

E: actual backend preview responses are held and released. The same aside DOM node and width survive edits; old numbers vanish immediately; skeleton and checklist remain through debounce/request. A superseded response cannot restore old numbers or terminate pending; the latest response restores the score. A controlled503 verifies pending ends with explicit unavailable score.

G: controlled lookup failures exercise retry behavior; actual service resolution verifies the recovered citation. Conditional table removal/remount preserves the completed shared result without a redundant request. The exact aborted concurrent child-batch race remains covered by unit tests; this browser run does not claim to reproduce that race. Readonly-to-editable behavior uses an independent reviewer requesting changes through the UI.

I: the real ontology service resolves MONDO:0009100 through actual DynamicField without a separately supplied diseaseName prop. The selected ID and persisted evidence stay unchanged. Actual free-text diabetes search excludes that susceptibility term. Native tests verify the upstream human-branch parameter for free text/partial IDs; browser checks verify observable results, not upstream request internals. No external service blocker occurred.

Responsive checks include keyboard focus visibility, nested horizontal table scrolling at390px, full HGVS text, readonly enum labels/false/zero/PMID links, then unchanged editable values. Save/Submit remain visible at mid/bottom positions in both themes. Pointer-down through blur/status or blocker updates keeps the Save target fixed and produces exactly one save.

Fixture setup and read-back assertions use authenticated APIs and are distinguished from actual UI actions. Clinical fixtures are synthetic and test the already specified methodology behavior; this run makes no new SOP interpretation. Existing excluded#386 qualitative preview/save mismatch was not fixed or claimed passing here; prior E25/26 evidence remains separately recorded. No broad scoring audit or excluded-scope repair was added.

Harness corrections retained as ignored diagnostics: JSONB property ordering now uses structural equality; D distinguishes the intentional PUT-save from rejected POST-submit; a dedicated G reference fixture replaced a missing-reference fixture; G readonly assertion uses I's intended PMID link instead of the old textbox; I fixture activates its derived schema, and free-text typing differs from the selected label (which intentionally triggers no query). Original diagnostics remain preserved; no behavioral assertion was skipped or weakened. G's16 assertions comprise the first11 successful actions and the corrected five-check readonly/editable continuation on the same fixture.

All generated JSON/screenshots/helpers remain ignored locally. No auth state or tokens copied. Sanitized reusable helpers persist under the ignored runner directory; only Markdown reports may be copied into the release PR. Current stack remains at the exact product candidate with API session6625 and Vite session84538, database volume preserved.
