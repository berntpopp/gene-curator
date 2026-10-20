# 03 — Curation work surface (precuration, curation form, detail, review queue, workflow)

Reviewer lens: senior product designer plus ClinGen GDV curator (SOP v11, GCI conventions).
Run 2026-10-20/21 against the dev stack (UI :5193, API :8051), headless Chromium 1.64, axe-core 4.
App rendered in its **dark theme** in every context (headless default is light), so all screenshots are dark.

Evidence: screenshots in `audit/2026-10-20/screens/03-curation/`, raw JSON (CLS, shifts, load
timelines, axe, task logs) in `audit/2026-10-20/data/03-curation/`. Scripts live in the session
scratchpad (`tools/curation/*.mjs`), not in the repo.

Records created for the tasks (all `UXR-` labelled, no seed record was changed):
precuration `f459bf7f…` (IFT140, kidney-genetics, disease "UXR-IFT140-related ciliopathy"),
curation `fa6db2b5…` (IFT140, now **active**), curation `53d70b0e…` (IFT140, evidence summary "UXR-audit second curation", stuck in review).

---

## Summary

The ClinGen curation form is a real improvement on February: it has tabs, panels for each evidence
category, a live score sidebar, an evidence table and local draft recovery. The surrounding workflow
does not work, though. None of the three primary tasks can be completed through the UI:

| Task (D9) | Result | Clicks | Time | Dead ends |
| --- | --- | --- | --- | --- |
| (a) Alice starts a precuration and moves on to curation | **Fails.** The scope Genes tab is empty for her, so she has to type the URL. The precuration form renders **0 fields**. Her Submit is rejected by the API ("requires one of: admin"). No screen anywhere approves a precuration. I unblocked the task through the API (`/complete`). | n/a | n/a | 4 |
| (b) Add one genetic evidence row with a PMID and see the score update | Works, slowly. Steps: Genetic tab, open AR panel, Add Evidence, fill 4 cells, Save Draft, Submit. **About 500 ms of input lag per keystroke**: 34 characters took 16.9 s, with 141 long tasks totalling 66 s of main-thread blocking. | 10 | 24 s scripted, ~2 min for a human | 0 |
| (c) Bob approves from the review queue | **Fails visibly but not durably.** Review, Approve, Confirm gives an HTTP 500 that the browser reports as a CORS error, and the dialog stays open with no message. The server **did** move the record to Active, while the page still says "In Review". | 3 | 9.8 s | 1 |

**View scores** (mean of applicable D1–D17):

| View / modal | Score |
| --- | --- |
| PrecurationFormView | **38** |
| CurationFormView, ClinGen form (new and edit) | **47** |
| CurationDetailView | **50** |
| Detail dialogs (Submit, Approve, Request Changes, Delete) | **62** |
| ReviewQueueView | **59** |
| FormRecoveryDialog | **62** |

Weighted area score (form and detail ×3, rest ×1): **≈ 51/100**.

---

## Status of the February 2026 curation findings (`audit/UX_AUDIT_REPORT.md`)

| # | Feb finding | Status now |
| --- | --- | --- |
| 1 | One long scroll form, no section navigation | **Fixed in the form.** It now has 5 tabs plus expandable panels. The detail view is still a long stack of cards. |
| 2 | Truncated field labels | **Partly fixed.** Column headers are readable, but cell content is clipped: "UXR-P1 (II-'", "Two nu…", truncated HGVS (`taskB-06-row-filled.png`). |
| 3 | Paternity checkbox label wrapping | Moot. The form now uses tables. |
| 4 | `evidence_summary: Unknown field type: string` | **Still open.** Shown on every curation detail page (`detail-active-naa10-desktop.png`). The generic DynamicForm also renders nothing at all now (see P0-1). |
| 5 | No autosave | **Partly fixed.** localStorage recovery every 5 s works and the restore dialog appears after a reload. Nothing is saved to the server, and the ClinGen form shows no save status. |
| 6 | Left-heavy layout | Fixed. Tables use the full width, but they are cramped at the 9/12 column width. |
| 7 | No inline validation or required markers | **Still open.** The PMID cell accepts "abc-not-a-pmid", the Points cell accepts 9 when the maximum is 3, and typing text into Points silently becomes 0. |
| 8 | Workflow actions show only Delete | **Fixed in the UI** (Submit, Approve, Request Changes exist). **Broken at runtime:** Approve returns 500 and precurations have no approve UI. |
| 9 | No evidence item summaries / collapse | Partly fixed. Categories collapse; there is no per-item summary. |
| 10 | Contradictory evidence buried at the bottom | Fixed (it has its own tab). The automatic "Disputed" rule is wrong (P1-4). |
| P1-6 | Breadcrumbs | **Still open** on the curation form, detail and review queue. Only the precuration banner has a fake breadcrumb. |
| P2-10 | Keyboard shortcuts | Partly fixed. Ctrl+S and Ctrl+Enter work. **Ctrl+Z is advertised but does nothing** in the ClinGen form. |
| Additional | Responsive below 1024 px | Still poor. At 390 px the app bar overflows and the fixed footer covers 110 px (`curation-edit-active-mobile-fold.png`). |
| SOP | Score modification justification | Partly fixed (there is a free-text "Explanation" column). There is no rule that a changed score must be explained. |

