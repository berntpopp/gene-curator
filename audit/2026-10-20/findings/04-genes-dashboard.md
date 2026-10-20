# 04 · Data browsing and personal work views

Reviewer: senior product design / UI-UX (agent 04). Date: 2026-10-20. Protocol: `../PROTOCOL.md`.
Scope: Dashboard, Gene Catalogue (`/genes`), Gene Database (`/admin/genes`), Gene Detail, Gene Summary,
My Work (`/assignments`), Create Assignment, Assignment Detail, Validation Dashboard, and the dialogs opened from them.

## Method and evidence

- Headless Chromium (Playwright 1.64), roles admin / curator (alice) / reviewer (bob), 1440x900 and 390x844.
  The app defaults to the **dark theme** (`main.ts:22`), so dark is the primary capture; light captures are prefixed `light-`.
- Scripts (scratchpad `tools/04-genes/`): `views.mjs` (baseline: screenshot, CLS load+3 s, console, failed requests, axe),
  `scale.mjs` (600 synthetic rows via `page.route`, forced empty/500 states, slow API, interaction CLS),
  `dialogs.mjs` (every modal: focus on open, Tab, Escape, focus return; keyboard tab order; light theme; task timing),
  `task1.mjs`, `ttc.mjs` (time to content).
- Screenshots: `screens/04-genes/` (`<role>-<view>-<desktop|mobile>.png`, `s-*` scale, `st-*` forced states, `dlg-*` dialogs, `light-*`, `task1b-*`).
- Raw data: `data/04-genes/views.json`, `scale-states-interactions.json`, `dialogs-keyboard-tasks.json`, `task1-find-gene-open-curation.json`, `time-to-content.json`.
- No data was written: dialogs were opened and cancelled; the validation dialog was fed by seeding the in-memory Pinia store.
- D15 (Lighthouse) is not scored here; it needs a production build and is measured centrally. Time to first content on the dev server was 0.26-0.62 s for all views (`time-to-content.json`).

### Cross-view measurements

| View | CLS load (desktop) | CLS worst case | axe desktop (serious/critical) | Console / network |
| --- | --- | --- | --- | --- |
| Dashboard | 0.006-0.012 | 0.03 (mobile) | tooltip-name, contrast x2, image-alt (shell) | clean |
| Gene Catalogue | **0.074-0.079** | **0.44** (catalogue API 2.5 s slow) | + **button-name x2 (critical)**, tooltip-name x5 | **500 on `/gene-catalogue/filters/scopes` on every load**, surfaced as CORS error |
| Gene Database | 0.009 | 0.02 | shell only | clean |
| Gene Detail | 0.004-0.009 | - | shell only | clean |
| Gene Summary | 0.009 | - | shell only | 404 on `/genes/:id/summary` for every private-scope gene |
| My Work | 0.006-0.011 | **0.10** (600 rows) | + **label x2-3 (critical)**, tooltip-name x3 | clean |
| Validation | 0.009 | - | + aria-input-field-name | clean |

Shell-level axe issues seen on every page (img without alt, `.clickable`/`.version-info` contrast, unnamed tooltip `#v-tooltip-v-35`) belong to the app-shell review but count against D12 here as well.
Horizontal scroll at 390 px: Dashboard (scrollWidth 468) and My Work (465), both caused by the page-header CTA not wrapping.

### Task timing (D9)

| Task | Result |
| --- | --- |
| T1 Find gene NAA10 and open its current curation (admin) | **Not completed** in 5 clicks / 14 s. Catalogue search **returns HTTP 500** (all genes stay listed, a "Network Error" banner shows). Path that works: Gene Catalogue, eye (quick view), arrow "View scope", Curations tab, row, then the row's "Curation actions" menu. The gene page itself has **no link to any curation**. A Linear-grade target is 2 actions: type, Enter. |
| T2 From Dashboard reach my next assigned task (curator alice) | **Not completed.** Dashboard shows no work. "View Assignments" opens a table of assignments for the whole scope set; the eye opens a read-only dialog whose only button is "Close". `AssignmentDetail` (which has "Start curation") is not linked from My Work at all. |

---

## Per-view scores and findings

