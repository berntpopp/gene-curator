# Wave 10 UI monkey test + UX rating, round 1 (origin/master 14753262, UI :5190, API :8052)

Tester: UI monkey (Playwright MCP, Chromium, timezone Europe/Berlin). Desktop 1440x900 and phone 390x844.
Genes used: HNF1B, COL4A5, COL4A4, APOL1, CLDN16 (A-M only). Users created: mui-rev1@example.org,
mui-rev2@example.org (kidney-genetics reviewers). Schemas created: "MUI Mini Curation" (published v2),
"MUI One Section". The KGDB Mendelian Precuration label change from flow 2 was reverted by re-importing the
original bundle (methodology now has two extra versions, content identical to the bundle). Leftover drafts: a duplicate
HNF1B precuration draft and an incomplete APOL1 precuration draft.
Screenshots (`mui-*.png`): /tmp/claude-1000/-home-bernt-popp-development-gene-curator/9c28a4b8-bf13-4193-9f9d-0a3aefa339b3/scratchpad/monkey-ui/

## Bug table

| id | sev | flow | steps | expected | actual | screenshot | suspected component |
|---|---|---|---|---|---|---|---|
| B1 | critical | 3 | Open any KGDB curation detail page (`/scopes/:id/curations/:cid`), e.g. Review queue "Review" on HNF1B; also WT1 (in review) and UMOD (active) | Read-only curation with Approve controls | "Something went wrong: Cannot read properties of undefined (reading 'flatMap')" at `TabContent.vue shownFields`; reviewer cannot open or approve any KGDB curation | mui-90-review-page.png, mui-91-review-crash.png | `components/dynamic/TabContent.vue:shownFields` gets a component-only section (ScoreSummary) without `fields` on the read-only path (`CurationEvidenceReadonly` / `normalizeDefinition`; likely since ca376e86 "one-section schemas render flat") |
| B2 | high | 3 | KGDB curation, Genetic evidence, add proband rows leaving Points blank (P2: c.494G>A heterozygous, primary paper, PMID) | Row scores the type default (1) | Row scores 0. Form stores `"points": null`; `default_points` does `row.get("points", default)` -> None -> 0. Only rows hit by a positive points_when rule score. HNF1B total 1.5 instead of 2.0 (P1 1.5 + P2 1, group cap 2) | mui-84-probands-filled.png | `backend/app/scoring/point_model.py:default_points` (treat blank/None as missing) |
| B3 | high | 1 | Build a schema in the UI with sections (field ids land flat in `evidence_data`), point model section `genetic`, type path `probands` | Point model scores the form's evidence table | Point model reads `evidence_data[section.key][path]`; UI-built sectioned schemas store `evidence_data.probands`, so nothing can ever score. Validator and Publish report say "No errors". Tests only pass with hand-written `{"genetic":{"probands":[...]}}` | mui-38-run-tests.png, mui-42-publish.png | `point_model.py` section lookup vs `normalizeDefinition` flattening; add a validator check that every type path resolves to a field |
| B4 | high | 3 | Start a precuration for APOL1 wanting the KGDB Susceptibility pair | Curator can choose the Susceptibility pair (or relationship type routes to it) | Precuration form always uses the scope default pair; "Relationship type" offers only "Mendelian". Susceptibility pair unreachable from the UI | mui-93-apol1-precur.png | `views/curation/PrecurationFormView.vue` (uses `default_workflow_pair_id` only) |
| B5 | high | 3 | Second precuration for HNF1B + same MONDO + AD, Save draft | Clear refusal: "This disease entity already has an open or approved precuration in this scope" with a link | Snackbar "Failed to save draft"; the 409 detail (message + precuration_id) is dropped; the draft (saved before MOI was set) is left as an orphan | mui-77-duplicate.png, mui-78-duplicate-moi.png | precuration save error handling (`errorMessage` ignores `detail.message`) |
| B6 | high | 5 | User Management, type in "Search users..." | List filters | `TypeError: query.trim is not a function` (console); list unchanged. `@input` passes the InputEvent to `debouncedSearch` | mui-54-user-search-broken.png | `views/UserManagement.vue:40` (`@input="debouncedSearch"` should pass the model value) |
| B7 | medium | 1 | Templates > New Template, open editor | Can add sections | New schema starts as a flat map with `example_field`, so "Add section" is hidden; it appears only after deleting the example field. No hint | mui-05-builder-edit.png, mui-07-section-added.png | template creation default `field_definitions` / `fieldModel.readLayout` |
| B8 | medium | 1 | Scoring > Sections > Evidence type, Rule "Case row" | Rule configurable in the UI | Check: "case_row requires blank_at"; no `blank_at` input exists in the builder | mui-31-diagnostics.png | `scoring/PointModelTypes.vue` (no blank_at column) |
| B9 | medium | 1/3 | points_when "is one of" on a Multiple-choice column (variant_class in [lof]); "is filled in" on a List column holding `[]` | Rule matches the list value; empty list is not "filled in" | `in` never matches a list cell (2.5 instead of 3.5 in the builder test); `present` treats `[]` as filled (1.5 awarded) | mui-38-run-tests.png | `point_model.py:_holds` and `_blank` |
| B10 | medium | 3 | Any KGDB evidence table (Probands, Detectability, Resources) | Columns in authored order (proband_label, variant, ...) | Columns ordered by jsonb key length: PMID, Phase, Points, De novo, Variant, ..., Proband 9th; Detectability starts with "Tools", Challenge 4th | mui-83-proband-row.png, mui-87-diagnostics.png | `columns` maps lose order (jsonb reorders keys); no `order` per column |
| B11 | medium | 1 | Templates page at 390 px | Header actions wrap | "New Template" button off-screen; page scrolls horizontally (scrollWidth 527 vs 375) | mui-46-phone-templates.png | `views/SchemaManagement.vue` header flex |
| B12 | medium | 3 | Score trace on the curation form | Trace shows `rules_applied` (which points_when / step fired per row) | `ScoreTrace.vue` never renders `rules_applied` or `capped_groups`; curator cannot see why P1=1.5, P3=0 | mui-86-show.png | `components/curation/ScoreTrace.vue` |
| B13 | medium | 3 | New precuration form, untouched | Neutral form | Red "Required field is missing" on every required field plus a "Form Validation Errors" box before any input | mui-70-start-precur.png | DynamicForm validation on mount |
| B14 | medium | 3 | Required booleans in KGDB precuration ("ClinGen has curated this entity", "Lumping or splitting applied") | "No" is an explicit answer | A checkbox cannot express "No": must tick and untick to clear the error | mui-70-start-precur.png | DynamicField boolean renderer (Yes/No control for required booleans) |
| B15 | low | 1/3 | List cells (PMIDs, Sources): type "31000006, 31000007" + Enter | Two chips | One chip "31000006, 31000007" | mui-22-preview-cells.png, mui-88-diag-list-cells.png | array cell combobox (no delimiter split) |
| B16 | low | 1 | Rename a field in a never-published new template | No published-version warning | Dialog says "This schema has a published version" (creation auto-publishes version 1 with example_field) | mui-40-rename-applied.png | `SchemaEditor.vue` `published = versions.length > 0` |
| B17 | low | 1 | Schema editor sidebar Statistics while editing | Live count | "Total Fields: 1" while 4 fields exist; "Last Modified: —" even after save | mui-17-fields-list.png, mui-41-saved.png | `SchemaEditor.vue` statistics card |
| B18 | low | 3 | My work / curation header after AD precuration | "HP:0000006" or "Autosomal dominant" | "Hp:0000006" | mui-81-curation-form.png | MOI title-casing helper |
| B19 | low | 5 | User Management pagination after creating users | Stable order | Order changes between loads (no ORDER BY); new users jumped to page 1, page 2 repeated earlier rows; header "10 users" stale until refresh | mui-52-users.png | `/users` list endpoint ordering |
| B20 | low | 3 | Review queue as reviewer in a scope with AI off | No dead link | "AI second view" link leads to "No AI second view here" | mui-92-second-view.png | review queue row actions |
| B21 | low | all | Load /login anonymously | No errors | 3 console 401s (`/auth/refresh` x2, `/auth/me`) | — | auth bootstrap |
| B22 | low | 1 | Templates / Workflows version column | "alpha", "SOP v11" | "valpha", "vSOP v11" (blind "v" prefix) | mui-01-schemas.png, mui-99-workflows.png | version formatter |