---

## PrecurationFormView (`/scopes/:scopeId/genes/:geneId/precuration/new`, `views/curation/PrecurationFormView.vue`, `components/forms/SchemaDrivenPrecurationForm.vue`)

Scores: D1 35 · D2 35 · D3 55 · D4 50 · D5 40 · D6 40 · D7 30 · D8 15 · D9 10 · D10 30 · D11 20 · D12 55 · D13 55 · D14 70 · D15 n/a · D16 50 · D17 15 → **38**

Evidence: `precuration-new-desktop.png`, `-laptop-fold.png`, `-mobile.png`; CLS 0.020 / 0.032 / 0.039 (desktop / laptop / mobile), caused by the form actions shifting at 1.9 s and 2.1 s. axe: image-alt (critical, 1, app logo), color-contrast (serious, 2), aria-tooltip-name (serious, 5). No console errors. The only warnings are router `next()` deprecation messages.

Findings:
- **[P0] The form renders no fields at all.** `stores/validation.ts:96-98` stores the whole API response `{json_schema, field_count, …}`, but `DynamicForm.vue:63` reads `jsonSchema.properties`, which only exists at `.json_schema.properties`. The flat fallback is therefore skipped and no error shows. The curator sees a card titled "Standard_Precuration" with no inputs and **two** button rows: Save Draft / Submit inside DynamicForm, plus Cancel / Undo / Redo / Save Draft / Submit for Review in FormActions. This also blanks every DynamicForm consumer: the detail page's "Evidence Details" and non-ClinGen curation schemas. — Fix: store `response.json_schema` in `generateJsonSchema`, and add a test in `stores/__tests__` asserting `getJsonSchema(id).properties` exists. Show an explicit "schema has no fields" error instead of an empty card.
- **[P0] The precuration Submit always fails for curators, and leaves an orphan draft.** `POST /precurations/{id}/submit` returns 400 "Invalid transition from precuration to review … requires one of: admin" for alice, and fails even for admin. `handleSubmit` (`SchemaDrivenPrecurationForm.vue:316-330`) creates the record first and then submits. Every retry therefore creates another draft, and the user only sees the generic toast "Failed to submit precuration". — Fix: call the endpoint that actually works (`/complete`) or fix the backend transition. Create and submit in one backend call, and show the API `detail` text.
- **[P0] There is no UI to approve a precuration**, yet curation is gated on an approved precuration. `CurationFormView.vue:272-286` sends the user back to `precuration/new`. `precurationsStore.approvePrecuration` exists but no view calls it, and the Review Queue lists curations only. This is a loop with no exit for any curator. — Fix: add precurations to the Review Queue with Approve and Request Changes, or remove the gate.
- **[P0] A saved precuration cannot be reopened.** Save Draft creates the record and redirects to the scope dashboard (`SchemaDrivenPrecurationForm.vue:300`; the code comment says "No precuration edit route exists"). — Fix: add `/scopes/:scopeId/precurations/:id` (view and edit).
- **[P1] "Unknown Gene" in a 48 px headline, and "Gene - Precuration".** The view reads `gene_symbol || symbol` (`PrecurationFormView.vue:49`) and the form reads `gene.symbol`, but the API returns `approved_symbol`. — Fix: map `approved_symbol` once, the same way `CurationFormView.vue:145` does.
- **[P1] Alice cannot reach this page from the product.** Her scope Genes tab says "No genes assigned" (`task-a-01-scope-genes.png`), and the only entry points are `GeneList.vue:431` and `AssignmentDetail.vue:65`. The scope header says "1 of 0 genes curated". — Fix: a "Start precuration" action on the gene catalogue and gene detail for scope curators.
- [P2] The full-bleed primary-blue hero banner with a white DNA icon, white chips and HGNC/NCBI buttons (`PrecurationFormView.vue:33-100`) is decorative and pushes the form below the fold at 1280×720. It also repeats the scope name, which belongs in a breadcrumb. — Fix: a one-line header with gene, scope and stage.
- [P2] The raw schema name "Standard_Precuration" is shown as a title (D7).