### Dashboard (`/dashboard`, `views/Dashboard.vue`, `components/dashboard/PendingInvitations.vue`)
Scores: D1 45 · D2 40 · D3 60 · D4 50 · D5 55 · D6 45 · D7 50 · D8 50 · D9 30 · D10 40 · D11 n/a · D12 60 · D13 50 · D14 82 · D15 n/a · D16 40 · D17 25 → **view score 48**
Evidence: `admin|curator|reviewer-dashboard-{desktop,mobile}.png`, `st-error-dashboard.png`, `st-slow-dashboard.png`; CLS 0.006-0.033; hscroll 468 px at 390 px.
Findings:
- [P1] **The dashboard does not answer "what should I do next?"** for any role. It shows scope chips, an invitations card and four navigation buttons. Admin, curator and reviewer see the same page (only "Schema Management" differs). No assigned genes, no drafts, no "awaiting my review", no due dates, no counts. Fix: replace the left card with a "My queue" list built from existing endpoints: `/gene-assignments/curator/{id}/assignments` (assigned genes plus `has_active_work`), `/workflow/reviews/my-assignments` (reviews waiting for me) and the user's draft curations. Sort by state (Changes requested, Review waiting, Draft, Not started). Each row deep-links to the curation or precuration. `views/Dashboard.vue:19-49`.
- [P1] **Errors are reported as empty data.** When `/scopes` returns 500, the card says "No scopes assigned" (`st-error-dashboard.png`); the error is only logged (`Dashboard.vue:112-117`, empty state at `:42-45`). Fix: track `error` and show an inline alert with Retry. Never present a failure as a true empty state.
- [P2] Duplicate primary actions: "Start new curation" (header) and "New curation" (Quick Actions) both go to `/scope-selection`. Quick Actions repeats the top navigation in four different colours (primary/secondary/info/warning outlined, `Dashboard.vue:62-83`). Delete the Quick Actions card. Keep one primary CTA.
- [P2] Scope chips are coloured `success` for active scopes and show no role, gene count or open work (`Dashboard.vue:31-40`). Replace them with a compact scope list: name, my role, open curations, waiting reviews.
- [P2] Mobile: the header CTA does not wrap, which causes horizontal scroll (468 px). Stack the header under `sm` or use an icon button.
- [P3] "Welcome back, Admin User" is filler. Use the space for a status line, for example "3 curations need you".
- AI-smell: the four rainbow outlined buttons, the 48 px green check for "No pending invitations" and the generic welcome line are template defaults, not product decisions.