Severity count: critical 1, high 5, medium 8, low 8.

Verified OK: show_when rename propagation; reorder, delete; Save; Publish report + impact + disabled-while-editing caption;
one-section schema renders flat; seeded ClinGen SOP, ClinGen_SOP_v11 and ClinGen Precuration saved unchanged (byte-identical JSON);
import plan Unchanged / Publish new version / error bundle shows 2 errors with Import disabled and writes nothing; precuration
approve from queue; segregation LOD 3.2 -> 2 points (step rule); review flags (band_margin, hotspot) in the score panel; intake
paste resolve (not found, repeat), curator assign, bulk due date shows 2026-12-01 in Europe/Berlin, re-intake keeps Alice;
scope role add/change/remove, removed role disappears, own account read-only; catalogue sticky gene column (phone + desktop);
Disagreements preset sets `?agreement=disagree`; Access tokens title.

Not tested: reviewer Approve page and its review flags, approval by a second reviewer, corrector-cannot-approve (all blocked by
B1); disease correction dialog (only shown for a legacy disease gap; no such record reachable from the UI); intake due date at
paste time (the dialog has no due-date field; only the bulk bar sets it).

## UX rating (senior product designer lens)

### Flow 1: Schema builder: 4/10
Top problems
- Two models glued together: form sections (Fields tab) and point-model sections (Scoring tab) share a name but not data;
  nothing connects a point-model "Evidence path" to a field. Free-text paths (`table.path`), free-text condition fields, and a
  "Points entered" rule label for "no rule" demand JSON knowledge (B3, mui-27-pm-type.png).