## CurationFormView + ClinGenCurationForm (`/scopes/:scopeId/genes/:geneId/curation/new`, `/scopes/:scopeId/curations/:curationId/edit`; `components/clingen/*`)

Scores: D1 55 · D2 50 · D3 60 · D4 55 · D5 50 · D6 60 · D7 55 · D8 55 · D9 35 · D10 45 · D11 30 · D12 45 · D13 40 · D14 40 · D15 20 · D16 55 · D17 45 → **47**

Evidence: `curation-new-desktop.png`, `curation-edit-active-{desktop,laptop,mobile}*.png`, `taskB-01…12*.png`, `flicker-curation-new-filmstrip.png`, `kbd-0{1,2}*.png`, `data/03-curation/taskB-part{1,2}.json`, `axe-genetic-tab-with-row.json`.
- CLS on load: 0.004 (new), 0.022 (edit; header card shift at 1.55 s). CLS during evidence entry: 0.
- Long tasks while filling one row: **141 tasks, 66.5 s total, max 1459 ms**. Typing 34 characters into the HGVS cell took **16.9 s**.
- axe with one evidence row added: **label (critical, 4 per row)**, image-alt (critical), color-contrast (serious), aria-tooltip-name (serious).
- Console: clean.

Findings:
- **[P0] Typing lag of about 0.5 s per key in evidence cells.** Every keystroke runs `EvidenceDataTable.updateField`, which copies the array, emits to the section, which emits to `ClinGenCurationForm.emitUpdate` (spread copy), then `SchemaDrivenCurationForm.handleEvidenceChange` (copy). That triggers a deep `watch` and `useHistory.recordAction` on the whole evidence tree (`SchemaDrivenCurationForm.vue:253-261`), plus the deep `initialData` watch merging back into the form (`ClinGenCurationForm.vue:405-416`), and the localStorage serialisation. This is a feedback loop over the full document on every key. — Fix: commit cell values on `blur`/`change` (or debounce to 300 ms). Remove the deep `initialData` watch after first hydration. Record history per committed cell, not per key. Target: under 16 ms per key with 50 rows.
- **[P0] Three different classification algorithms, so three different verdicts for the same record.**
  - The form uses `scoring.ts:115-122`: Strong at ≥7, Moderate at ≥2, and any contradictory item makes it "Disputed".
  - The detail page uses `curationScores.ts:127-134`: Strong needs ≥12 and genetic ≥4.5, Moderate needs ≥9.
  - The queue and catalogue use the backend `computed_verdict`. That stays `None` (raw_scores `{}`) for curations saved by this form, because the backend engine does not understand the form's `evidence_data` shape.
  - Real case: `fa6db2b5` shows **Limited 1.50** in the form and on the detail page, but **0 / 18 "No Known Disease Relationship"** in the Review Queue. With points 9 the form says **"Strong"**; SOP v11 says Moderate (7–11).
  - SOP v11 rules: Limited 0.1–6, Moderate 7–11, Strong 12–18, Definitive is 12–18 plus replication over time (curator judgment). Disputed and Refuted are expert calls, not an automatic switch.
  - Fix: one source of truth. The backend scoring engine computes the score; the frontend displays it, or uses a shared, tested port. Delete `classifyScores` and `classifyScore`, and make the engine read the shape the form saves.