### Gene Catalogue (`/genes`, `views/GeneCatalogueView.vue`, store `stores/geneCatalogue.ts`)
Scores: D1 50 · D2 48 · D3 55 · D4 40 · D5 50 · D6 55 · D7 45 · D8 60 · D9 25 · D10 35 · D11 n/a · D12 45 · D13 45 · D14 55 · D15 n/a · D16 40 · D17 45 → **view score 46**
Evidence: `admin-catalogue-desktop.png`, `i-catalogue-real-after.png` (dark expanded row), `light-catalogue.png`, `s-catalogue-600.png`, `s-catalogue-600-mobile.png`, `dlg-catalogue-quickview.png`; CLS 0.074-0.079 on load, **0.44** with a slow catalogue API (`st-slow-catalogue`); axe button-name x2 critical.
Findings:
- [P0] **Gene search is broken.** `GET /gene-catalogue/?search=NAA10` returns 500, so typing in "Search genes" leaves every row in place and shows "Network Error". Root cause, confirmed: `backend/app/crud/gene_catalogue.py:218-219` uses `.cast(str)`, and SQLAlchemy raises `TypeError: Object '' ... is not a TypeEngine`. Fix: `cast(String)` (or `func.array_to_string`). Add an API test that calls the endpoint with `search=`, because today no test covers it.
- [P1] **The Scope filter is always empty and triggers a "Network Error" banner on every page load.** `/gene-catalogue/filters/scopes` returns 500 because the CRUD layer returns keys `scope_id/scope_name/scope_display_name` (`crud/gene_catalogue.py:496-503`) while `ScopeFilterOption` expects `id/name/display_name` (`schemas/gene_catalogue.py:156-158`). The 500 also lacks CORS headers, so the browser reports a CORS failure. One failed filter-option request replaces the page state with a generic error (`GeneCatalogueView.vue:132-136`, `onMounted` at `:716-722`). Fix: map the keys in the CRUD layer. In the UI, a failed filter-options call should disable only that filter ("Scopes unavailable"), and the main error alert needs a specific message and Retry.
- [P1] **Dark mode is broken in the expanded row.** `color="grey-lighten-4"` / `bg-grey-lighten-4` (`GeneCatalogueView.vue:298, 304`) paints a near-white slab in the default dark theme, and the light-on-light text (G/E scores, date) disappears (`i-catalogue-real-after.png`). Fix: use `variant="tonal"` or `bg-surface-variant`.
- [P1] **Disease data disagrees with the scope view.** The catalogue says "No disease" for NAA10, while the scope's Curations tab lists "NAA10-related syndrome" for the same active curation (`task1b-curations.png`). The catalogue reads the flat `evidence_data["disease_name"]` (`crud/gene_catalogue.py:284`), which the current schema-driven curation does not populate. A public catalogue that drops the disease from a gene-disease assertion is a trust problem. Fix: resolve the disease through the same accessor the scope list uses, and add a contract test.
- [P1] **Double pagination with a wrong total.** `v-data-table` (client mode, `:141-151`) renders its own footer ("1-20 of 20"), and a separate `v-pagination` (`:404-413`) pages the server. At 600 rows the footer still says "1-20 of 20" and the outer pager shows only arrows (`s-catalogue-600.png`). Fix: use `v-data-table-server` with `items-length=total`, `@update:options` and one footer.
- [P1] **At scale, long disease names push the Actions column off-screen.** `.text-truncate` only works inside the multi-disease tooltip branch (`:240-246`, CSS `:750-761`). The single-disease branch (`:255-258`) has no max-width, so a 120-character MONDO label widens the table past the card (`s-catalogue-600.png`, Actions column missing). Fix: give the Diseases column a fixed width, set `min-width:0` on the flex child and truncate, with the full name in a tooltip.
- [P1] Layout shift: the classification-summary chip row (`:114-130`) and the error alert (`:132-136`) are inserted with `v-if` above the table after data arrives. CLS is 0.074 on every load and **0.44** when the API takes 2.5 s. Fix: reserve the row height or move the summary into the filter bar as facet counts, and render the alert below the toolbar.
- [P2] Expand toggle buttons have no accessible name (axe `button-name`, critical, 2 nodes). Rows have `cursor:pointer` and a hover state (`:738-744`) but no click handler: an affordance that does nothing. Make the row open the gene, or remove the pointer.
- [P2] Colour semantics: "Best score" is coloured by fixed thresholds (`GeneCatalogueView.utils.ts:62-68`), so a "Disputed" row with 13.5 points shows bright green. Disputed and Refuted are both `error` red, and "Strong" is the brand `primary` blue. Colour the classification only, and keep the score neutral with tabular figures.
- [P2] "Pending" is shown for an active curation whose classification is null (PKD1). It reads like a workflow state. Use "Not classified".
- [P2] Mobile: the table scrolls horizontally inside the card. The four filters stack with about 48 px gaps, and the first result row starts around y≈1000 (`admin-catalogue-mobile.png`). Provide a card list under `md`, plus a single search field with a "Filters" sheet.
- [P3] Stat tiles "Curated genes / Active curations / Clinical scopes" duplicate the table footer, carry no time or trend and take the top-right of the page. Remove them or fold them into a one-line summary.
- AI-smell: a DNA avatar on every row, an orange `mdi-virus` icon in front of every disease (genetic diseases are not viruses), a map-pin icon on every locus and a folder icon in every scope chip. That is icon confetti across about 5 icons per row. A curator scans symbols, classifications and diseases, so drop the icons and let the type work.

