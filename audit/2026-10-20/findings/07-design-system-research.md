# 07 Design system, copy and research

Area: code-level design system (D3, D4, D5, D7, D16, D17) plus external research. Read-only review of
`frontend/src` (89 `.vue` files, 27,244 lines). Run date 2026-10-20, branch `chore/deps-majors-2026-10-20`.

Raw data in `audit/2026-10-20/data/07-system/`:
`detect.json` (Impeccable detector), `inventory.json` (token-usage counts with file:line examples),
`component-props.txt` (Vuetify prop distributions per component), and the two scripts that produced
them (`inventory.py`, `tags.py`). To rerun: `python3 inventory.py frontend/src out.json` and
`python3 tags.py frontend/src v-btn,v-chip,v-dialog`.

Scores for this area (system-wide, code evidence only; per-view scores come from the browser agents):
D3 52 · D4 45 · D5 38 · D7 48 · D16 50 · D17 55 → **48**

---

## Top findings

| Sev | Finding | Evidence | Fix |
| --- | --- | --- | --- |
| P0 (domain) | **Three different ClinGen classification threshold sets**, none matching the SOP. The SOP says 12-18 points is Strong or Definitive (the difference is replication over time). The backend and `scoring.ts` call 7-11.99 "Strong" and 2-6.99 "Moderate". `curationScores.ts` adds genetic-score sub-thresholds that the SOP does not have. | `backend/app/scoring/clingen.py:925-945`; `frontend/src/components/clingen/scoring.ts:115-122`; `frontend/src/views/curation/curationScores.ts:127-134`. SOP: Strande et al. 2017, "scoring between 12 and 18 points can be 'Strong' or 'Definitive'" ([PMC5473734](https://pmc.ncbi.nlm.nih.gov/articles/PMC5473734/)) | Use one backend source of truth from the SOP Summary Scoring Matrix ([clinicalgenome.org](https://clinicalgenome.org/docs/summary-scoring-metric/)). The frontend only displays it. Add a test per threshold. This is outside visual design, but it changes every classification chip. |
| P1 | **11 classification-to-color implementations with 5 different mappings.** "Moderate" is warning in 9 places and info in 1. "Limited" is grey, orange, secondary or warning. "No Known" is error, grey or default. | see §2.3 | One `useClassification()` (label, color, icon, order), backed by the tokens in §6 |
| P1 | **Status value bug:** `under_review` does not exist. The backend enum is `in_review` (`backend/app/models/models.py:78`). Curations under review render as a grey chip with the raw value. | `components/curation/CurationList.vue:362,476,491`; `views/curation/CurationDetailView.vue:648`; `components/gene/geneDisplay.ts:30`; `components/gene/GeneList.vue:403` | Use the generated enum type from `types/api.ts`, not string maps |
| P1 | **Score maximum differs between views.** Total shown as "/ 18" in some views, while progress bars divide by 12. | `/18`: `ScoreSummary.vue:13`, `CurationList.vue:106,207`, `ReviewQueueView.vue:133`; `/12`: `useScoring.ts:118`, `ScopeSummaryCard.vue:104`, `ScorePreview.vue:48` (genetic, which is correct) | Score bar 0-18 with threshold ticks (§5 pattern 2) |
| P1 | **3 MDI icons do not exist and render blank**, including the Workflows nav item and the Disputed classification icon | `router/index.ts:308` + `WorkflowManagement.vue:21` (`mdi-workflow`); `GeneCatalogueView.utils.ts:91` (`mdi-alert-triangle`); `Home.vue:188` (`mdi-architecture`) | Replace with `mdi-sitemap-outline`, `mdi-alert`, delete the feature card |
| P1 | **Dark mode is the default** (`main.ts:22`, `|| 'dark'`), but ~30 light-only styles remain: `bg-grey-lighten-3/4` table bands, raw `rgba(0,0,0,…)`, and classes that do not exist (`bg-success-lighten-5`, `text-white-darken-1`) | §2.6 | Default to `system` via `prefers-color-scheme`. Replace with `surface-variant` tokens |
| P2 | Roboto is declared but never loaded. `index.html:141-143` preconnects to Google Fonts with no stylesheet, so text renders in whatever local sans exists | `App.vue:123`; Vuetify CSS sets `"Roboto", sans-serif` 79 times | Self-host a chosen face (§6) |
| P2 | Vuetify 3.9 uppercases every button and tab (`VBtn.css: text-transform: uppercase`), with no override in the repo. 99 Title Case labels render as ALL CAPS | `node_modules/vuetify/lib/components/VBtn/VBtn.css` | `defaults: { VBtn: { class: 'text-none' } }` or a Sass var, plus sentence-case labels |

---

## 1. Deterministic detector (Impeccable)

Command (from repo root): `impeccable detect --json frontend/src`, exit 2, ran on the whole tree in one pass.
Output: `data/07-system/detect.json`.

| Rule | Count | Files |
| --- | --- | --- |
| `overused-font` (warning, slop) | 8 | `App.vue:123` (`'Roboto', sans-serif`); `ErrorBoundary.vue:121`, `evidence/HPOInheritanceSelect.vue:325`, `evidence/HPOInput.vue:328`, `evidence/MONDOAutocomplete.vue:303`, `evidence/OMIMAutocomplete.vue:457`, `evidence/PMIDInput.vue:463`, `logging/LogViewer.vue:478` (all `'Roboto Mono', monospace`) |
| every other rule | 0 | – |

**Assessment.**
- Valid: 1 (`App.vue:123`). Roboto is the stock Vuetify face, and that is the "stock Material demo" look. It is also not loaded (see above).
- Partly false positive: 7. `Roboto Mono` is used correctly for identifiers (PMID, HPO, MONDO, OMIM) and logs. The problem is that the mono face is redeclared in 7 scoped blocks instead of one `--font-mono` token. It is not that the face is overused.
- **False negatives (detector blind spots).** The detector parses CSS, not Vuetify props or utility classes, so it reported 0 findings for things this audit found by grep:
  - 2 gradients (`CurationHeader.vue:187`, `Login.vue:243`)
  - glassmorphism `backdrop-filter: blur(10px)` (`Login.vue:253`)
  - hover-lift cards (`Home.vue:271`, `ScopeList.vue:409`, `UserManagement.vue:607`, `GeneList.vue:615`, `CurationList.vue:594`)
  - an icon-on-top feature card grid (`Home.vue:89-101`)
  - decorative stat tiles (`ValidationDashboard.vue:17-52`, `Home.vue:55-67`)
  - marketing copy (§3)

  Treat the detector's "8" as a floor, not a score.

---

## 2. Design-system inventory

### 2.1 Theme and global CSS

- Theme lives inline in `main.ts:24-92`: two `ThemeDefinition`s and **no `defaults` block**, so every density, variant and size choice is made per call site. There is no SCSS settings file and no `vuetify` options file, and the only global CSS is `App.vue:120-185`.
- Problems in the global CSS:
  - Dead or unused classes: `.gene-table .v-data-table__wrapper` is a Vuetify 2 selector, and `.form-container` and `.info-card` are unused.
  - Invalid scrollbar colors: `background: var(--v-theme-surface)` (`App.vue:132`) is a raw RGB triplet, not a color, so it must be wrapped in `rgb()`. `--v-theme-primary-darken-1` (`App.vue:141`) has the same problem.
- Theme palette: light uses Material blue `#1976D2` with `secondary #546E7A` and `accent #82B1FF`, the 2019 Vuetify defaults. Dark uses an indigo-navy `#1A1A2E / #25253A`, a different hue family from the light theme's neutral grey (`#F5F5F9`).
- `main.ts:15-16` imports `* as components` and `* as directives` while `vite.config` also runs `vite-plugin-vuetify({ autoImport: true })`. The full library ships and the plugin's tree-shaking has nothing left to remove (bundle size is a perf concern; see 06-perf).

### 2.2 Counts

| Dimension | Measure | Count | Notes / worst examples |
| --- | --- | --- | --- |
| Hex colors in `.vue`/`.ts` (outside `main.ts`) | literals | **0** | Good. |
| Raw `rgba(0,0,0,…)` / `rgba(255,255,255,…)` | literals | **17** in 13 files | Break in the other theme: `DisclaimerDialog.vue:164`, `ClinGenCurationForm.vue:446`, `CurationList.vue:589`, `GeneList.vue:610`, `MemberManagement.vue:408`, `InviteMemberDialog.vue:410`, `FooterBar.vue:109` |
| Theme-variable `rgb(a)(var(--v-…))` | uses | 47 | Correct pattern |
| `color="…"` / `:color` expressions | distinct / total | **82 / 506** | 7 semantic names plus raw palette names: `grey` 59, `purple` 6, `orange` 6, `green` 5, `blue` 5, `red` 2, `pink` 1, `grey-darken-1` 6, `white` 20 |
| Color-helper functions (`get*Color`, `*Color` computed) | definitions | **45** | 11 for classification, 6 for status, 5 `getRoleColor` (one shared `useRoleColors.ts:70` plus 4 local copies: `Home.vue:224`, `UserProfile.vue:256`, `AssignCuratorModal.vue:423`, `ReassignGeneModal.vue:287`) |
| `v-btn` | instances / variants / sizes / combos | **264 / 5 / 4 / 16** | text 93, outlined 56, tonal 32, flat 26, elevated 9, default 48; size small 70, x-small 14, large 11 |
| `v-btn` colors | distinct | 7 | primary 74, secondary 20, error 16, success 9, warning 8, info 7, white 6. `Dashboard.vue:61-80` shows 4 stacked buttons in 4 colors |
| `v-chip` | instances / variants / sizes / combos | **204 / 4 / 6 / 17** | outlined 65, tonal 56, flat 25, elevated 3, default 55; small 87, x-small 67, large 7, x-large 1 |
| `v-dialog` max-width | distinct | **8** | 400, 450, 500, 550, 600, 700, `700px`, 800 (`UserManagement.vue:301` … `ValidationDashboard.vue:171`) |
| Confirm dialogs | implementations | **13** | 7 native `window.confirm()` (`SchemaManagement.vue:326`, `SchemaEditor.vue:373`, `WorkflowManagement.vue:442`, `CurationList.vue:568`, `LogViewer.vue:384`, `SchemaDrivenCurationForm.vue:357`, `SchemaDrivenPrecurationForm.vue:346`) plus 6 bespoke `v-dialog`s (`RemoveGeneDialog.vue`, `ScopeSettings.vue:176`, `MemberManagement.vue:155`, `UserManagement.vue:300`, `CurationDetailView.vue:380,405,432`) |
| Snackbars | implementations | **7** | Global `MessageSnackbar.vue`, plus local ones in `UserManagement`, `UserProfile`, `PendingInvitations`, `ScopeCreate`, `MemberManagement`, `ScopeSettings` |
| `elevation` | explicit values | 1 (`8`, `Login.vue:5`) | Everything else uses default card elevation. 432 `v-card`s, 397 with default variant (shadowed) |
| `border-radius` | distinct | 3 (4px, 8px, 50%) | Plus 14 `rounded` props. Fine |
| Spacing utilities | distinct tokens / uses | **55 / 850** | Steps used: 0,1,2,3,4,6,7,8,12,16. Odd steps `3` (88) and `7` (2) are off a 4/8 rhythm |
| Custom `.gap-N` classes | files | 15 redefine locally (`Dashboard.vue:126` → 8px, `Login.vue:258` → 0.5rem) | **4 files use `gap-N` without defining it, so there is no gap at all:** `SchemaManagement.vue`, `WorkflowManagement.vue`, `ValidationDashboard.vue`, `GeneAssignmentManager.vue`. Vuetify's utility is `ga-N` |
| Type classes | distinct / uses | 11 / 502 | `text-caption` 205. Page titles mix `text-h3` (5 h1s) and `text-h4` (18 h1s). 7 views have no h1 (`ScopeSelection`, `ScopeCreate`, `UserProfile`, `GeneSummaryView`, `Login`, `Register`, `UserDetailsDialog`) |
| Custom `font-size` | distinct | 9 | 0.75rem, 0.85em, 0.85rem, 0.875rem, 0.9rem, 1.25rem, 1.75rem, 2rem, `14px` |
| Font families | distinct | 5 | Roboto (not loaded), Roboto Mono ×6, `monospace`, `'Courier New'` (`SchemaEditor.vue:422`), `Monaco/Menlo` stack |
| Tabular numbers | uses | **0** | No `font-variant-numeric` anywhere, yet scores use `toFixed(2)` 61 times |
| MDI icons | distinct / uses | **163 / 630** | `mdi-dna` ×39 stands for gene, curation, scope, app hero, "Genetic Evidence" and the nav item. Large decorative icons (≥48px): 15 |
| Emoji | in templates/strings | **0** | Good. |
| Date formatters | implementations | **20** functions | 8× `toLocaleDateString()` (browser locale), 4× `'en-US'`, 2× `undefined`. Null placeholder varies: `N/A` ×4, `Unknown` ×4, `—` ×3, `-` ×2, `unknown` ×1 |
| Number formats | `toFixed` | 61×(2), 5×(1), 2×(0) | Total shown as `x.x / 18` in one view and `x.xx` elsewhere |
| Tables | primitives | 3 | `v-data-table` (8), `v-table` (8), hand-rolled `v-list`/card rows (`GeneList.vue`, `CurationList.vue`). There is no `v-data-table-server`, so all paging is client-side |

### 2.3 Classification color, side by side (D4/D17)

| Implementation | Definitive | Strong | Moderate | Limited | Disputed | Refuted | No Known |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `GeneCatalogueView.utils.ts:70` | success | **primary** | warning | **secondary** | error | error | **default** |
| `ReviewQueueView.vue:346`, `CurationList.vue:501` | success | info | warning | grey | – | – | **error** |
| `GeneSummaryView.vue:153,163`, `ScopeSummaryCard.vue:93`, `useScoring.ts:104` | success | info | warning | grey | error (fallthrough) | error | **error** |
| `CurationDetailView.vue:590` | success | info | warning | **orange** | grey | grey | grey |
| `CurationHeader.vue:136`, `ScoreSummary.vue:201`, `SummarySection.vue:281` | success | info | warning | grey | error | error | grey |
| `useSchemaScoring.ts:103` | success | **success** | **info** | **warning** | warning | grey | grey |

Two semantic errors in the current approach:
1. Reusing workflow status colors (success, warning, error) for an ordinal evidence scale makes "Moderate" look like a warning and "No Known" look like a failure.
2. Strong=info=blue breaks the ordinal ramp.

Carbon's status-indicator pattern pairs color with shape and label and reserves status colors for things that need action ([Carbon](https://carbondesignsystem.com/patterns/status-indicator-pattern)). The icon map in `GeneCatalogueView.utils.ts:85-92` gives "Moderate" an alert icon.

### 2.4 Status labels, one value with many names (D7)

| Backend value | Labels in UI |
| --- | --- |
| `draft` | Draft (`CurationHeader.vue:156`), In Progress (`useGeneWorkflowStatus.ts:189`), Curation In Progress (`:204`) |
| `submitted` | Submitted, Pending Review (`useGeneWorkflowStatus.ts:190`, `Home.vue:216`), Awaiting Review (`:205`) |
| `in_review` | In Review (`CurationHeader.vue:158`, `terminology.ts:71`), Under Review (`useGeneWorkflowStatus.ts:206`, plus the non-existent `under_review` key in 4 files) |
| `approved` (precuration) | Approved, Ready for Curation (`useGeneWorkflowStatus.ts:192`) |
| `rejected` | Rejected (`terminology.ts:73`), Needs Revision (`useGeneWorkflowStatus.ts:193`) |

### 2.5 Components that do the same job

| Job | Implementations | Recommendation |
| --- | --- | --- |
| Gene table | `GenesTable.vue` (/admin/genes, "Gene Database"), `GeneCatalogueView.vue` (/genes), `GeneList.vue` + `GeneCard.vue` (scope tab, list rows), `GeneAssignmentManager.vue` (/assignments) | One `GeneTable` on `v-data-table-server` with column presets per context |
| Curation list | `CurationList.vue` (list rows), `ReviewQueueView.vue` (cards), table in `CurationDetailView` | One `CurationTable` with a `mode="review"` column preset |
| Score display | `ScoreSummary.vue` (circle + table, /18), `ScoreDisplay.vue`, `ScorePreview.vue` (/12 bars), `ScopeSummaryCard.vue`, inline in `CurationList.vue:204-210`, `ReviewQueueView.vue:130-135`, `CurationDetailView.vue:243-250` | One `ScoreBar` (compact) and one `ScoreMatrix` (full), §5 |
| Gene detail | `GeneDetail.vue` (page) and `GeneDetailModal.vue` (modal), ~340 lines each | Keep the page and use a side sheet that embeds the same component |
| Confirm | 13 (see 2.2) | One `ConfirmDialog` plus `useConfirm()`; type-to-confirm for destructive scope/user delete |
| Snackbar | 7 | Only `MessageSnackbar` via `useNotifications` (already exists in `composables/useNotifications.ts`) |
| Date formatting | 20 | `utils/format.ts`: `formatDate` (ISO `2026-10-20` in tables), `formatRelative` (with `title` holding the absolute date) |
| PubMed link | `PubmedLinkButton.vue`, `PubmedLinkChip.vue` | One component with a `variant` prop |
| Role color | `useRoleColors.ts` plus 4 local copies | Delete the copies |
| Terminology | `config/terminology.ts` exists but is imported by only 2 files (`MainNavigation.vue:77`, `UserMenu.vue:79`) | Make it the source for page titles, router meta and status labels |

### 2.6 Dark mode: present, default, incomplete

- A toggle exists (`AppBar.vue:26,80-83`). Default is **dark** for first-time users (`main.ts:22`) and ignores `prefers-color-scheme`.
- Light-only surfaces that glare in dark mode:
  - `bg-grey-lighten-4` / `bg-grey-lighten-3` banding: `SummarySection.vue:42,61,89,101,126,148,166,182`, `EvidenceDataTable.vue:5`, `GeneCatalogueView.vue:298,304`
  - `bg-grey-darken-3` footer in both themes (`FooterBar.vue:2`)
- Classes that do not exist because the theme has no `variations` configured: `bg-success-lighten-5` (`LumpingSplittingSection.vue:142`), `bg-warning-lighten-5` (`:177`), `bg-error-lighten-5` (`ContradictoryEvidenceSection.vue:26`; a scoped polyfill exists in `AddGeneModal.vue:610-620` only), and `text-white-darken-1` (`PrecurationFormView.vue:62`).
- Raw black alphas, invisible on dark: see 2.2. `DisclaimerDialog.vue:164-174` hand-patches both themes.
- Dark palette hue (navy `#1A1A2E`) differs from light (neutral `#F5F5F9`), so the two themes look like different products.

---

## 3. "AI tell" sweep

| # | Where | What | Rewrite / action |
| --- | --- | --- | --- |
| 1 | `Home.vue:83-85` | "Key Features" / "Comprehensive tools for genetic data management", above a 6-card grid of 64px colored icons (`Home.vue:89-101`) | Delete the section. Signed-in users should land on their work queue; anonymous users get one paragraph and a "Sign in" link |
| 2 | `Home.vue:151-187` | "Built-in support…", "**Powerful** search capabilities across gene symbols, HGNC IDs, and **dyadic names**" ("dyadic" is a leftover from another product), "**Comprehensive CRUD operations**" (developer jargon), "**Modern Architecture** – Three-tier architecture with PostgreSQL, FastAPI, and Vue 3" (stack is not a user benefit), icon `mdi-architecture` does not exist | Delete. If an intro is needed: "Curate gene-disease validity with ClinGen or GenCC criteria. Every classification is reviewed by a second curator." |
| 3 | `Home.vue:9-10`, `About.vue:14-15` | "**Advanced platform** for genetic information curation and management with ClinGen compliance" | "Gene-disease validity curation for clinical genetics teams." |
| 4 | `About.vue:23-27` | "a **sophisticated Vue.js-based platform** … has undergone a **major architectural transformation** … migrate to a **modern three-tier architecture**" | Changelog language, not user copy. Replace with what it does, who maintains it, how to cite it, SOP version, licence |
| 5 | `About.vue:32-56`, `Home.vue:177-182` | "Scientific Integrity – Immutable change logs and **cryptographic content addressing**" | Claim needs checking against the backend. If it is not user-visible, remove it |
| 6 | `About.vue:60-77` | Technology-stack chip wall (Vue 3, Vuetify 3, Vite…) | Move to README |
| 7 | `Home.vue:44-67` | 4 decorative stat tiles (48px icon, big number, label) | Replace with one sentence or a compact table with links ("128 genes curated · 14 awaiting review") |
| 8 | `ValidationDashboard.vue:17-52` | 4 stat tiles with 48px icons in 4 status colors | Inline counts as filter chips above the table ("Valid 120 · Invalid 3 · Warnings 8") that filter on click |
| 9 | `Home.vue:105-125` | "Recent Activity" card that has no activity, only "Welcome back, {email}!" and "Your role: user" (application role, which curators don't care about) | Delete, or show real recent events |
| 10 | `Dashboard.vue:8`, `Home.vue:116` | "Welcome back, …" | Delete; the page title is enough |
| 11 | `Dashboard.vue:12-15` and `:61-64` | "Start New Curation" and "New Curation", two primary actions for the same thing on one screen; Quick Actions in 4 colors (`:61-80`) | One primary "New curation". Quick Actions becomes a plain link list or goes away (the nav already has these) |
| 12 | `Login.vue:240-256` | 135° gradient page background plus `backdrop-filter: blur(10px)` glass card with `elevation="8"` | Plain `background` canvas, flat card with a 1px border |
| 13 | `CurationHeader.vue:186-188` | Gradient header band | Flat `surface` with a bottom border |
| 14 | `PrecurationFormView.vue:44-70` | Primary-colored hero band, white `text-h3` gene symbol, white chips | Standard page header (§6.3): gene symbol in mono, HGNC link, scope breadcrumb |
| 15 | Hover lift `translateY(-2…-4px)` on every card | `Home.vue:271`, `ScopeList.vue:409`, `UserManagement.vue:607`, `GeneList.vue:615`, `CurationList.vue:594`, `ReviewQueueView.vue:388` | Remove. Show interactivity with row hover background and cursor. Lift on non-clickable cards misleads |
| 16 | Exclamation marks | `ScopeCreate.vue:512` "Scope created successfully!", `Login.vue:194` "Login successful!", `ReviewQueueView.vue:81` "All caught up!", `Home.vue:116` | "Scope created", no toast on login (the redirect is the feedback), "No curations waiting for your review" |
| 17 | "Coming soon" shipped to users | `InviteMemberDialog.vue:50,102` (email invitations), `GeneAssignmentManager.vue:57,68` (disabled buttons with "Coming soon" tooltips) | Hide unbuilt features. Disabled buttons with "coming soon" are noise |
| 18 | ALL CAPS buttons | Vuetify 3.9 `VBtn.css` `text-transform: uppercase`; 99 Title Case labels, 3 sentence case (`AssignmentDetail.vue:68` "Start curation", `ScopeSelector.vue:62`) | Global `text-none` default; sentence case everywhere ("Create user", "View all", "Back to genes") |
| 19 | Title Case headings mixed with sentence case | Card titles "My Clinical Scopes", "Quick Actions", "Score Summary" vs "Curations awaiting peer review" | Sentence case for all UI text except proper nouns (ClinGen, HGNC, MONDO) |
| 20 | Icon-in-a-header everywhere | `mdi-dna` ×39 and an icon before nearly every card title (`<v-icon start>` pattern) | Icons only where they help scanning (nav, status). Remove from card titles |

No emoji, no "Lorem", no user-visible TODO. "comprehensive" in `GeneDetail.vue:4`, `GeneDetailModal.vue:4` and `SchemaDrivenCurationForm.vue:104` ("Key Features") is in code comments, not user copy.
`index.html` meta copy ("Methodology-agnostic platform for clinical genetics teams…") is actually the most accurate product description in the repo. Reuse it.

---

## 4. Terminology (D7)

### 4.1 Same concept, many names

| Concept | Variants found | Where |
| --- | --- | --- |
| Scope | "Clinical Scope(s)" (router title `router/index.ts:98,107`, `Dashboard.vue:23` "My Clinical Scopes"), "Scope(s)" (nav label `:111`, `:120` "Create Scope"), "Scope Dashboard" | Pick **Scope** (short, matches the data model); define it once in onboarding |
| Assignments / work | "My Work" (nav + title, `router/index.ts:247,251`), "View Assignments" (`Dashboard.vue:68`), "Create Assignment", "Assignment Details", "Gene Assignments", path `/assignments` | **My work** for the personal queue; **Assignment** for the object |
| Templates | Nav label "Templates" (`router/index.ts:284`), page title "Schema Management" (`:279`), button "New Schema" (`SchemaManagement.vue:12`), Dashboard button "Schema Management" (`Dashboard.vue:78`), field labels "Precuration Schema", "Curation Schema" | **Template** in UI, "schema" only in the JSON editor |
| Workflows | Nav "Workflows" (`:309`), title "Workflow Management", page body "Workflow Pairs (n)", "New Workflow Pair" (`WorkflowManagement.vue:14,22,240`), "Methodology Pair Selected" (`SchemaSelector.vue:71`), "Workflow Pair" (`ScopeSettings.vue:42`) | **Workflow** (a precuration template plus a curation template). `terminology.ts` already marks the others deprecated |
| Gene list | "Gene Catalogue" (nav, `:205`), "Gene Catalog" (`terminology.ts:33`), "Gene Database" (`GenesTable.vue:7`, `:218`), "Browse Genes" / "Manage Genes" (`Home.vue:20,29`), "Back to Genes" (`GeneDetail.vue:32`) | **Genes** (catalogue) and **Gene admin** (admin). Fix the en-GB/en-US split: the product uses "Catalogue" but `terminology.ts` says "Catalog" |
| Review | "Review Queue", "Pending Review", "Awaiting Review", "Under Review", "In Review", "Curations awaiting peer review", "4-eyes" | Queue = **Review queue**; status = **In review**; action = **Review** |
| Validation | "Validation", "Validation Dashboard" (dashboard is filler) | **Validation** |
| Classification thresholds | "No Known Disease Relationship" vs `no_known` keys vs GenCC "No Known Disease Relationship"; "Disputed" vs GenCC "Disputed Evidence", "Refuted" vs "Refuted Evidence"; "Animal Model Only" absent | Use the GenCC standard terms for GenCC export and ClinGen terms in the ClinGen workflow, from one enum |
| SOP version | "SOP v11" hard-coded in 5 UI places (`About.vue:27,35`, `Home.vue:152`, `GeneSummaryView.vue:110`, `ScorePreview.vue:5`) | ClinGen released **SOP v12 in February 2026** ([training materials](https://www.clinicalgenome.org/curation-activities/gene-disease-validity/training-materials/)). Show the version from the workflow's template metadata, not from copy |
| Precuration | "Precuration" only (no hyphen variants) | Good. Keep it. |
| Sign in | "Login" (noun used as verb: `Home.vue:37`, router title), "Login successful!" | **Sign in** / **Sign out** |

### 4.2 Proposed glossary (drive from `config/terminology.ts`, delete deprecated keys)

| Term | Definition shown in UI tooltip / FAQ |
| --- | --- |
| Scope | A team and its clinical area (e.g. "Kidney genetics"). Members have a scope role. |
| Scope role | Viewer, Curator, Reviewer, or Scope admin. Separate from platform admin. |
| Gene assignment | A gene added to a scope, optionally assigned to a curator. |
| Precuration | Defines the disease entity and mode of inheritance before evidence scoring (lumping and splitting). |
| Curation | Evidence collection and scoring for one gene-disease-MOI. |
| Template | The form, validation and scoring definition a curation uses. |
| Workflow | A precuration template plus a curation template, assigned to a scope. |
| Review | Independent check by a second person (4-eyes) before a curation becomes active. |
| Classification | Definitive · Strong · Moderate · Limited · Disputed · Refuted · No known disease relationship (ClinGen), in this order. |
| Statuses | Draft → Submitted → In review → Approved → Active; Rejected returns to Draft; Archived. One label per value, everywhere. |

Formats:
- Dates: ISO `2026-10-20` in tables (sortable, locale-neutral for an international team); relative ("3 d ago") only in activity feeds, with the absolute date in `title`.
- Empty value: em dash `—`.
- Scores: one decimal for totals (`11.5 / 18`), two decimals only inside the evidence matrix; tabular figures.

---

## 5. Research: patterns from best-in-class tools

Each pattern names its source and where it applies in Gene Curator.

| # | Pattern | Source | Apply here |
| --- | --- | --- | --- |
| 1 | **Classification matrix next to the evidence.** GCI shows a "Calculated Classification Matrix" with Points Counted capped per category even when total points are higher | [GCI: previewing curated evidence](https://vci-gci-docs.clinicalgenome.org/vci-gci-docs/gci-help/previewing-curated-evidence.md) | Replace the 4 score components with one `ScoreMatrix` (categories × points × max × counted) |
| 2 | **Calculated vs modified classification.** The default saved value is the calculated one. An override needs an "Explain Reason(s) for Change". Definitive needs an explicit "replicated over time" flag | [GCI: saving the summary classification](https://vci-gci-docs.clinicalgenome.org/vci-gci-docs/gci-help/saving-reviewing-and-approving-classifications/saving-the-summary-classification.md); [Strande 2017](https://pmc.ncbi.nlm.nih.gov/articles/PMC5473734/) | Show "Calculated: Strong" and "Final: Definitive (replicated over time ✓)" side by side; require a reason when they differ. This also fixes the threshold bug |
| 3 | **Score / Review / Contradicts row states.** Only "Score" rows count. Each row label links back to the evidence form | GCI previewing page (above) | Evidence tables get a per-row "counts toward score" state and a deep link; reviewers see which rows they are approving |
| 4 | **Evidence summary text with live preview** of how it will be published | GCI saving page (above) | Summary field with preview in the curation summary step |
| 5 | **Provisional → Approved → Published** as explicit record states with timestamps | [GCI docs index](https://vci-gci-docs.clinicalgenome.org/llms.txt) | One status vocabulary (§4.2) shown as a horizontal stepper in the curation header |
| 6 | **Traffic-light gene rating with consolidated reviewer opinions.** Green/amber/red, curated from multiple reviewers' ratings | [PanelApp, Martin et al. 2019](https://pmc.ncbi.nlm.nih.gov/articles/PMC8456155) | Gene summary across scopes: per-scope classification chips plus a consensus row with an explicit "conflict" flag (`GeneSummaryView.vue` already computes consensus) |
| 7 | **Standard terms from a Delphi process** (Definitive … No Known Disease Relationship, Animal Model Only) | [GenCC / ClinGen terms, Strande 2017 & GenCC](https://pmc.ncbi.nlm.nih.gov/articles/PMC5473734/) | One enum and one order for sorting and color ramp |
| 8 | **Persisted table preferences** (page, page size, search, sort) | [ClinGen gene-validity KB, "Manage Page Preferences"](https://search.clinicalgenome.org/kb/gene-validity) | Remember table state per user; GeneList/CurationList currently reset |
| 9 | **Filters in the URL, revert to default, empty state names the active filters** | [Primer filter pattern](https://primer.style/product/scenario-patterns/filter): "Persist filter state in URL parameters so filtered views are shareable and survive page reloads." | Gene catalogue, My work, review queue. Then saved views ("My drafts", "Waiting for me") on top |
| 10 | **Explicit save for forms; do not mix with autosave in the same form; `beforeunload` warning** | [Primer saving pattern](https://primer.style/product/ui-patterns/saving) | Curation form has explicit Save plus local draft recovery (`FormRecoveryDialog`). Add a persistent "Saved 14:02 · Unsaved changes" status near Save, not toasts |
| 11 | **Error summary at top, linked to fields, wording identical to inline messages, focus moves to it** | [GOV.UK error summary](https://design-system.service.gov.uk/components/error-summary) | Schema-driven forms on submit: an error list at the top of the tab with links into collapsed panels |
| 12 | **Status = color + shape + label; status color only when action is needed** | [Carbon status indicator pattern](https://carbondesignsystem.com/patterns/status-indicator-pattern) | Workflow status chips get distinct icons; classification uses a neutral-to-strong ramp, not alert colors |
| 13 | **Defined row-height sizes; header row matches row size; toolbar height matches density** | [Carbon data table style](https://carbondesignsystem.com/components/data-table/style) | Two densities only (compact 32px for work queues, default 48px for admin); a user toggle on lists |
| 14 | **Command menu (Cmd/Ctrl+K) to run any action or jump to any page; Cmd+/ lists shortcuts; G-then-X navigation** | [Linear: navigating Linear](https://linear.app/enablement/guide/navigating-linear) | "Go to gene…", "New curation for…", "Open review queue". The only shortcut today is the dev log viewer (`App.vue:69`) |
| 15 | **Criteria list with per-criterion strength and edit, engine pre-fills what it can, curator confirms** | [Franklin ACMG classification help](https://help.genoox.com/en/articles/7887793-franklin-acmg-clingen-cnv-classification) | External validators (HGNC, PubMed, HPO) pre-fill; show "auto" vs "curator" provenance per field |
| 16 | **Dense metric table with a small explanatory color scale** (gnomAD constraint table, o/e with CI; regional constraint Z ≥ 2.18 yellow, ≥ 4.0 red) | [gnomAD v2.1 news](https://gnomad.broadinstitute.org/news/2018-10-gnomad-v2-1); [genomic constraint](https://gnomad.broadinstitute.org/news/2022-10-the-addition-of-a-genomic-constraint-metric-to-gnomad/) | Numbers in a table, color only for thresholds, legend inline; this is the visual register to aim for |
| 17 | **Skeletons for full-page loads, spinners for single modules, nothing under 1 s** | [NN/g skeleton screens](https://www.nngroup.com/articles/skeleton-screens/) | Today: 16 `v-progress-circular`, 10 skeletons. Rule: route-level skeleton matching final layout; in-card spinner only for slow single widgets; delay any indicator ~300 ms |
| 18 | **Reserve space for late content; avoid injecting UI near the top** ("Dynamically injected content closer to the top of the viewport usually causes greater layout shifts") | [web.dev: optimize CLS](https://web.dev/articles/optimize-cls) | `PendingInvitations` and alerts above dashboards: render a fixed-height slot or put them below the main content |
| 19 | **Fonts: `font-display: optional` or metric-matched fallback; preload critical fonts** | [web.dev: optimize CLS](https://web.dev/articles/optimize-cls) | Self-host one variable font, preload, `size-adjust` fallback |
| 20 | **Animate only `transform` / `opacity`** | [web.dev: optimize CLS](https://web.dev/articles/optimize-cls) | `transition: all` in `ScorePreview.vue:263`, `ScoreDisplay.vue:331`, `DynamicForm.vue:544`, `ScoreSummary.vue:237`, `UserManagement.vue:603`, `LogViewer.vue:469` animates layout properties |
| 21 | **Same-document View Transitions are Baseline (Oct 2025)**: Chrome/Edge 111, Safari 18, Firefox 144 | [MDN ViewTransition](https://developer.mozilla.org/docs/Web/API/ViewTransition); [Chrome 2025 update](https://developer.chrome.com/blog/view-transitions-in-2025) | Wrap `router.beforeResolve` in `document.startViewTransition` for list → detail; falls back to no animation; respect `prefers-reduced-motion` |
| 22 | **Global component defaults** (`createVuetify({ defaults: { VBtn: {...}, VTextField: {...} } })`, precedence explicit > component > global) | [Vuetify defaults (mirror)](https://www.mintlify.com/vuetifyjs/vuetify/api/composables/defaults) | Collapse the 16 button and 17 chip combos into 3 button roles and 2 chip kinds via `defaults`, plus `v-defaults-provider` for dense tables |
| 23 | **Sentence-case button labels; any caps via CSS, never in the string** (screen readers) | [Angular Material button notes](https://v7.material.angular.io/components/button); [Firefox Acorn buttons](https://acorn.firefox.com/latest/mobile/components/buttons/android-dzMuCmlW) | `text-none` default; rewrite labels |

Flicker and stability guidance for Vue/Vuetify SPAs (2025-26):
- Use `<KeepAlive :include>` for list views so back-navigation restores scroll position and data without refetch ([Vue KeepAlive](https://vuejs.org/guide/built-ins/keep-alive.html)).
- Do not use `<Suspense>` for routes. It is still experimental ([Vue Suspense](https://vuejs.org/guide/built-ins/suspense.html)).
- Use `v-skeleton-loader` with the final layout's dimensions instead of spinner → empty → data.
- Initialise `loading = true`, not `false`, so the empty state never paints first.
- Read the theme before mount (already done in `main.ts:22`), but default to the system preference.

Not verified: GenCC's site colors, OMIM, Monarch and Benchling UI specifics. Searches returned no attributable design guidance, so no pattern above relies on them.

---

## 6. Target visual direction: "Operate" mode

Principles:
- **Calm:** neutral canvas, one accent, color only for meaning.
- **Dense:** a curator sees a gene's whole evidence state without scrolling cards.
- **Precise:** tabular numbers, mono identifiers, exact labels.
- **Trustworthy:** provenance and status are always visible; nothing decorative competes with data.

### 6.1 Tokens

**Neutrals (cool grey, same hue in both themes)**

| Token | Light | Dark |
| --- | --- | --- |
| `canvas` (background) | `#F6F7F9` | `#14171B` |
| `surface` | `#FFFFFF` | `#1C2026` |
| `surface-sunken` (table header, banding) | `#EEF0F3` | `#171A1F` |
| `border` | `#DCE0E5` | `#2C3139` |
| `text` | `#1B1F24` (16.6:1 on white) | `#E6E8EB` (14.6:1) |
| `text-muted` | `#5B636E` (6.1:1) | `#A0A7B1` (7.4:1) |

**Accent (one):** `#2B59C3` light (6.3:1 on white) / `#8AA9F2` dark (7.7:1 on `#14171B`). Use it for the primary action, links, focus ring and selection. No `secondary` or `accent` colors: delete `secondary`, `accent`, `primary-darken-1` usage.

**Workflow status (action-oriented, color + icon + label):**
- Draft: neutral, `mdi-pencil-outline`
- Submitted / In review: accent, `mdi-account-eye-outline`
- Approved: success `#1F7A4D` / `#6CC596`, `mdi-check`
- Active: success filled, `mdi-check-decagram`
- Rejected: error `#B4233A` / `#F2899A`, `mdi-undo`
- Archived: neutral, `mdi-archive-outline`
- Warning: `#9A5B00` / `#E8B35A`

**ClinGen classification (ordinal data scale, distinct from status):** a single green ramp for supporting evidence, an orange and red pair for contradiction, and neutral for none. The label is always shown. Contrast was computed against white and the dark canvas.

| Class | Light | Dark | Contrast L / D |
| --- | --- | --- | --- |
| Definitive | `#0F6B4F` filled chip, white text | `#5CC39A` | 6.5 / 8.3 |
| Strong | `#237A55` tonal | `#7FCF9E` | 5.3 / 9.7 |
| Moderate | `#4A7F2A` tonal | `#A9D07A` | 4.8 / 10.3 |
| Limited | `#776712` outlined | `#D8C25E` | 5.6 / 10.1 |
| Disputed | `#A55400` outlined + `mdi-scale-unbalanced` | `#F0A35A` | 5.4 / 8.6 |
| Refuted | `#B4233A` outlined + `mdi-close` | `#F2899A` | 6.5 / 7.6 |
| No known relationship | `#5F6670` outlined, no fill | `#A3AAB4` | 5.8 / 7.7 |

Fill weight (filled → tonal → outlined) carries strength redundantly, which helps with color-vision deficiency. ClinGen publishes no official color palette (none found), so treat these as product tokens. Put them in the theme as custom colors (`cls-definitive`, …) so `color="cls-definitive"` works.

**Typography**
- UI face: **IBM Plex Sans** (OFL, designed for technical UIs, has tabular figures). Body 14px / 20px, meta 12px / 16px. Headings: page title 20px/28px 600, section 16px/24px 600. No `text-h3`/`text-h4` hero titles.
- Mono: **IBM Plex Mono** for HGNC IDs, PMIDs, MONDO/HPO/OMIM CURIEs and gene symbols in tables.
- `font-variant-numeric: tabular-nums` on `.v-table`, `.v-data-table`, and score cells.
- Self-host with `font-display: optional` plus preload ([web.dev](https://web.dev/articles/optimize-cls)).
- Alternative pairing if Plex feels too corporate: Source Sans 3 with Source Code Pro.

**Spacing:** 4px base, steps 4, 8, 12, 16, 24, 32 (Vuetify `1,2,3,4,6,8`). Drop 5, 7, 12 and 16 utility steps. Use Vuetify `ga-*`; delete all local `.gap-N` classes.

**Radius:** 4px for inputs, chips and buttons; 8px for cards and dialogs; full for avatars only.

**Elevation:**
- 0 for everything in the page flow; cards are `variant="flat"` with a 1px `border`.
- Shadow (level 2) only for overlays: menus, dialogs, snackbars.
- No hover lift.

### 6.2 Vuetify `defaults` (replaces ~600 per-call props)

```ts
defaults: {
  global: { density: 'compact' },
  VBtn: { variant: 'flat', rounded: 'sm', class: 'text-none' },     // primary passes color="primary"
  VCard: { variant: 'flat', border: true, rounded: 'lg' },
  VChip: { size: 'small', variant: 'tonal', rounded: 'sm' },
  VTextField: { variant: 'outlined', density: 'compact' },
  VSelect: { variant: 'outlined', density: 'compact' },
  VAutocomplete: { variant: 'outlined', density: 'compact' },
  VDialog: { maxWidth: 560 },
  VAlert: { variant: 'tonal', density: 'compact' },
  VDataTable: { density: 'compact', hover: true },
}
```

Button roles (3):
- Primary: flat with accent, one per view
- Secondary: outlined neutral
- Tertiary: text

Destructive actions use the error color, in a confirm dialog only. Sizes: default, plus `small` in table rows. Delete `x-small`, `large` and `x-large` buttons.

### 6.3 Component guidance

- **Page header (one component, every view).** Breadcrumb (`Scope / Gene / Curation`), then the title row: title (20px), status chip and classification chip on the left, the one primary action on the right. Below it go meta text and provenance ("Updated 2026-10-18 by A. Smith · Template ClinGen GDV v11"). This replaces `CurationHeader`, the gradient band and the `PrecurationFormView` hero band.
- **Tables.** Use `v-data-table-server` for anything that pages.
  - Two density modes; sticky header; first column is the gene symbol in mono and links to the record.
  - Numbers right-aligned with tabular figures.
  - Row actions in an overflow menu, with only the primary row action inline.
  - Filters above the table and kept in the URL; saved views on top.
  - Empty state is one line plus the reset action.
- **Chips.** Two kinds only: *status* (workflow) and *classification* (data). Tags such as MOI use neutral outlined chips. Never `color="purple"` or `"orange"` for MOI (`CurationDetailView.vue:656-665`); MOI is a label, not a state.
- **Score.** Compact `ScoreBar` (0-18, ticks at the SOP thresholds, genetic and experimental segments, number in tabular mono) in lists and headers. Full `ScoreMatrix` (GCI-style, counted vs max) in the curation sidebar, sticky on desktop.
- **Dialogs.**
  - Three widths only: 400 (confirm), 560 (form), 800 (complex, e.g. assign curator).
  - Title in sentence case, body, actions right-aligned with Cancel (text) before the primary.
  - Destructive confirm names the object, and for scope or user delete requires typing the name.
  - Esc closes and focus returns to the trigger.
  - One `ConfirmDialog` via `useConfirm()` replaces 7 `window.confirm()` calls and 6 bespoke dialogs.
- **Empty states.** One sentence naming why it's empty and one action, e.g. "No genes in this scope yet. Add genes". No 64px grey icon (`ScopeList.vue:198`, `Dashboard.vue:44`, `GeneCatalogueView.vue:391`, `GenesTable.vue:156`).
- **Feedback.**
  - Persistent save status next to the Save button.
  - Snackbar only for background results, via the single `useNotifications` path.
  - Inline errors plus a GOV.UK-style error summary on submit.

### 6.4 Delete list

1. `Home.vue` hero, stat tiles, "Key Features" grid and fake "Recent Activity". Signed-in `/` redirects to My work; signed-out `/` shows a short intro and "Sign in".
2. `About.vue` "About the Project", architecture story and tech-stack chips. Keep purpose, citation, SOP version, contact and licence.
3. Gradients (`CurationHeader.vue:187`, `Login.vue:243`), glass (`Login.vue:253`), hover lifts (6 files), `elevation="8"`.
4. Decorative icons: the `<v-icon start>` in card titles, 48-120px icons in empty and error states (keep one small icon in 404/403), and `mdi-dna` as a generic "anything genetic" icon.
5. Quick Actions card (`Dashboard.vue:56-82`). It duplicates the nav and adds 4 colors.
6. "Coming soon" UI (`InviteMemberDialog.vue:50,102`, `GeneAssignmentManager.vue:57,68`).
7. Local color maps (45 helpers), local snackbars (6), local confirms (13), local date formatters (20), local `.gap-N` classes (15 files), all replaced by one shared module each.
8. Theme colors `secondary`, `accent`, `primary-darken-1`; the navy dark palette; raw `rgba(0,0,0,…)`; `bg-grey-lighten-*` bands; the non-existent `*-lighten-5` classes.
9. Redundant gene and curation list implementations (§2.5): 4 gene tables become 1, 3 curation lists become 1, and 4+ score displays become `ScoreBar` and `ScoreMatrix`.
10. Deprecated terminology keys in `config/terminology.ts` once page copy uses the canonical terms.

### 6.5 Suggested order (fits the "smallest complete change" rule)

1. Fix the domain bugs:
   - Classification thresholds: backend single source, frontend reads it.
   - `under_review` → `in_review`.
   - `/12` vs `/18`.
   - 3 missing icons.
2. One `classification.ts` (label, order, token, icon) and one `status.ts`, which deletes 11 + 6 maps.
3. Theme: new tokens, `defaults` block, `text-none`, self-hosted font, `prefers-color-scheme` default.
4. Shared `ConfirmDialog`, `formatDate`, and the single snackbar path.
5. Home/About/Dashboard copy rewrite and delete list.
6. Unify the gene and curation tables on `v-data-table-server`, with URL filters and saved views.
7. `ScoreBar` / `ScoreMatrix`, page header component, command palette.

Not done in this area: no screenshots (browser agents own per-view evidence). Contrast was computed for the proposed tokens only, not the current theme. The `under_review` impact was inferred from code, not reproduced in the browser.