- **[P1] The score counts things it should not.**
  - (a) An empty row scores 1.5 pts as soon as "Add Evidence" is clicked, with no variant and no PMID, and the verdict jumps to "Limited" (`GeneticEvidenceSection.vue:305-320`, `taskB-04-row-added.png`).
  - (b) Rows with status "Review" or "Contradicts" are still counted (`scoring.ts:28-31` ignores `score_status`; `taskB-07`).
  - (c) Points above the range are accepted: 9 in a 0–3 cell is counted (`taskB-08-points-9.png`).
  - (d) Models (max 4) and Rescue (max 4) are capped separately (`scoring.ts:94,102`); SOP v11 caps Models plus Rescue together at 4.
  - (e) The segregation hint "LOD 0.6-1.2 = 1pt, 1.2-2.4 = 2pts, >2.4 = 3pts" (`GeneticEvidenceSection.vue:158-165`) does not match SOP v11, which awards points by summed LOD and sequencing method (candidate gene vs exome/genome). Points are typed by hand rather than derived from the LOD.
  - Fix: count only `score_status === 'score'` rows with a PMID. Clamp to the column `min`/`max` and show an inline error. Make the shared cap a single function. Derive segregation points from LOD and method.
- **[P1] Unlabelled inputs everywhere in the evidence tables.** The inputs are `variant="plain" hide-details` with no `aria-label` (`EvidenceDataTable.vue:18-71`), which gives axe "label" critical ×4 per row. Focus is invisible: the computed outline is `none`, and plain variant has no field border (`kbd-02-after-add.png`). — Fix: `:aria-label="`${col.label}, row ${index+1}`"`, and use the `underlined` variant with a visible `:focus-within` row highlight.
- **[P1] PMID entry has no lookup or validation.** `PMIDInput.vue` (which validates against Europe PMC) exists but the ClinGen table uses a bare text field. "abc-not-a-pmid" is accepted silently. The GCI shows the citation (first author, year, title) after PMID entry. — Fix: reuse PMIDInput's validator in the PMID cell and show "Smith 2019, *Am J Hum Genet*" under the cell. Validate on blur.
- **[P1] Flicker: the wrong form renders first.** `useDynamicForm` (`SchemaDrivenCurationForm.vue:195-203`) evaluates to `true` before the schema loads (name `''` does not contain "clingen"). The generic layout ("NAA10 - ClinGen_SOP_v11", ScorePreview with a red "No Known Disease Relationship" chip) therefore paints first, then is replaced by the ClinGen form about 0.5 s later. During that half second the header also says "Disease Not specified / MOI Unknown" (filmstrip and `data/curation-new.json` timeline at 1163–2099 ms). — Fix: render nothing or a skeleton while `schema` is undefined (`v-if="schema"`), and keep one skeleton that matches the final two-column layout.
- **[P1] Advertised features do not work.** The sidebar promises <kbd>Ctrl</kbd>+<kbd>Z</kbd> Undo, but the ClinGen form's `handleKeydown` handles only S and Enter (`ClinGenCurationForm.vue:391-402`). The "Add Case-Level Evidence" and "Add Experimental Evidence" quick actions only switch tab and add nothing (`:381-389`; test: rows 1→1). — Fix: wire them to the section add handlers, or remove them.
- **[P1] No save status, and the ClinGen path gives no feedback while saving.** `saving` and `submitting` are set and cleared synchronously around an `emit` (`ClinGenCurationForm.vue:359-375`), so the spinners never show. There is no "Saved 2 min ago" or "Unsaved changes" indicator in the ClinGen path; only the generic path has the `lastSaved` chip. Save Draft took 3.0 s with no visible feedback before the route changed to `/edit`. — Fix: pass `savingDraft`/`submitting` from the parent as props, and add a persistent status line ("All changes saved · 14:02", "Saving…", "Offline – stored locally").
- **[P1] Submit for Review is a disabled button with no reason, and it has no confirmation.** The detail page uses a confirm dialog, but the form submits immediately. The two-step `updateCuration` then `submitCuration` assumes `lock_version + 1` (`useCurationSubmission.ts:146-152`). — Fix: show a tooltip or helper ("Add at least one scored genetic evidence item"), use the same confirm dialog as the detail page, and take `lock_version` from the update response.
- **[P1] The edit page loses the gene.** It shows "Gene: Unknown" because the edit route has no `geneId` and `formGene` is never filled from the curation (`CurationFormView.vue:145, 264-269`; `curation-edit-active-laptop-fold.png`). An **Active** curation opens in a fully editable form with Save Draft, with no "create new version" semantics. — Fix: derive the gene from the curation. For active records, show read-only with a "Start re-curation" action.
- **[P2] Score shown three times.** The header chip, the Summary tab's large classification block plus its 26-row "Evidence Score Summary" table, and the sticky sidebar all show the same 0.0. On the Summary tab the narrative field, which is the only input, is at y≈1600 below a static reference table (`curation-new-desktop.png`). — Fix: Summary tab = narrative first, with the reference table in a collapsible "SOP point guide". The sidebar is the single live score.
- **[P2] The tab bar overflows at 1440 px.** "Lumping & Splitting" sits behind scroll chevrons (`curation-new-desktop.png`), and at 1280 px "Contradictory" is cut. — Fix: shorter labels (Summary, Genetic, Experimental, Contradictory, Lumping) or a left-hand section rail.
- **[P2] The MOI from the precuration is ignored.** The `moi` prop is accepted but unused (`GeneticEvidenceSection.vue:255-259`). The AD/XL panel always opens, even when MOI is AR, so an AR curator needs an extra click and has to scroll past an irrelevant section. — Fix: open the panel that matches the MOI and label the other "not expected for AR".
- [P2] At 1280×720 only about 250 px of form is visible above the fold: the 77 px fixed footer (`FooterBar.vue:2`, `app`), the 64 px app bar, the H1 and the 100 px header card take the rest. The sidebar's `max-height: calc(100vh - 100px)` then clips "Quick Actions" behind the footer. — Fix: a non-fixed footer on work surfaces, a compact sticky header, and no H1 "New Curation" (the gene is the title).
- [P2] At 390 px the app bar overflows (nav items cut off, logo pushed off screen) and the evidence tables need horizontal scrolling inside the card (`curation-edit-active-mobile-fold.png`). Curators work on laptops, so this is lower priority than the laptop fold.
- [P3] The research-use disclaimer modal re-opened over the form mid-session for the curator, intercepting clicks (`taskB-01-curation-new-loaded.png`; another area owns this). On a work surface it costs focus and can swallow a click on Submit.

