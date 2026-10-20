# Gene Curator UI/UX Review (2026-10-20)

**Scope:** every routed view (31 routes including all scope tabs) and every dialog (21 `v-dialog` components), as three roles (admin, curator, reviewer), at 390, 1280, 1366 and 1440 px, in dark and light themes.
**Method:** the repeatable protocol in [`PROTOCOL.md`](PROTOCOL.md): 17 dimensions scored 0-100 per view, P0-P3 severity, plus Nielsen heuristics. Seven parallel review agents, each with its own headless Playwright browser:

| # | Area | Detailed findings |
| --- | --- | --- |
| 01 | App shell, public pages, auth | [`findings/01-shell-public-auth.md`](findings/01-shell-public-auth.md) |
| 02 | Scopes, members, gene-assignment dialogs | [`findings/02-scopes.md`](findings/02-scopes.md) |
| 03 | Precuration, curation, detail, review queue | [`findings/03-curation.md`](findings/03-curation.md) |
| 04 | Dashboard, genes, My Work, validation | [`findings/04-genes-dashboard.md`](findings/04-genes-dashboard.md) |
| 05 | Admin: users, schemas, workflows | [`findings/05-admin.md`](findings/05-admin.md) |
| 06 | Lighthouse, layout shift (CLS), flicker, bundle, network | [`findings/06-performance-stability.md`](findings/06-performance-stability.md) |
| 07 | Design-system inventory, AI-tell sweep, external research, target direction | [`findings/07-design-system-research.md`](findings/07-design-system-research.md) |

**Tools:**
- Playwright 1.64 for screenshots, video frames and DOM timelines
- axe-core 4 for WCAG 2.2 AA checks
- Lighthouse 13.5: production build, 3 runs per route, median, desktop and mobile
- `PerformanceObserver` for layout shift and input timing
- the Impeccable design detector
- ffmpeg contact sheets for flicker

Screenshots (`screens/`) and raw data (`data/`) are local only (gitignored).

**Previous run:** [`../UX_AUDIT_REPORT.md`](../UX_AUDIT_REPORT.md) (2026-02-28) gave 5.3/10. The scales differ, so compare findings, not numbers.

---

## 1. Verdict

**Overall: 51/100.** This is the weighted mean of 42 view and dialog scores; the core work surfaces count ×3 and the lists ×2.

Gene Curator has a solid architecture and a curation form that is much better than in February: it now has tabs, collapsible panels per evidence category, a live score sidebar, and draft recovery. The product around that form does not yet hold together:

1. **The main workflow cannot be completed in the UI.** We tried three core tasks, and none finished:
   - A curator starting a precuration hits 4 dead ends.
   - "Add gene to scope" fails for genes already in the catalogue.
   - Gene search returns HTTP 500.
2. **The scoring gives wrong answers.** Three separate implementations of the ClinGen classification disagree with each other and with the SOP, so the same curation shows different verdicts on different pages.
3. **The UI fails silently.** 65 call sites send toast messages that are never rendered. Errors show as "No data". The schema editor's "Validate" button only writes to the developer log.
4. **It looks like a stock template.** Material blue from 2019, ALL CAPS buttons, gradient hero, "Key Features" grid, stat tiles that read 0, a DNA icon on everything, and 11 different classification color maps.

Desktop speed is fine (Lighthouse 92-98). Mobile is slow (45-69) because of bundle weight. Layout shift is low on 24 of 31 routes, but every hard reload flashes a white screen, then the logged-out menu, then an empty page.

### Scores by area

| Area | Score | Weakest view |
| --- | --- | --- |
| Curation work surface (03) | 51 | Precuration form 38 |
| Scopes and assignments (02) | 54 | Genes tab 46 |
| Genes, dashboard, My Work (04) | 49 | Validation 40, My Work 41 |
| Admin (05) | 50 | Schema editor 36 |
| Shell, public, auth (01) | 50 | Home, logged in, 37 |
| Performance and stability (06) | D14 62 · D15 55 | Home on mobile: Lighthouse 45, CLS 0.73 |
| Design system and copy (07) | 48 | Consistency (D5) 38 |

### Scores by dimension (app-wide, consolidated from all agents)