### Gene Database (`/admin/genes`, `views/GenesTable.vue`)
Scores: D1 50 · D2 50 · D3 60 · D4 65 · D5 45 · D6 35 · D7 50 · D8 45 · D9 40 · D10 40 · D11 n/a · D12 55 · D13 60 · D14 82 · D15 n/a · D16 60 · D17 35 → **view score 51**
Evidence: `admin-genedb-desktop.png`, `s-genedb-600.png`, `st-error-genedb.png`; CLS 0.009; `i-genedb-real` (search "BRC" gives 3 rows while the chip still says "13 genes").
Findings:
- [P1] **"Add gene" and "Edit" do nothing.** "Add gene" links to `GeneAdmin`, the page itself (`GenesTable.vue:11-18`). "Edit" pushes `?edit=<id>` to the same route (`:289-291`), and nothing reads the query. Fix: wire them to the existing gene create/edit dialog, or remove them until they work.
- [P1] The route is named "admin" but is not role-gated (`router/index.ts:213-220`, `requiresAuth` only). It is also unreachable from navigation (only `Home.vue:24` links to it). Decide: add it to Curation setup for admins with `requiredRoles: ['admin']`, or merge it into the catalogue as an "All genes" toggle.
- [P2] The count chip shows `genesStore.genes.length` (`:68-70`). That is the size of the current page, and it ignores search results ("13 genes" with 3 rows shown, "20 genes" with 600 in the database). Show `total`.
- [P2] Two sort mechanisms (a "Sort by" select at `:83-91` plus sortable headers) and two paginators (`:99-106` plus `:169-178`). Same fix as the catalogue: `v-data-table-server`, header sort only.
- [P2] The chromosome filter options come from the current page only (`:239-253`). With 600 genes, page 1 offers chromosomes 2-21 only. Use a static 1-22, X, Y, MT list.
- [P2] 500 is shown as "No genes available in the database" plus a toast (`st-error-genedb.png`). Show an error state instead.
- [P2] Rows open on mouse click only (`@click:row`, `:105`). Rows are not focusable. The first link is the eye icon, which has only `title`.
- [P3] There is no curation signal at all, although the API returns `is_assigned` and `has_active_work`. Add a status column. Duplicate `BRCA1` records (HGNC:1000 and HGNC:1100 both named BRCA1) are visible and suggest a seed or data-quality check is missing.

### Gene Detail (`/genes/:id`, `views/GeneDetail.vue`)
Scores: D1 55 · D2 55 · D3 65 · D4 70 · D5 60 · D6 40 · D7 60 · D8 55 · D9 35 · D10 55 · D11 n/a · D12 65 · D13 70 · D14 82 · D15 n/a · D16 55 · D17 20 → **view score 56**
Evidence: `admin-gene-naa10-desktop.png`, `light-gene-naa10.png`, `st-error-gene.png`, `st-404-gene.png`; CLS 0.004-0.009.
Findings:
- [P1] **The gene page is an HGNC record viewer, not a curation hub.** NAA10 has an active *Definitive* curation (13.5 points), yet its page shows only HGNC fields, a UUID and timestamps. It has no curation status per scope, no classification, no disease, no score breakdown, no evidence summary, no assignment, no "Start curation in scope X" and no link to `/genes/:id/summary`. Fix: put a "Curations" section first. It needs one row per scope with workflow stage, classification badge, disease (MONDO), MOI, score G/E/total, curator, last change and an "Open" link. Below it, add assignment status with "Assign to me / Start precuration" for scopes where the user can curate. All the data exists (`/genes/:id/assignments`, `/genes/:id/progress`, catalogue `scope_curations`).
- [P1] **External links are HGNC only** (`:179-203`). Curators work from OMIM, ClinGen (gene validity), GenCC, MONDO, PanelApp, gnomAD and PubMed. Add a link row built from the HGNC ID and symbol, opening in a new tab with an icon.
- [P2] The "Database Record" card shows the internal UUID and created/updated timestamps (`:205-231`). This is developer data in the user's primary sidebar. Move it to a footer line or an admin-only disclosure.
- [P2] Not-found and server errors both say "Failed to load gene details" (`:352`). A deleted or mistyped gene should say "Gene not found", with a search field.
- [P2] HGNC enrichment blocks first paint: `loadGene` awaits the external HGNC call before `loading=false` (`:335-340`). HGNC is cached locally (165 ms), but a slow or down HGNC holds the whole page on a spinner. Render local data first and fill HGNC fields progressively.
- [P3] The back arrow always goes to the catalogue (`:40-46`), even when the user came from a scope or My Work. Use `router.back()` with a fallback, plus breadcrumbs.
- [P3] Card titles each carry a decorative icon (info, map-marker, tags, link, database). Three cards contain one or two fields each. Merge them into one dense key-value panel.