## CurationDetailView (`/scopes/:scopeId/curations/:curationId`, `views/curation/CurationDetailView.vue`)

Scores: D1 55 · D2 50 · D3 60 · D4 50 · D5 45 · D6 50 · D7 45 · D8 55 · D9 50 · D10 35 · D11 30 · D12 60 · D13 55 · D14 70 · D15 n/a · D16 55 · D17 30 → **50**

Evidence: `detail-active-naa10-*.png`, `detail-inreview-bob-*.png`, `detail-uxr-inreview-alice-*.png`, `taskC-0{2..5}*.png`. CLS 0.003–0.007; page height oscillates 1575→1444→1575→1541 while the schema loads (timeline). axe: image-alt, color-contrast, aria-tooltip-name (app chrome only). Approve: `500 POST /workflow/curation/{id}/transition`, reported by the browser as a CORS error.

Findings:
- **[P0] Approve fails with HTTP 500, yet the transition is applied.** For `fa6db2b5` the stage became `active` server-side while the UI kept "In Review" and the dialog stayed open. For `53d70b0e` the same 500 left it in review; that is probably the "one active curation per gene and scope" rule surfacing as a 500 instead of a 409. `execute_transition` (`backend/app/crud/workflow_engine.py:176-258`) mutates state, then logs and notifies, and an exception after that point becomes a 500. — Fix: one transaction around transition, audit log and notification. Map rule violations to 409 with readable `detail`. Add a regression test for reviewer approve in `tests/api`.
- **[P0] Failures are silent.** After the 500 no toast was visible within 2.5 s. The only signal was a red "2" badge on the footer "Logs" link (`taskC-05-after-approve.png`). The 500 response has no CORS headers, so axios gets a network error with no `detail`. — Fix: add CORS headers on error responses (exception middleware order). Show an inline `v-alert` in the dialog on failure rather than relying on a toast.
- **[P0, domain] A reviewer cannot see the evidence they are approving.** The detail page shows only category subtotals. The "Evidence Details" card renders an empty DynamicForm with the Feb bug "evidence_summary: Unknown field type: string" and stray **Save Draft / Submit** buttons on a read-only Active record (`detail-active-naa10-desktop.png`). There is no PMID, variant, proband, explanation or narrative. A 4-eyes review without the evidence is a rubber stamp. — Fix: a read-only evidence ledger (the same `EvidenceDataTable` with `readonly`), grouped as in the GCI: proband, variant(s), PMID with citation, status, default vs counted points, explanation. Show the evidence summary narrative at the top.
- **[P1] 4-eyes messaging is missing.** The author sees "No actions available" with no reason (`detail-uxr-inreview-alice-desktop.png`). They should see "Waiting for review by another scope reviewer. You can't review your own curation." with a Withdraw option. The reviewer is not told who submitted the record and when, or that approving makes it the public active record for the gene.
- **[P1] Status and MOI rendering bugs.** `getStatusColor` has no `in_review` key (`:644-654`), so "In Review" is grey. `formatInheritance` expects `AD`/`AR` (`:633-642`), but precurations store `autosomal_recessive`, so the raw snake_case is shown. NAA10 is shown as "X-linked Dominant" in purple: the MOI colours (blue/green/purple/orange) are decorative.
- **[P1] Delete sits directly under Approve and Request Changes** in the same stack (`detail-inreview-bob-desktop-fold.png`). The approve dialog asks for no confirmation of what is being approved (no checklist, no score-change diff since submission). — Fix: move Delete into an overflow menu. Give the approve dialog a short SOP checklist (all items have PMIDs, contradictory evidence considered, classification matches the score) and show the evidence summary.
- **[P2] No breadcrumb and no back-to-queue.** The back arrow always goes to the scope dashboard (`:815-817`), even when the user came from the Review Queue. The H1 "Curation Details" is generic and the gene is a chip in a card. — Fix: H1 "IFT140 – UXR-IFT140-related ciliopathy (AR)", with breadcrumb Scope › Curations › IFT140, and back = `router.back()` when the previous page was in-app.
- [P2] The colour block banner (an orange tonal card for "Limited", 64 px numerals) plus a large classification chip duplicates the score breakdown below. The ClinGen classification palette is not used consistently across views (see Review Queue).
- [P2] Dates use `toLocaleString()` ("10/20/2026, 11:59:23 PM"), the queue uses relative time, and other views use "Oct 14, 2025". The Feb consistency finding is still open.