- Empty-state trap: a new template starts with `example_field` in a flat map, which hides "Add section" (B7).
- Cramped scoring table at 1440 px: the editor gets 2/3 of the width, Evidence path shows "table.pa", Category key "segregati",
  condition Field "va"; Default/Min/Max inputs have no visible box (mui-32-step.png).
- Tests require hand-written evidence JSON and failures give no reason ("expected 3.5, got 0" for missing `pmid` / wrong nesting).
- Terminology drift: "Template" (nav, list, create dialog) vs "Schema" (editor, fields); "Version 1.0.0" field vs "Publish version 2".
- "View Schema" page at an `/edit` URL with a separate Edit button; after Create the list stays put and the new row is on page 2.
- Type list has near-duplicates (Text/String, Single choice/Choice (enum)) and offers Evidence table as a column type; "1 categories".
Ranked fixes
1. Replace free-text Evidence path / condition Field with pickers fed by the schema's evidence tables and their columns.
2. Bind point-model sections to form sections (or store sectioned data under section ids) and add a validator error when a type path resolves to nothing (fixes B3).
3. New Template opens the editor directly on an empty sectioned schema ("Add your first section" empty state).
4. Give the Scoring tab full width (move Statistics/Actions into a header bar); use a card per evidence type instead of a 9-column table.
5. Tests: build evidence with the Preview widgets; on failure show the per-row trace (rules_applied, uncited reasons).
6. One noun ("Methodology" or "Template") everywhere; drop the free "Version" field or label it "Display version".