### Gene Summary (`/genes/:geneId/summary`, `views/GeneSummaryView.vue`, `components/clingen/ScopeSummaryCard.vue`)
Scores: D1 45 · D2 50 · D3 55 · D4 45 · D5 40 · D6 20 · D7 40 · D8 40 · D9 40 · D10 50 · D11 n/a · D12 65 · D13 65 · D14 78 · D15 n/a · D16 40 · D17 40 → **view score 48**
Evidence: `admin-summary-naa10-desktop.png`; 404 on the summary API.
Findings:
- [P1] **Orphan route.** Nothing in the app links to `GeneSummary` (grep: only the router definition). Users cannot discover the only view designed for cross-scope consensus and conflicts. Fix: merge it into Gene Detail as the "Curations across scopes" section, or link it from the catalogue and gene page.
- [P1] **Misleading empty state.** For a gene with a Definitive curation, an admin who is a member of that scope reads "This gene has not been curated in any public scopes yet". The endpoint covers public scopes only, while the user expects their own scopes to count. Fix: call `/summary/full` for authenticated members, and word the empty state precisely ("No public curations. 1 curation in your private scopes", with a link).
- [P2] Hard-coded `ClinGen SOP v11` chip (`:110`) on a methodology-agnostic platform. Use the schema name of the curations shown.
- [P2] A third, inconsistent classification colour map (`:152-170`): Limited is grey here and `secondary` in the catalogue, Unknown is error-red, Strong is info versus primary. Move the classification colours into a single shared module (or theme tokens) that every view imports.
- [P2] The title shows the raw UUID while loading (`:8`, `geneSymbol || geneId`). Show a skeleton instead.
- [P3] AI-smell: three tonal stat cards ("Scopes curating", "Consensus", "Agreement") followed by a fourth chip block that repeats the same distribution.

### My Work (`/assignments`, `views/GeneAssignments.vue`, `components/dynamic/GeneAssignmentManager.vue`)
Scores: D1 45 · D2 35 · D3 60 · D4 55 · D5 50 · D6 35 · D7 35 · D8 40 · D9 20 · D10 40 · D11 40 · D12 45 · D13 35 · D14 65 · D15 n/a · D16 35 · D17 25 → **view score 41**
Evidence: `curator-assignments-desktop.png`, `reviewer-assignments-desktop.png`, `curator-assignments-mobile.png`, `s-assignments-600.png`, `dlg-*-assign-*.png`, `curator-assign-assignee-filter.png`; CLS 0.10 at 600 rows; axe `label` critical.
Findings:
- [P0] **"My Work" is not my work.** The menu item is labelled "My Work", but the page is titled "Gene Assignments: Manage ... workload distribution" (`GeneAssignments.vue:6-9`). It loads `fetchAssignments()` with no curator filter (`GeneAssignmentManager.vue:554`), so the reviewer Bob sees Alice's assignments. The user's own workload is fetched (`:562`) and never rendered. Fix: split the page in two. "My Work" for everyone uses `/gene-assignments/curator/{me}/assignments` plus my review queue plus my drafts, grouped by state, with the next action per row. "Assignments (manage)" for scope admins holds the current table.
- [P1] **Silent truncation at 100 rows.** The table is client-side, but the API returns only the first 100 (`ASSIGNMENTS_DEFAULT_LIMIT`, `core/constants.py:66`). With 600 assignments the footer reads "1-25 of 100", and search runs over those 100 only ("GENE5" finds 10 instead of 111, `s-assignments-600*.png`). Fix: server-side table (`v-data-table-server`) with `search` passed to the API.
- [P1] **No path from an assignment to the work.** The eye opens a read-only dialog whose only action is "Close" (`:542-546`, dialog at `:256-309`). The table has no workflow stage, due date or "Open curation / Start" action. Fix: make the gene cell a link to `AssignmentDetail` (or straight to the curation), and add Stage, Due and Last activity columns.
- [P1] **Curators see manager controls they cannot use.** Bulk assign, Reassign and Edit priority show for every role. For a curator the assignee list is "No data available" (users are admin-only, `:557-558`), so Reassign and Bulk assign are dead ends. Fix: show these controls only for scope admins.
- [P1] **Bulk "Assign" is enabled with no user selected** and then silently does nothing (`:439`, button `:205-213`). Disable it until a user is selected, and validate inline.
- [P2] Two permanently disabled "Coming soon" buttons ("Rebalance workload", "Export", `:57-80`) are visual noise. Remove them until the features ship.
- [P2] The scope column shows the slug (`naa10-curation-demo`) in an info chip (`:118`). Use the display name as plain text. The Filter by Scope list reads `scopesStore.scopes` (`:391`) and offers every scope the user can see, not the scopes in the table.
- [P2] Accessibility: the two filter selects and the search field are flagged by axe as unlabeled (`label`, critical). After Escape, focus goes to `<body>` instead of the trigger in all four dialogs. Assignment/validation "view" dialogs do not trap focus.
- [P2] Mobile: the header CTA overflows (465 px scroll width), "Bulk assign/Rebalance" are clipped, and the table needs horizontal scroll.
- [P2] An error (500) shows "No data available" with only a toast (`st-error-assignments.png`).
- AI-smell: a generic avatar icon per assignee, the "Gene Assignment Management" card title inside a "Gene Assignments" page, and disabled feature-placeholders.