## Detail dialogs (Submit / Approve / Request Changes / Delete)

Scores: D1 65 · D2 70 · D3 65 · D4 65 · D5 60 · D6 n/a · D7 65 · D8 70 · D9 65 · D10 35 · D11 50 · D12 50 · D13 70 · D14 80 · D15 n/a · D16 70 · D17 45 → **62**

Evidence: `taskC-03-request-changes-dialog.png`, `taskC-04-approve-dialog.png`.

Findings:
- [P1] **Focus is not returned to the trigger** on Escape. Focus went to the app-bar brand link. **Tab escapes the dialog:** the order was textarea › Cancel › Approve › "Gene Curator" (app bar). — Fix: Vuetify `v-dialog` with `retain-focus` (default), and make sure nothing sets `:retain-focus="false"` globally. Return focus to the trigger after close.
- [P1] "Request Changes" correctly requires feedback (the button is disabled while empty), but there is no explanation next to the disabled button, and the same `reviewComments` ref is shared with Approve, so typed text carries across dialogs (`:580`).
- [P2] The Approve dialog's score row is a three-column `justify-space-between` text line. It is fine, but it should state "Score unchanged since submission" or show a diff.

## ReviewQueueView (`/review-queue`, `views/curation/ReviewQueueView.vue`)

Scores: D1 60 · D2 65 · D3 60 · D4 45 · D5 50 · D6 65 · D7 60 · D8 70 · D9 55 · D10 60 · D11 n/a · D12 65 · D13 65 · D14 75 · D15 n/a · D16 60 · D17 35 → **59**