| Dimension | Score | One-line reason |
| --- | --- | --- |
| D1 Visual design and modernity | 50 | Stock Vuetify/Material 2019 look; gradients, glass, hover-lift cards |
| D2 Hierarchy and layout | 52 | No consistent page header; competing primary actions; fixed footer takes 77-110 px |
| D3 Typography | 52 | Roboto declared but never loaded; ALL CAPS buttons; no tabular numbers for scores |
| D4 Color and theming | 45 | 82 distinct color values; 11 classification maps; dark-mode default but incomplete |
| D5 Consistency | 38 | 4 gene tables, 13 confirm dialogs, 7 snackbars, 20 date formatters |
| D6 IA and navigation | 45 | Users page unreachable from the menu; My Work isn't the user's work; no mobile nav |
| D7 Clarity and copy | 48 | Several names for one concept; marketing filler; raw snake_case and slugs shown to users |
| D8 Learnability | 45 | Dead ends without explanation; disabled buttons with no reason |
| D9 Efficiency | 35 | No command palette; ~0.5 s lag per keystroke in evidence entry; 13 clicks to assign a gene |
| D10 Feedback and status | 30 | Toasts never render; errors look like empty states; no save status |
| D11 Error prevention and recovery | 35 | Browser `confirm()`/`prompt()`; out-of-range points accepted; orphaned drafts |
| D12 Accessibility | 55 | Unlabelled evidence inputs; focus not returned after dialogs; hidden drawer traps Tab |
| D13 Responsiveness | 40 | App bar overflows at 390 px; admin views scroll sideways |
| D14 Stability (perceived) | 62 | Auth/theme flash on every load; wrong form flashes first; numbers jump from "0" to real values |
| D15 Measured performance | 55 | Desktop 92-98; mobile 45-69 (largest content appears at 5-6 s) |
| D16 Authenticity (no AI tell) | 48 | See §4 |
| D17 Domain fit | 40 | Wrong thresholds; reviewers can't see the evidence they approve; no PMID lookup |

### Nielsen heuristics (0-4)

| # | Heuristic | Score | Key issue |
| --- | --- | --- | --- |
| 1 | Visibility of system status | 1 | Toasts never shown; save state invisible; Approve's HTTP 500 shows nothing |
| 2 | Match between system and real world | 2 | ClinGen vocabulary mostly right, but wrong thresholds and raw `autosomal_recessive` / slugs shown |
| 3 | User control and freedom | 2 | Draft recovery works; Ctrl+Z advertised but does nothing; inactive items vanish permanently |
| 4 | Consistency and standards | 1 | 5 classification color mappings; 3 labels per status; 8 dialog widths |
| 5 | Error prevention | 1 | Points 9 accepted in a 0-3 cell; one wrong password locks the login; deletes via `confirm()` |
| 6 | Recognition rather than recall | 2 | Users must type URLs (`/admin/users`, precuration); no breadcrumbs |
| 7 | Flexibility and efficiency | 1 | Only Ctrl+S and Ctrl+Enter; no bulk actions; no saved filters |
| 8 | Aesthetic and minimalist design | 2 | Score shown 3× per page; decorative icons and chips; marketing home page |
| 9 | Help users recover from errors | 1 | Errors become "No data" or a generic "Failed to …"; backend `detail` is dropped |
| 10 | Help and documentation | 2 | FAQ exists but describes features that don't exist |
| | **Total** | **15/40** | **Poor** |

---

## 2. Verified root causes (checked in code, not just reported)

| Finding | Evidence |
| --- | --- |
| Classification thresholds are wrong | `backend/app/scoring/clingen.py` `_classify`: Strong 7-11.99, Moderate 2-6.99, Limited 0.1-1.99. The SOP says Limited 1-6, Moderate 7-11, Strong/Definitive 12-18 (Definitive = replicated over time). `curationScores.ts:130-132` uses a third, invented set. |
| Toasts never render | `stores/notifications.ts:225` `addToast` (65 call sites) writes to a list that no component renders. `App.vue` mounts only `MessageSnackbar`, which is bound to the separate `useNotifications` state. |
| Gene catalogue filter returns 500 | Backend log: `ScopeFilterOption` validation error (`scope_id` vs `id` mismatch). Search returns 500 because of `.cast(str)` in `crud/gene_catalogue.py:218` (agent 04). |
| **Environment, not product** | Approve's HTTP 500 and the failed log writes were caused by the dev database **missing migrations 026 and 027**: there was no `notifications` table and no default `system_logs` partition. Both are now applied with `make db-migrate`. The real UI bug remains: when an action returns a 500, the dialog shows no error. Also check `execute_transition`: per agent 03 the workflow change was committed even though a later step failed, so the action didn't happen all-or-nothing. |

---

## 3. P0 list: fix before any visual work

These block tasks or produce wrong scientific output. Most are small changes.

