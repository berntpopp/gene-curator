# I resumed independent review

Actual claude-opus-5-5, is_error=false, session `45f7fe7a-786c-4d1b-a793-5acaf635a108`.

**Verdict: SHIP at pinned head `62fe62e5d7d84d942cf783777f52f8c75b4afde5`.** Nothing blocks the merge. I found one small display regression that can be fixed later.

**What this change does:** Readonly forms now show stored values as plain, selectable text instead of greyed-out inputs. Evidence tables scroll inside their own box. Form action bars and the workspace header stay on screen while scrolling. New MONDO suggestions come only from the human-disease branch (`directAncestor=…MONDO_0700096`). It also fixes local invitation dates, the role-chip contrast and text wrapping in headers.

I read the I-only patch and the connected current files: `DynamicField`, `DynamicNestedField`, `EvidenceTableField`, `ReadonlyValue`, `MONDOAutocomplete`, `PubmedLinkButton`, `componentRegistry`, `WorkspaceHeader`, `format.ts`, `useRoleColors`, the MONDO seed field (`016`) and the MONDO section of the plan.

**Scope groups**
1. **Table overflow, HGVS, single description:** Done. The outer box scrolls (the inner Vuetify wrapper scroll is turned off), and it can be focused with the keyboard and has a label. Text cells have a minimum width, and long values break with `overflow-wrap: anywhere`. The description is printed once because `DynamicField` skips it for type editors and the table caption shows it.
2. **Header and chip clarity:** Titles and breadcrumbs now wrap, including on the review queue.
3. **Role contrast:** The role chip is now `variant="flat"`, so the text uses the matching on-color for each role colour.
4. **Readonly display vs disabled input:** Readonly fields render text, not inputs, and every write path (`updateValue`, `onInput`/`onChange`, `addRow`/`removeRow`, nested emits) returns early. PMID lookups do not run while readonly and run again when the form becomes editable. `formatValue` keeps `false` as "No", `0` as "0", and shows `null`/`''` as "none". The readonly load path in `DynamicForm` skips declared defaults, so stored values are shown as they are.
5. **MONDO suggestions:** The human-branch filter runs before pagination in one request, with no name matching and no extra query per result. The watcher now requires an exact ID match and ignores late responses, so a stale or unrelated first hit can no longer replace the label, and nothing is emitted when the lookup fails. One gap remains (finding 1).
6. **Invitation dates:** These use the shared `formatDate`, which works in local time.
7. **Sticky actions:** The blocker text stays below the buttons, so the Save button does not move between mousedown and click (the new spec checks this). The header is only sticky when there is a draft and the page is not readonly.

**Findings**

1. **Should fix (not blocking): a saved susceptibility term loses its label in the edit form** (`frontend/src/components/evidence/MONDOAutocomplete.vue:265-289`, `frontend/src/components/dynamic/DynamicField.vue:10-19`)
   - **Problem:** `DynamicField` passes only `modelValue` to the component, never `diseaseName`. The watcher's ID lookup now goes through the human-only filter.
   - **Trigger:** A curator opens an existing precuration whose stored `mondo_id` is MONDO:0009100.
   - **User impact:** The field shows `MONDO:0009100 MONDO:0009100` instead of "type 1 diabetes mellitus 1", and the info tooltip is missing. The ID itself is kept and the separate `disease_name` field is still shown, so no data is lost. The new spec claims the label is kept, but it passes `diseaseName` directly, which the real form never does.
   - **Smallest fix:** In `ontology_service.search_mondo`, leave out `directAncestor` when the query is exactly one `MONDO:\d{7}` ID. An exact-ID lookup is not a suggestion, so this matches the plan's "suggestions only" rule. Change the parametrised backend test so the `MONDO:0007258` case asserts the filter is absent.
   - **Regression test:** Mount it through `DynamicField` (no `diseaseName`), have the mocked lookup return the stored term, and assert the label appears.
   - **If we skip it:** Only already-stored susceptibility terms show the bare ID while editing.

**Smaller issues, no action needed**
- Readonly MONDO and OMIM fields show the bare ID. This is acceptable for MONDO because `disease_name` is a separate field in the seeded schema; OMIM has no such field.
- A readonly enum option with no label shows the raw value, while the editable select shows a humanised one.
- The MONDO hint gets a double period if a schema description already ends with ".". The seeded schema has no such description.

**Limitations**
- I ran no tests or browser checks. All gate and browser counts in your message are reported evidence that I did not verify.
- Nothing reserves space for the sticky header or action bar when a field gets focus (no `scroll-padding`/`scroll-margin` anywhere in the frontend). Whether a focused field ends up hidden behind them, especially with shift-tab at 390 px or in Firefox, depends on how the browser scrolls to focus. I could not confirm this either way.
- The parent commits merged after this delta were not reviewed again, as you asked.

Root assigned the stored-term label regression for a scoped fix, followed by independent Opus delta review and browser recheck. Raw JSON remains local and ignored.