Evidence: `review-queue-{desktop,laptop,mobile}*.png`, `taskC-01-queue.png`. CLS 0.007. The header chip flashes "0 pending reviews" then "1 pending review" at 342→422 ms (timeline).

Findings:
- **[P0 via the scoring split] The queue shows "0 / 18 points · No Known Disease Relationship" in red** for curations whose own pages say 1.50 Limited, because it reads the backend `computed_scores` that never populate (see the form findings). Reviewers triage on wrong numbers.
- [P1] Precurations are not in the queue (see the precuration findings), and there is no "Assigned to me" versus "Any reviewer in scope" split, although `/workflow/reviews/my-assignments` exists.
- [P1] Classification colours conflict with the detail page: NKDR is `error` red here but grey on the detail page; Limited is grey here but orange on the detail page (`:346-355` vs `CurationDetailView.vue:590-599`). — Fix: one `classificationColor()` util and tokens, with a single ClinGen-style ordinal scale and no red for "no evidence".
- [P2] The scope shows as the slug "kidney-genetics", not "Kidney Genetics". "Submitted 2/28/2026" uses `updated_at`, not the submission time. There is no age or SLA cue. Search and total pages use different filters: disease is searched, but `totalPages` ignores it (`:276-288`).
- [P2] Each item is a full-width card with a decorative DNA icon and a large "0" numeral. For a queue a dense table is better (gene, disease, MOI, curator, score, verdict, submitted, age), with keyboard row navigation and a split-view preview.
- [P2] "All caught up!" is a green success alert with an exclamation mark, which is mildly gamified copy for an empty queue.

## FormRecoveryDialog (`components/FormRecoveryDialog.vue`)

Scores: D1 60 · D2 60 · D3 65 · D4 50 · D5 60 · D6 n/a · D7 45 · D8 70 · D9 70 · D10 55 · D11 70 · D12 65 · D13 70 · D14 80 · D15 n/a · D16 55 · D17 n/a → **62**

Evidence: `recovery-01-after-reload.png`, `recovery-02-after-restore.png`. A reload 6 s after editing showed the dialog, and Restore brought back the row (score 1.5) and the narrative.

Findings:
- [P2] The copy reads "We found unsaved changes **from recently**". The timestamp is not passed through (`FormRecoveryDialog.vue:12,72`). There is no preview of what will be restored (e.g. "1 genetic evidence row, summary text, 14:02"). — Fix: pass `recoveryData.timestamp`; render "from 2 minutes ago" and a three-line diff summary.
- [P2] There are two warning icons in front of "This will overwrite any current form data", a full-orange title bar, an info alert, and helper text: four emphasis layers for one decision. — Fix: plain dialog, one sentence, primary "Restore", text-button "Discard".
- [P2] After Restore, the expansion panel the user had open (AR) is collapsed, so the restored row is not visible until they reopen it.

---

## "AI smell" / authenticity call-outs

- The **"Quick Actions" card with a lightning-bolt icon** (`ClinGenCurationForm.vue:157-186`) contains two buttons that do nothing beyond switching tab. This is filler UI.
- The **keyboard-shortcut card** advertises an undo that does not exist.
- There are **icon prefixes on every card title and chip**: cog "Workflow Actions", chart "Evidence Score Breakdown", info "Metadata", DNA on every gene chip, folder on every scope. The icons add noise, not meaning.
- **Decorative chips**: "Default: 1.5 pts" / "Range: 0-3" as two chips on every subsection, an "SOP v11" chip, "Draft" chips in two places, and coloured MOI chips.
- **The score as a 64–72 px numeral** appears three times per page (banner, Summary tab, sidebar ring). A ring gauge for a 0–18 ordinal score is a meaningless stat tile.
- The **primary-blue hero banner** on the precuration page.

No emoji and no hard-coded hex colours were found in this area. The only raw values are `rgba(0,0,0,.1)` for `kbd` (`ClinGenCurationForm.vue:446`), which is invisible in dark mode, and `rgba(0,0,0,.02)` in `CurationList.vue:589`.

## ClinGen GCI comparison (D17)