### Create Assignment (`/assignments/create`, `views/CreateAssignment.vue`)
Scores: D1 50 · D2 50 · D3 n/a · D4 n/a · D5 50 · D6 40 · D7 50 · D8 50 · D9 50 · D10 50 · D11 n/a · D12 70 · D13 70 · D14 55 · D15 n/a · D16 50 · D17 n/a → **view score 53**
Findings:
- [P2] This is a redirect stub: a page with a 64 px spinner, "Redirecting to assignment creation flow..." and then `router.replace` to scope selection (13 console warnings during the hop). Replace it with a router-level `redirect: { name: 'ScopeSelection' }` and delete the view. The back button on the stub also points into a loop.

### Assignment Detail (`/assignments/:id`, `views/AssignmentDetail.vue`)
Scores: D1 55 · D2 55 · D3 65 · D4 60 · D5 55 · D6 45 · D7 55 · D8 55 · D9 45 · D10 55 · D11 45 · D12 70 · D13 70 · D14 82 · D15 n/a · D16 65 · D17 35 → **view score 57**
Evidence: `curator-assignment-detail-desktop.png`, `st-error-assignment-detail.png`.
Findings:
- [P1] **The page ignores existing work.** NAA10 already has an active Definitive curation in this scope, yet the page offers "Start precuration" and "Start curation" (`:67-74`) with no hint that work exists, which invites duplicate curations. Fix: load `/genes/:id/progress` and show the current stage with a single contextual primary action (Continue draft / Open active curation / Start precuration).
- [P2] Reachable only right after creating an assignment (`ScopeSelection.vue:284`). Link it from My Work and the gene page.
- [P2] The gene link uses the browser's default visited purple and underline (`:40-43`). Style it with theme tokens.
- [P3] It shows priority and due date but not the assigner, assigned date, notes history or workflow stage.

### Validation Dashboard (`/validation`, `views/ValidationDashboard.vue`)
Scores: D1 40 · D2 40 · D3 55 · D4 45 · D5 50 · D6 40 · D7 20 · D8 30 · D9 20 · D10 30 · D11 n/a · D12 55 · D13 60 · D14 85 · D15 n/a · D16 15 · D17 20 → **view score 40**
Evidence: `admin-validation-desktop.png` (0/0/0/0 %), `validation-seeded.png`, `dlg-validation-detail.png`.
Findings:
- [P1] **The view has no data source.** It shows only results cached in this browser session's Pinia store (`:280-286`), so on any fresh visit it shows four tiles of zeros and "0 % compliance". The subtitle admits it in developer language: "The API provides no aggregate validation statistics, so the figures below are derived from these results" (`:7-10`). The "Result" column shows internal cache keys. Fix: remove the page from the Curation menu and from the dashboard Quick Actions until a backend aggregate exists. Validation belongs inline in the curation form and as a "has blocking issues" column in curation lists.
- [P2] "0 %" compliance with zero results is misleading. Show an empty state instead of a percentage.
- AI-smell (strong): four centred stat tiles with 48 px coloured icons, all meaningless; a "Common issues" card that is empty; generic "Compliance rate". This is the most template-like page in the area.