| # | Problem | Fix | Where |
| --- | --- | --- | --- |
| 1 | Three classification algorithms; thresholds don't match the SOP; empty, "Contradicts" and out-of-range rows are counted | One backend scoring engine that reads the `evidence_data` shape the form saves; the frontend only displays the result. Count only `score` rows that have a PMID; clamp points to each field's range; cap Models+Rescue together. Add one test per threshold. | `scoring/clingen.py`, `components/clingen/scoring.ts`, `views/curation/curationScores.ts` |
| 2 | No toast is ever visible | Mount one toast host in `App.vue` for `notificationStore.toasts`, or route `addToast` through `useNotifications`. Delete the 6 local snackbars. | `App.vue`, `stores/notifications.ts` |
| 3 | Precuration form renders zero fields | Store `response.json_schema` (the store currently keeps the whole API response) | `stores/validation.ts:96` |
| 4 | Precuration workflow has no exit | Make Submit work (or call `/complete`); add a precuration view/edit route; add precurations to the Review Queue with Approve and Request changes | `SchemaDrivenPrecurationForm.vue`, router, `ReviewQueueView.vue` |
| 5 | ~0.5 s lag per keystroke in evidence cells | Commit cell values on blur (or debounce), remove the deep `initialData` watch after first load, record undo history per committed edit | `EvidenceDataTable.vue`, `ClinGenCurationForm.vue:405`, `SchemaDrivenCurationForm.vue:253` |
| 6 | Reviewer approves without seeing the evidence | Read-only evidence ledger on the detail page (PMID + citation, variant, points, explanation), with the narrative on top | `CurationDetailView.vue` |
| 7 | Gene search and the scope filter return 500 | `cast(String)`; align field names; add API tests | `crud/gene_catalogue.py:218,496` |
| 8 | Add Genes fails for existing catalogue genes | Reuse the existing gene; rank exact symbol matches first | `useAddGenes.ts` |
| 9 | One wrong password locks the login form | Clear field errors on input; don't attach the generic credential error to the email field | `Login.vue:457-494` |
| 10 | My Work is an admin table of everyone's assignments | Personal queue grouped by next action, each row linking to the work | `GeneAssignments.vue` |
| 11 | Schema create and duplicate always fail; the editor never shows errors | Make the seed schemas pass `/validate`; show the backend `detail` and validation results on screen | `SchemaManagement.vue`, `SchemaEditor.vue`, `004_seed_data.sql` |
| 12 | No navigation on phones | Navigation drawer below the `md` breakpoint, including account and logout | `AppBar.vue` |

---

## 4. AI smell / tell inventory (D16 = 48)

The app looks auto-generated in these places. Each one is a delete or rewrite, not a redesign:

- **Home page:** gradient hero; four stat tiles; "Key Features" six-card icon grid; "Powerful search… dyadic names" (left over from another product); "Comprehensive CRUD operations"; "Modern Architecture – PostgreSQL, FastAPI, Vue 3"; a "Recent Activity" card with no activity; `mdi-architecture`, an icon that doesn't exist and renders blank.
- **About page:** "sophisticated Vue.js-based platform… major architectural transformation", a tech-stack chip wall, and an unverified claim of "cryptographic content addressing".
- **Login:** 135° gradient background, frosted-glass card, `elevation="8"`, and a "Login successful!" toast.
- **Everywhere:**
  - hover-lift on cards that aren't clickable (6 files)
  - an icon before every card title
  - `mdi-dna` ×39, meaning gene, scope, curation and app all at once
  - decorative chips ("Default: 1.5 pts", "Range: 0-3", colored MOI chips)
  - a 64-72 px score number shown three times per page
  - a ring gauge for an ordinal score
  - Quick Actions cards in four colors that repeat the navigation
- **Placeholder and filler UI:**
  - the Validation Dashboard's four tiles are always 0 because nothing feeds them
  - the "Recent 30d" tile is always 0
  - "Coming soon" disabled buttons
  - "Quick Actions" in the curation form that only switch tab
  - a Ctrl+Z shortcut card for an undo that doesn't exist
- **Copy tics:** exclamation marks ("All caught up!", "Scope created successfully!"), "Welcome back, {email}!", Title Case and ALL CAPS mixed with sentence case.

The Impeccable detector found only 8 issues (all font-related), because it can't see Vuetify props or copy. Treat it as a floor, not a score.

---

## 5. Flicker and layout-shift register