The GCI organises curation around **evidence items attached to publications**: you add a PMID first, see its citation, then score probands or experiments from that paper. The score matrix is a summary page, and every point change requires an explanation. Gene Curator inverts this. You pick a category table and type a PMID into a cell, with no citation feedback, no per-paper view, no "default vs counted points" distinction (only "Points"), no requirement to explain a changed score, and no provenance (who changed what, when). Lumping & Splitting is read-only and fed from a precuration form that cannot be filled. Disputed and Refuted are computed automatically instead of being expert assertions.

---

## Top 10 recommendations

1. **Fix the DynamicForm schema shape** (`stores/validation.ts:96`): store `json_schema`. This single line restores the precuration form and the detail "Evidence Details" card, and resolves the Feb `evidence_summary` warning. Add a store test. (P0)
2. **Make the precuration workflow passable**: a working Submit (or `/complete`), a precuration view/edit route, and precurations in the Review Queue with Approve and Request Changes. Without this the product is a dead end for curators. (P0)
3. **Fix approve**: one transaction, 409 for rule violations, CORS headers on 500s, and an inline error in the dialog. Add an API test with the reviewer role. (P0)
4. **One scoring and classification source of truth** in the backend engine, which reads the form's `evidence_data` shape. Delete `classifyScore` and `classifyScores`. Apply the SOP v11 thresholds, the shared Models+Rescue cap, and LOD-derived segregation. Count only scored rows that have a PMID. (P0/P1)
5. **Remove the input lag**: commit on blur or debounce, drop the deep `initialData` watch after hydration, and record history per committed edit. Budget: under 16 ms per keystroke at 50 rows. (P0)
6. **Read-only evidence ledger on the detail page** with the narrative on top. A reviewer must see PMIDs, variants, points and explanations before approving. (P0, domain)
7. **Evidence table accessibility and validation**: aria-labels per cell, a visible focus ring, PMID validation with a citation preview (reuse `PMIDInput`), and min/max clamping with inline errors. (P1)
8. **Kill the first-paint flicker**: a `v-if="schema"` guard and one skeleton that matches the ClinGen two-column layout. (P1)
9. **Save-state and 4-eyes clarity**: a persistent "Saved · 14:02 / Saving… / Stored locally" line, a reason for the disabled Submit, the same confirm step everywhere, an author banner "Awaiting review by another reviewer", Delete moved to an overflow menu, and breadcrumbs. (P1)
10. **De-clutter**: one live score (the sidebar), the narrative first on the Summary tab, the SOP point guide collapsible, no decorative icons and chips, and a non-fixed footer on work surfaces to win back 77 px at 1280×720. (P2)

## Bold redesign ideas for the curation surface

1. **Paper-first curation ("evidence inbox").** Start from a PMID list (pasted, or imported from PubTator/LitVar). Each paper opens in a split view: citation and abstract on the left, typed evidence cards (Proband, Segregation, Case-control, Function, Model, Rescue) on the right, pre-filled with SOP defaults. The score matrix becomes a derived summary, as in the GCI, but faster.
2. **A live SOP score matrix as the persistent right rail.** It is the canonical ClinGen summary matrix (rows = categories, columns = default / range / counted / max). Each cell is clickable to filter the evidence ledger, and a cell glows when an item is above default and still lacks an explanation. It replaces the ring gauge and the duplicate tables.
3. **Review mode as a diff, not a re-read.** The reviewer sees the evidence ledger with per-item Accept / Query toggles and inline comments anchored to items. "Request changes" sends the anchored threads back, and the curator sees them as to-dos on the form. On approval the record shows a signed provenance block (curator, reviewer, date, SOP version, score snapshot).
4. **Keyboard-first entry grid.** A spreadsheet-like evidence grid (arrow keys, Enter to edit, Tab to the next cell, Cmd+Enter for a new row, `/` to jump to a category) with typeahead for variant type, an HGVS syntax check, and PMID lookup in place. Undo and redo are per committed cell. This targets about 20 s per evidence row.
5. **Gene workspace instead of three routes.** A single `/scopes/:s/genes/:g` workspace with a stage rail (Entry › Precuration › Curation › Review › Active) where each stage is a panel of the same page. That ends the redirects between precuration and curation and the "Unknown Gene" headers, and keeps the gene, disease and MOI always in a compact sticky header.