### Modals (quick view, assignment edit / reassign / view / bulk, validation detail)
Scores: D1 55 · D2 60 · D3 n/a · D4 n/a · D5 55 · D6 n/a · D7 55 · D8 n/a · D9 n/a · D10 50 · D11 40 · D12 45 · D13 n/a · D14 80 · D15 n/a · D16 55 · D17 45 → **view score 54**
Evidence: `dlg-catalogue-quickview.png`, `dlg-admin-assign-{edit,reassign,view,bulk}.png`, `dlg-curator-assign-*.png`, `dlg-validation-detail.png`; `dialogs-keyboard-tasks.json`.
Findings:
- [P2] Escape closes every dialog (good), but **focus returns to `<body>`, not the trigger**, in all 6 tested dialogs. Keyboard users lose their row position. Vuetify does this when the activator is not bound; use the `activator` slot or restore focus manually.
- [P2] Read-only "view" dialogs (assignment view, validation detail) let Tab leave the dialog. Their `v-list` usage also triggers axe `aria-required-children` (critical) and `aria-input-field-name`. Use plain `<dl>` markup for key-value content.
- [P2] Quick view duplicates the expanded row and Gene Detail: three representations of the same per-scope curation list, each with slightly different fields (the expanded row shows the curator, quick view hides it). Keep one. Recommendation: no quick view, an expandable row only, and the gene page as the hub.
- [P2] "View scope" in quick view leads to the scope overview, not to that gene's curation. A per-curation "Open curation" link would satisfy task T1 in 3 clicks.
- [P3] Copy: "1 assignments will be updated", "Assignment Comment (Optional)". Use plural rules and sentence case ("Note for the curator").

---

## Nielsen heuristics (this area, 0-4)

| # | Heuristic | Score | Note |
| --- | --- | --- | --- |
| 1 | Visibility of system status | 1 | Errors are reported as empty data ("No scopes assigned", "No genes available"), the catalogue shows a generic "Network Error", and the validation tiles show 0 % |
| 2 | Match with the real world | 2 | Virus icon for genetic diseases, "Pending" for an unclassified active curation, slugs instead of names; the G/E score breakdown and MONDO ids are good |
| 3 | User control and freedom | 2 | Escape works; focus is lost; back arrows hard-coded |
| 4 | Consistency and standards | 1 | Three classification colour maps, two paginators per table, two sort mechanisms, three duplicated curation summaries |
| 5 | Error prevention | 1 | Bulk assign with no user, "Start curation" offered when a curation is already active, dead "Add gene"/"Edit" |
| 6 | Recognition rather than recall | 2 | The gene page does not show curation state, so the user must remember which scope holds it |
| 7 | Flexibility and efficiency | 1 | No row click to open, no keyboard search shortcut, no saved filters, search broken |
| 8 | Aesthetic and minimalist design | 1 | Stat tiles, icon confetti, "Coming soon" buttons, decorative quick actions |
| 9 | Recognise, diagnose, recover from errors | 1 | "Network Error", "Failed to load gene details" for a 404, no Retry except on Assignment Detail |
| 10 | Help and documentation | 2 | Subtitles exist but are generic ("Browse and search genetic information") |

**Area score (weighted, lists x2): 49 / 100.** Views: Dashboard 48, Gene Catalogue 46, Gene Database 51, Gene Detail 56, Gene Summary 48, My Work 41, Create Assignment 53, Assignment Detail 57, Validation 40, Modals 54.

---

## Top 10 recommendations (priority order)