| Symptom | Where | Cause | Fix |
| --- | --- | --- | --- |
| White flash, then dark | every hard load (lasts until first paint, ~4.5 s on mobile) | Theme applied by JS after the bundle loads | Inline `background` and `color-scheme` in `index.html`; default to `prefers-color-scheme` |
| Logged-out menu → full menu; empty content area | every authenticated route | `/auth/me` called twice; the router guard and app bar resolve separately | One memoised `initialize()`; an `authStatus: 'unknown'` state that renders a skeleton app bar; await it before the first route resolves |
| Icons pop in, nav shifts 0.011 | every route | 394 KB MDI icon font | SVG icons (`@mdi/js` with Vuetify's `mdi-svg` icon set) |
| Home layout shift 0.73 on mobile | `/` | logo image without dimensions | `width`/`height` on the logos in Home, Login, Register, About and AppBar |
| Generic form, then ClinGen form; red "No Known… 0.00" | curation new/edit | `useDynamicForm` is true before the schema loads | `v-if="schema"` and one skeleton matching the two-column layout |
| "0" → real number | stat cards, review badge, queue header | `loading` starts as `false` | Start with `loading = true`; show a skeleton, never a fake 0 |
| Spinner → "No data" → rows; double paginator; row-height jump | gene tables, scope Genes tab (CLS 0.055), catalogue (0.07; 0.44 with a slow API) | client-side tables, no reserved space | `v-data-table-server` with skeleton rows at the final height |
| Workflows CLS 0.16, schemas 0.09 | admin | rows inserted without reserved height | fixed row height and a skeleton |
| Deep link to Members or Settings jumps back to Overview | `/scopes/:id/members` | tab list computed before the role loads, then `router.push` | stable tab list and `router.replace` |
| Disclaimer dialog reopens mid-session over the form | curation form | disclaimer state re-checked on navigation | check once per version, never on work routes |

**Bundle:** the entry chunk is 674 KB (223 KB gzipped) and the CSS 800 KB. `main.ts:15-16` registers every Vuetify component and directive, which defeats `vite-plugin-vuetify` auto-import. Removing it plus the icon font is the single biggest speed win; agent 06 estimates mobile Lighthouse would rise from about 66 to over 80 and first paint would come 1.5-2 s sooner (estimated, not measured).

---

## 6. Target design direction

**Gene Curator is a scientific work tool.** The user's success is finishing a curation correctly, so the design should be calm, dense, precise and trustworthy (the Impeccable "Operate" mode). The visual model is the gnomAD, ClinGen GCI and Linear family, not a SaaS landing page. Full token tables and contrast values are in [findings/07 §6](findings/07-design-system-research.md).

**Tokens**
- One cool-grey neutral scale, with the same hue in both themes; the dark theme drops the navy.
- One accent: `#2B59C3` in light, `#8AA9F2` in dark.
- Workflow status: color + icon + label, used only where action is needed.
- **ClinGen classification as an ordinal scale, separate from status.** A green ramp from Definitive to Limited, with fill weight carrying strength (filled → tonal → outlined); orange/red outlined for Disputed and Refuted; neutral outline for No known relationship. The label is always shown. Every chip in the app comes from one `classification.ts`.
- **Type:** IBM Plex Sans and Plex Mono, self-hosted with `font-display: optional`. Mono for HGNC IDs, PMIDs, CURIEs and gene symbols in tables. `tabular-nums` on every table and score.
- **Spacing:** 4 px base, steps 4/8/12/16/24/32. **Radius:** 4 px for controls, 8 px for cards and dialogs.
- **Elevation:** 0 in the page flow (flat cards with a 1 px border); shadows only on overlays; no hover lift.

**Global Vuetify `defaults` block** in `createVuetify`. It replaces about 600 per-call props:
- `text-none` buttons, flat and bordered cards, `small` tonal chips, `outlined` compact fields
- one dialog width of 560
- three button roles: primary, secondary, tertiary

**Shared components** (each deletes several duplicates):

| New component | Replaces |
| --- | --- |
| `PageHeader`: breadcrumb, title, status and classification chips, one primary action, provenance line | `CurationHeader`, the gradient bands, hero banners |
| `ConfirmDialog` + `useConfirm()` (type-to-confirm for scope and user delete) | 7 `window.confirm()`, 6 custom confirm dialogs, `prompt()` password reset |
| `AppDialog`: 3 widths, Esc closes, focus returns to the trigger, `[Cancel] [Primary]` order | 21 dialogs with mixed widths and broken focus handling |
| `ScoreBar` (0-18 with SOP threshold ticks) and `ScoreMatrix` (GCI-style counted vs max) | `ScoreSummary`, `ScoreDisplay`, `ScorePreview`, `ScopeSummaryCard`, 3 inline score displays |
| `GeneTable` / `CurationTable` on `v-data-table-server`, with filters in the URL, saved views and a density toggle | 4 gene tables, 3 curation lists |
| `formatDate` (ISO in tables, relative with absolute in `title` in feeds) and `—` for empty values | 20 date formatters, 5 empty placeholders |

**Copy:** sentence case everywhere; one glossary driven by `config/terminology.ts`:
- Scope, Scope role, Template, Workflow, My work, Review queue
- one label per status: Draft → Submitted → In review → Approved → Active
- "Sign in", not "Login"
- the SOP version read from template metadata, since "SOP v11" is hard-coded in 5 places and ClinGen released v12 in February 2026

---

## 7. Recommended roadmap

Each phase is shippable on its own and ordered by user impact per unit of effort.

### Phase 0: correctness and trust (1-2 weeks; all P0 in §3)
Single scoring engine with SOP thresholds; toast host; precuration schema fix and precuration review path; gene search and add-gene fixes; login lockout; errors shown in dialogs; `under_review` → `in_review`; one score maximum (18); 3 missing icons. Add a regression test for each.

### Phase 1: stability and speed (1 week)
- Inline theme in `index.html` and a single auth bootstrap (removes the white and logged-out flashes).
- Drop the global Vuetify import; switch to SVG icons; give logos fixed dimensions.
- Skeletons that match the final layout; `loading = true` initially; server-side tables.
- Non-fixed footer on work pages; LogViewer unmounted when closed and admin-only.
- **Targets:** mobile Lighthouse ≥ 80, CLS < 0.05 on every route, no visible flash on hard reload.

### Phase 2: visual system (1-2 weeks)
- Tokens, the `defaults` block, Plex fonts, `prefers-color-scheme` default.
- `classification.ts` and `status.ts`, replacing 17 color maps.
- `PageHeader`, `AppDialog`, `ConfirmDialog`, `formatDate`.
- Execute the delete list: Home/About filler, gradients, glass, hover lifts, decorative icons, Quick Actions, "Coming soon" buttons, the Validation Dashboard.

### Phase 3: workflow and IA (2-3 weeks)
- Signed-in `/` goes to **My work**: a personal inbox grouped by next action ("Address 2 review comments", "Review PKD1").
- Navigation becomes **My work · Review (badge) · Scopes · Genes · Admin**, with a left rail on desktop and bottom tabs on mobile.
- **Gene page as a case file:** curation status per scope, classification, consensus, links to OMIM, ClinGen, GenCC, MONDO, PanelApp, gnomAD and PubMed.
- One add-and-assign gene flow with bulk actions; a setup checklist for new scopes; delete the `/scope-selection` wizard and `/admin/genes`.
- User management in the menu, with scope roles editable there.

### Phase 4: expert speed (ongoing)
- **Ctrl/⌘K command palette:** "go to PKD1", "new precuration for…", "review queue".
- **Keyboard-first evidence grid:** arrow keys, Enter to edit, PMID lookup showing "Smith 2019, *AJHG*", HGVS syntax check.
- **Paper-first curation:** paste PMIDs, then score probands and experiments per paper, as in the ClinGen GCI.
- **Review as a diff:** accept or query per evidence item, with comments anchored to items; the approval stores a provenance block (curator, reviewer, date, SOP version, score snapshot).
- **Methodology Studio:** a field-tree schema editor with a live form preview and simulated scoring, replacing the raw JSON textareas.

---

## 8. Test-data side effects and caveats

**Database changes made during the review:**
- Migrations 026 and 027 were applied to the dev database; they were missing and caused false HTTP 500s.
- Bob (`bob.jones@genecurator.org`) had been switched to platform admin during testing; he is reset to `user`. He still has a curator membership in Kidney Genetics that an agent added.
- **Leftover test records:**
  - scope `UXR-test`
  - users `uxr-*@example.org`
  - workflow pair `UXR-pair-53760` (inactive)
  - precuration `f459bf7f`
  - curations `fa6db2b5` (now **Active** for IFT140 in kidney-genetics) and `53d70b0e` (in review)

  Delete these, or rebuild the dev database, before the next demo.

**Limits of this review:**
- Some "reviewer" screenshots were taken while Bob was an admin. Carol was used as the reviewer for scope checks.
- API timings come from a local server with a tiny dataset; only the number and order of requests is meaningful.
- The SOP point rules for segregation and Models+Rescue come from reviewer knowledge; confirm them against the SOP v11/v12 text before implementing.
- Lighthouse was not run as curator or reviewer, and axe was not run at 390 px on admin views.