### Flow 2: Import methodology: 7/10
Top problems
- The button opens the OS file picker directly; no explanation of a bundle or what will happen.
- Plan rows say "Publish new version" without saying what changed (a one-label change gives no diff).
- With errors, rows still read "Publish new version" next to a red error list; the "Scope default" row vanishes.
- Success toast "Imported 1 change(s)" does not name the template or new version.
Ranked fixes
1. Per-row diff summary (fields added/removed/relabelled, scoring changed) with an expandable JSON diff.
2. In error state, mark rows "Blocked" and anchor each error to its row.
3. Toast: "KGDB Mendelian Precuration published as version N" with a link.
4. Open a small dialog first (drop zone + "What is a methodology bundle?") instead of the raw file chooser.

### Flow 3: KGDB curation: 3/10
Top problems
- Reviewers cannot open KGDB curations (B1); scoring silently drops default points (B2); Susceptibility pair unreachable (B4).
- New precuration opens with red errors everywhere and a validation box (B13); required booleans need a tick-untick dance (B14).
- Duplicate entity refusal is a generic "Failed to save draft" (B5).
- Evidence tables: 12 columns in scrambled order (B10) inside a half-width card with horizontal scroll; PMID column is the widest.
- Score panel appears only after the first edit (layout shift); tab badges are empty grey pills; "Hp:0000006" in the header.
- Score trace lacks the per-row "why" (B12); hotspot text "1.5 of 1.5 proband points come from 2 variants" when one variant scored.
- Mixed field styles in one form (outlined MONDO, filled others); OMIM/Orphanet not prefilled from the xrefs the MONDO picker shows.
Ranked fixes
1. Fix B1 and B2 (blocking correctness).
2. Pair choice at precuration start when the scope has more than one pair (or route by Relationship type), with a one-line explanation.
3. Validate on blur/submit only; replace required checkboxes with Yes/No segmented controls.
4. Surface 409 details inline: "HNF1B / MONDO:0007669 / AD already has an open precuration by Alice" + Open link.
5. Evidence rows: authored column order, sticky first column, a row drawer for long rows, per-row points chip naming the rule that set it.
6. Keep the score panel mounted from the start with a "0 points" empty state.

### Flow 4: Intake: 7/10
Top problems
- No due date at paste time, so "assign with deadline" needs a second pass through the bulk bar.
- Resolve step does not flag genes already in the scope; "1 already in scope" appears only after adding, silent about the curator kept.
- My work does not show the due date; "Stage" is "—" in My work but "Precuration" in the scope gene list for the same assigned gene.
Ranked fixes
1. Optional due date (and priority) next to "Assign to curator" in the intake dialog.
2. In the resolve table mark "Already in scope (curator: Alice Smith, kept)".
3. Show Due in My work and align stage naming ("Assigned" vs "Precuration").

### Flow 5: User Management / scope roles: 6/10
Top problems
- Search broken (B6); pagination order unstable (B19).
- Scope-role changes apply immediately while the dialog still has Cancel/Update, so Cancel suggests an undo that does not exist; removing a role has no confirm or undo.
- Scope picker shows slugs (kidney-genetics), not display names; Create user cannot set scope roles.
Ranked fixes
1. Fix search; sort by name with stable pagination.
2. Separate "Scope roles" into its own panel with per-row save state, or stage changes until Update; Undo on the removal toast.
3. Display names in the scope picker; allow a first scope role in Create user.

### Flow 6: Catalogue / tokens / workflows: 7/10
Top problems
- Catalogue: "Disagreements" preset hidden inside the "Scopes shown" menu; classification casing inconsistent ("likely" vs "Limited"); strength bars have no legend.
- Workflows: schema links use browser-default blue/visited purple; dates wrap "2026-10-\n31"; no column for scopes using a pair.
- Phone: Scope dashboard stacks four full-width stat cards before the gene list; Templates header overflows (B11).
Ranked fixes
1. Promote Disagreements to a chip beside Agreement/Classification.
2. Theme link color and nowrap (or relative) dates in admin tables; add "Used by" scopes.
3. 2x2 stat grid on phone; wrap admin page header actions.