1. **Fix catalogue search** (`crud/gene_catalogue.py:218-219`, `cast(str)` to `cast(String)`) and the **scope filter key mismatch** (`:496-503` vs `schemas/gene_catalogue.py:156-158`). Add API tests for `search=` and `/filters/scopes`. [P0/P1, a 10-line fix that unblocks the primary find-a-gene task]
2. **Rebuild "My Work" as a personal queue.** Use the curator-assignments endpoint, review assignments and drafts, grouped by next action, each row deep-linked. Move the management table to a scope-admin "Assignments" page. [P0]
3. **Make Gene Detail the hub.** Add a per-scope curation table (stage, classification, disease, MOI, score, curator, Open), assignment status with a contextual primary action, cross-scope consensus from the summary endpoint (then delete the orphan `GeneSummaryView`), and an external link row (OMIM, ClinGen, GenCC, MONDO, PanelApp, gnomAD, PubMed). [P1]
4. **Dashboard answers "what next".** Replace the scope chips and Quick Actions with "Needs you" (changes requested, reviews waiting, drafts, unstarted assignments) and a compact scope list with counts. [P1]
5. **Server-side tables everywhere** (`v-data-table-server`): one footer, real totals, server search and sort. This removes the double paginators, the wrong counts ("20 genes", "1-20 of 20") and the silent 100-row truncation in My Work. [P1]
6. **Separate error from empty** in every list. Show an inline error with Retry; a failed filter-options call degrades only that filter; 404 says "Gene not found". [P1]
7. **Fix dark mode in the catalogue expanded row** (`grey-lighten-4` at `GeneCatalogueView.vue:298,304`) and define classification colours once as theme tokens (`classification-definitive` ... `refuted`), used by catalogue, summary and scope views. Stop colouring scores. [P1]
8. **Remove dead and placeholder UI:** Validation Dashboard (from menu and dashboard), "Coming soon" buttons, Gene Database "Add gene"/"Edit" self-links, the `CreateAssignment` stub (router redirect), and manager controls for non-admins. [P1/P2]
9. **Stabilise layout:** reserve space for the summary/alert rows in the catalogue (CLS 0.07 normally, 0.44 on a slow API), truncate long disease labels in a fixed-width column, and wrap page-header CTAs on mobile (two views scroll horizontally at 390 px). [P1/P2]
10. **Accessibility pass on these views:** name the expand toggles, label the My Work filters and search, return focus to the trigger on dialog close, make table rows keyboard-openable (rows as links), and replace `v-list` key-value blocks with `<dl>`. [P2]

## Bold redesign ideas

1. **Command-bar first navigation.** A global `/` or `Ctrl+K` palette that resolves gene symbols, aliases, HGNC IDs and MONDO terms, then jumps straight to "NAA10 · NAA10 Curation Demo · Definitive · Open curation". That cuts T1 from more than 5 clicks to 2 keystrokes, and the catalogue stops being the only entry point.
2. **The gene page as a "case file".** A two-column layout: on the left, a per-scope timeline of the gene-disease assertion (Entry, Precuration, Curation, Review, Active), with who acted and when; on the right, a sticky evidence ledger (genetic and experimental points against the SOP maxima, contradicting evidence, linked PMIDs). Cross-scope disagreements are flagged as a first-class "Conflict" banner instead of a stat card.
3. **"Inbox zero" My Work.** A Linear-style list with keyboard triage (`j/k` to move, `Enter` to open, `a` to accept an assignment, `s` to snooze), grouped by *Needs you now / Waiting on others / Done this week*. Every row shows the next verb ("Address 2 review comments", "Finish case-level scoring"), not just a gene name.
4. **A catalogue that reads like a matrix, not a card stack.** Rows are genes and columns are scopes; each cell is a small classification glyph (colour plus letter for colour-blind safety) with a hover card. Facet counts sit in the filter rail, and the stat tiles disappear. Curators see consensus and gaps across panels at a glance, which is what GenCC-style comparison work needs.
5. **Validation as an ambient signal, not a page.** Blocking issues appear inline in the form and as a red dot in any curation row ("2 blocking"), and the reviewer queue sorts by readiness. The standalone Validation Dashboard is retired.

---
Not checked: Lighthouse/D15 (central run), reviewer-specific review-queue pages (another area), curation form internals. Data created by parallel agents (UXR-test scope, IFT140 now in the catalogue) appears in some screenshots; it does not change the findings.
