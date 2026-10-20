# 02 — Clinical scopes and gene assignment management

Reviewer: UI/UX agent "scopes" · Run: 2026-10-20/21 · Protocol: `audit/2026-10-20/PROTOCOL.md`
Evidence: `audit/2026-10-20/screens/02-scopes/` (≈110 PNGs), `audit/2026-10-20/data/02-scopes/` (pages-*.json, modals-{d,m}.json, create-flow.json, d9-b.json, roles-uxr.json, assignments-manager.json).
Scripts: scratchpad `tools/scopes/*.mjs` (Playwright 1.64 headless, axe-core 4, 1440x900 + 390x844).

Test data created: scope **UXR-test** (`uxr-test`, id `1a5491de-…`), PKD1 assigned to Alice, Carol invited (accepted as reviewer, used as the true reviewer persona). No seed data was changed by this agent.

**Environment caveats (read before acting on role findings)**
- The dev DB has drifted from `004_seed_data.sql`: `bob.jones` now has application role `admin` and is a *curator* in Kidney Genetics; the seed `cardio`/`neuro` scopes do not exist. Bob therefore sees everything as admin, so I used Carol (scope reviewer in UXR-test) as the reviewer persona.
- The app defaults to the **dark theme** whatever the OS preference (`main.ts:22`), so every screenshot is dark unless noted. I did not capture the light theme for this area.
- Lighthouse (D15) was not run for this area (it needs the production build). D15 is marked n/a.

---

## Cross-cutting findings (apply to every view below)

- **[P0] Success and error toasts are never rendered.** `useNotificationsStore().addToast` is called 65 times, but no component reads `toasts`; `grep -rn toasts src --include=*.vue` returns nothing. Every "Gene X added", "Failed to add gene(s): …" and "N genes assigned" message is lost. The only visible trace is the red counter on the footer "Logs" link (`d9b-01-after-add.png`). Fix: mount one `<v-snackbar-queue>` (or a `ToastHost.vue`) in `App.vue` bound to `notificationStore.toasts`, and delete the three local `v-snackbar`s in `ScopeCreate.vue:304`, `MemberManagement.vue:173` and `ScopeSettings.vue:242`.
- **[P1] Deep links and reloads on `/members` and `/settings` jump back to Overview.** `ScopeDashboard.vue:147,181,195`: those tabs are rendered only after the role has loaded (`v-if`), and `v-tabs` (mandatory) resets the model to the first tab, whose setter calls `router.push('overview')`. Measured for admin, curator and reviewer: `dash-members` and `dash-settings` both end on `/overview` (pages-*.json). Fix: render the tabs from a computed list once `userRole !== undefined`, or keep the `v-tab` elements always present and use `disabled`. Also have the setter call `router.replace`, so each tab switch does not add a history entry.
- **[P1] The fixed footer (`FooterBar.vue:2`, `v-footer app`) takes 76 px of every desktop viewport and about 95 px on mobile.** It covers table pagination, dialog-adjacent content and the Create Scope buttons at 1440x900 (`admin-d-scope-create.png`, `admin-d-dash-genes.png`). Fix: make it a normal in-flow footer (drop `app`), or a 32 px single line.
- **[P1] Focus is not returned to the trigger after any dialog closes.** In all 9 dialogs, focus lands on `BODY` (modals-d.json `focusAfterClose`). Each dialog also leaks one Tab stop to the app-bar title before the trap pulls focus back (`tabSeq` contains `OUT:Gene Curator…`). Fix: pass `:return-focus="true"` / restore `document.activeElement` on close, and make the brand link non-focusable or put it after the main navigation in DOM order.
- **[P2] Escape behaves differently in each dialog.** Escape closes Add Genes, Assign, Reassign, Edit, Gene detail and Remove member. It does not close Remove gene, Invite member or Delete scope (`persistent` without an `@keydown.escape` handler: `RemoveGeneDialog.vue:5`, `InviteMemberDialog.vue:33`, `ScopeSettings.vue:177`). Use one rule: Escape always means Cancel.
- **[P2] Dialog chrome is inconsistent.**
  - Widths: 450, 500, 550, 600 and 700 px.
  - Button order and variants: `Cancel (left) … Primary (right)` in the gene modals; `spacer, Cancel, Remove` with default variants in `MemberManagement.vue:165-167`; `spacer, text Cancel, flat Delete` in `ScopeSettings.vue:223`.
  - Titles: some have an icon and an × close button (gene modals); others have neither (Remove member, Delete scope).
  - Fix: one `BaseDialog` with `size="sm|md"`, a title slot, an × close button, and a `[secondary] … [primary]` footer.
- **[P2] axe (desktop, every scope view):**
  - `image-alt` (critical): the logo `img` in the app bar.
  - `aria-required-children` and `aria-input-field-name` (critical/serious): `v-list` used as a definition list in `ScopeOverview.vue` and `MemberManagement.vue`.
  - `aria-progressbar-name` (serious): the unlabelled curation progress bar, `ScopeDashboard.vue:127`.
  - `color-contrast` (serious): the footer "version-info" and ".clickable" text.
  - `aria-tooltip-name`.
  - In dialogs: `label` (critical) for the unlabelled due-date input in `EditGeneAssignmentModal.vue:151`, and `color-contrast` in the Remove gene and Delete scope warnings.
- **[P2] Generic copy and "AI tells" across the area:**
  - Uppercase Material button labels everywhere.
  - Decorative icons on every field label and every list row (`mdi-identifier` and `mdi-format-title` on plain text fields).
  - Doubled info icons in alerts (`AddGeneModal.vue:191` and `AssignCuratorModal` add an extra `v-icon` inside `v-alert` that already has an icon).
  - "Danger Zone" and "Coming Soon" chips, and disabled "Rebalance Workload"/"Export" buttons in `GeneAssignmentManager.vue:57-75`.
  - Leftover refactoring banners in component headers (`**New View** - Built with DRY/SOLID principles`, `ScopeDashboard.vue:1-27`, `ScopeList.vue:1-27`): not user-facing, but noise.

---

### ScopeList (`/scopes`, `views/scope/ScopeList.vue`)
Scores: D1 50 · D2 60 · D3 60 · D4 55 · D5 60 · D6 65 · D7 55 · D8 70 · D9 55 · D10 50 · D11 n/a · D12 55 · D13 65 · D14 85 · D15 n/a · D16 45 · D17 40 → **view score 58**
Evidence: `admin-d-scopes.png`, `admin-m-scopes.png`, `admin-dark-scopes.png`; CLS 0.0067 (app-bar nav only); axe: 1 critical, 4 serious types; no console errors (apart from the vue-router `next()` deprecation, logged 5x per page).
Findings:
- [P1] **Every card shows "0% complete".** The list API returns `stats: {total_genes, member_count}` but no `completed_genes`, so `calculateScopeProgress` (`ScopeList.vue:353`) is always 0. A progress bar that is always empty is noise. Fix: return `completed_genes` (active curations) from `GET /scopes/`, or remove the bar.
- [P2] **"Kidney Genetics: 0 genes"** while the scope holds 2 curations and 1 active curation, because the counts come from different sources (see Dashboard).
- [P2] **An identical card grid for 2 items.** Four filters (search, visibility, status, sort) sit above two cards. The cards duplicate the same three facts (genes, members, % complete), add a hover lift (`translateY(-4px)`, `:409`), and wrap a single "Active" status in a green pill. Fix: a dense table or list (name, institution, your role, genes, active/in-review/total, last activity, due date), sortable by column, with filters only once there are more than about 8 scopes.
- [P2] **"Create Scope" is shown to every user** (route comment: "any authenticated user"), while the file header says "admin only". Decide which is intended. If anyone may create scopes, label the button "New scope" and say who becomes admin.
- [P3] The role chip is missing on cards (the API does not return `user_role`), so users cannot see their role in each scope at a glance, which is the most useful fact for a member.
- [P3] Mobile: the four filters stack to about 230 px before the first card.

### ScopeSelection wizard (`/scope-selection`, `views/ScopeSelection.vue`)
Scores: D1 45 · D2 50 · D3 55 · D4 60 · D5 40 · D6 35 · D7 45 · D8 45 · D9 35 · D10 50 · D11 55 · D12 60 · D13 60 · D14 85 · D15 n/a · D16 50 · D17 30 → **view score 50**
Evidence: `admin-d-scope-selection.png`; reached from `/assignments` → "New Assignment".
Findings:
- [P1] **It contradicts the scope model.** Step 2 asks the user to "Choose Methodology", but ScopeSettings states that the *scope* defines the workflow pair for all genes. The step either duplicates that choice or silently ignores it (the created assignment payload has no schema fields, `ScopeSelection.vue:265-270`). Fix: delete step 2. Better, delete the wizard and route "New Assignment" to the Genes tab of the chosen scope.
- [P1] **A third way to assign genes.** The same job is done here, on `/assignments` (GeneAssignmentManager) and in the scope Genes tab (AddGeneModal + AssignCuratorModal), with three different UIs, vocabularies ("Normal" vs "Medium" priority) and success paths. Fix: keep one path, the Genes tab.
- [P2] `fill-height` + `min-height: 100vh` (`:2,295`) centres a 1-field card vertically, leaving roughly 280 px of empty space above it at 1440x900. Step subtitles wrap into 3 lines ("Select curation / schemas").
- [P2] The search requires at least 2 characters and gives no hint; failures are only logged (`logger.error`), with no UI message.

### ScopeCreate (`/scopes/create`, `views/scope/ScopeCreate.vue`)
Scores: D1 55 · D2 50 · D3 60 · D4 60 · D5 55 · D6 60 · D7 60 · D8 65 · D9 55 · D10 55 · D11 65 · D12 60 · D13 70 · D14 90 · D15 n/a · D16 55 · D17 50 → **view score 60**
Evidence: `create-1-bad-name.png` … `create-10-after-create.png`, create-flow.json. Creating a scope with one initial member took **11 clicks, 13.5 s** (scripted, no thinking time). CLS 0.0068.
Findings:
- [P1] **The primary action reads weaker than Cancel.** "Create Scope" renders as a text-style button and Cancel as an outlined, high-contrast box (`create-8-member-added.png`). At 1440x900 both sit under the fixed footer until you scroll. Fix: `variant="flat" color="primary"` for Create, `variant="text"` for Cancel, and a sticky action bar.
- [P2] **Premature validation.** Blurring the machine-name field already shows "Display name is required" in red on an untouched field (`create-1-bad-name.png`).
- [P2] **Two names, entered in the wrong order.** Users type a slug ("machine-readable") before the display name. Fix: ask for the display name first and derive the slug live (`Kidney Genetics` → `kidney-genetics`), shown as an editable "URL name" under it.
- [P2] **The "Scope Naming Guidelines" card uses red ✗ icons for rules** ("No consecutive dashes"). It reads as failing validation before the user has typed anything. Turn it into helper text under the field.
- [P2] **No workflow pair is asked for at creation.** The new scope lands on a dashboard with no warning. The "No workflow configured" alert lives only on the Settings tab, and the Genes tab then offers "Start Precuration", which dead-ends (see Genes). Fix: add a required "Methodology" select (SOP v11 / GenCC / custom) to the create form.
- [P3] The help copy "You'll be added as an admin automatically" is good. The "Add Initial Member" dialog: focus goes to the dialog DIV rather than the search field, and the Add button has no loading state.

### ScopeDashboard shell + Overview tab (`/scopes/:id/overview`, `ScopeDashboard.vue`, `ScopeOverview.vue`)
Scores: D1 45 · D2 45 · D3 55 · D4 55 · D5 55 · D6 50 · D7 45 · D8 60 · D9 50 · D10 50 · D11 n/a · D12 50 · D13 50 · D14 75 · D15 n/a · D16 35 · D17 40 → **view score 51**
Evidence: `admin-d-dash-overview.png`, `admin-m-dash-overview.png`, `create-10-after-create.png`, `uxr-d-tab-overview.png`; CLS 0.009 on load, 0 on tab switches; axe: 2 critical (`aria-required-children` ×2), 3 serious types.
Findings:
- [P1] **The numbers contradict each other** (`admin-d-dash-overview.png`): "Total genes 0 · Completed 1 · 1 of 0 genes curated · 0%". `total_genes_assigned` counts assignments, while `active_curations` counts curations, including some on genes that have no assignment. Clinicians will distrust the whole page. Fix: derive every tile from one query (genes in scope, broken down by workflow stage), and clamp "x of y".
- [P1] **The header stats go stale.** After assigning PKD1, the tiles still read "Total genes 0" until a reload (`d9b-06-after-assign.png`). Fix: refetch statistics when GeneList emits `assigned`/`added`/`removed`, or move the stats into the scope store.
- [P2] **Meaningless stat tiles (AI tell).** Four equal cards (Total, Completed, In Progress, Members) are followed by a full-width striped progress bar repeating the same ratio, then an Overview tab with an 8-row "Statistics" list repeating the same numbers again (Total Genes, Active Curations…). Together with the "Recent Activity" block, the same 4 numbers appear 3 times. On mobile, the tiles and bar push the tabs about 900 px down (`admin-m-dash-overview.png`). Fix: replace them with one horizontal **pipeline strip** (Unassigned → Precuration → Curation → In review → Active, each count clickable to filter the Genes tab).
- [P2] **The Overview "Scope Information" card is a settings echo.** Name, display name, description, visibility and status rows each carry a decorative icon, and it uses `v-list` semantics, which causes the axe critical. Fix: show the methodology (workflow pair), the scope admins and the due date; those are what a curator needs.
- [P2] **The role chip conflates the two role systems.** An application admin who is a scope *curator* is shown as "admin" (`fetchUserRole` short-circuits on `authStore.isAdmin`, `stores/scopes.ts:232`). Show the scope role, and add "(platform admin)" when that is what grants the rights.
- [P2] **Loading is a 4 px bar, then a jump.** `v-progress-linear` (`:31`) replaces the whole page, and on first paint the tiles show `0` before the stats arrive. Use skeleton tiles and render tiles only once `scopeStats` is defined.
- [P2] **Not-found state:** "Scope not found or you don't have access." appears as a warning alert, with no way back (no link to `/scopes`) and no distinction between 404 and 403 (`dash-404` screenshots).
- [P3] Mobile: the role chip is clipped ("adn") and the tabs scroll horizontally without an affordance.

### Genes tab (`/scopes/:id/genes`, `components/gene/GeneList.vue`, `GeneRowActions.vue`)
Scores: D1 50 · D2 45 · D3 60 · D4 50 · D5 50 · D6 45 · D7 45 · D8 35 · D9 30 · D10 25 · D11 45 · D12 60 · D13 30 · D14 65 · D15 n/a · D16 50 · D17 45 → **view score 46**
Evidence: `uxr-d-tab-genes.png`, `admin-d-dash-genes.png`, `admin-m-dash-genes.png`, `role-*-genes.png`, `role-*-rowmenu.png`, `d9b-*`; CLS **0.046** on direct load (data-table header and footer shift when rows arrive), close to the 0.05 budget.

**D9 primary task: "As scope admin, add a gene to a scope and assign a curator"** (d9-b.json)
| Path | Clicks | Keys | Time (scripted) | Result |
|---|---|---|---|---|
| Expected: Genes → Add Genes → search PKD1 → pick → Add Gene | 6 | 4 | 12.4 s | **Dead end**: `400 Gene with HGNC ID HGNC:9008 already exists`. The dialog stays open, the toast is invisible, and nothing is added to the scope. |
| Recovery: Cancel → Assign to Curator → filter PKD1 → pick → pick curator → Assign (1) | +7 | +5 | +9.7 s | Success |
| **Total** | **13 clicks + 9 keys** | | **22.1 s** of robot time (a human needs ~60–90 s, plus the time to work out the dead end) | |
| Ideal (one "Add genes to scope" dialog with an optional curator) | 5 | 4 | — | |

Findings:
- [P0] **"Add Genes" cannot add a gene that is already in the catalogue.** That is the common case: the catalogue is shared, and PKD1 was already there. `useAddGenes.addSingleGene` always calls `genesAPI.createGene` first and only assigns the scope after that succeeds (`components/gene/useAddGenes.ts:32-80`). The dialog title "Add Genes to Catalog" also tells a scope admin they are editing the global catalogue. Fix: search the local catalogue and HGNC together; if the gene exists, skip creation and call `createAssignment` (or treat the 400 "already exists" as success and assign it); rename the dialog "Add genes to UXR-test".
- [P0] **No feedback on failure or success** (toast host missing, see cross-cutting). The user clicks "Add Gene" and nothing visible happens.
- [P1] **Two modals split one job, and they exclude each other.** AddGeneModal assigns genes to the scope *unassigned*. AssignCuratorModal lists only genes **not yet in the scope** (`AssignCuratorModal.vue:434-447`). A gene added through "Add Genes" therefore never appears in "Assign to Curator" (empty text: "No unassigned genes available"); its curator can only be set through the row menu → "Reassign". The toast copy "Genes added to catalog. You can now assign them to curators." (`GeneList.vue:555`) points users to that dead end. Fix: one "Add genes" dialog (search or paste a list, optional curator, optional priority and due date), and a "Assign curator" bulk action on table row selection.
- [P1] **HGNC search ranks the exact match third.** "PKD1" returns PKD1-AS1, PKD1L1-AS1, PKD1 … (`d9a-03-hgnc-results.png`, `exactIndex: 2`). The first run of the script picked PKD1-AS1, an error a tired curator would make too. Fix: exact symbol (then previous/alias symbol) first, then prefix matches; show the approved name and locus type in each row ("polycystin 1, transient receptor potential channel interacting · protein-coding").
- [P1] **The workflow state is not explained.** With no workflow pair configured, the row menu still offers "Start Precuration", which leads to a page titled "Unknown Gene" that says "No Schema Configured … contact an administrator" (`role-carol-start-precuration.png`). Fix: show a blocking banner on the Genes tab ("This scope has no methodology yet. [Configure]" for admins, "Ask a scope admin" for others), and disable the action with that reason.
- [P1] **The reviewer sees curator actions.** Carol (scope reviewer) gets "Start Precuration" in the row menu (`roles-uxr.json`) and can open the precuration page. `GeneRowActions.vue:9-36` does not check `canCurate`. Hide the action, or disable it with "Reviewers can't start precurations".
- [P2] **Duplicate empty states.** The table shows "No data available" and, below it, an info alert says "No genes assigned … Start by assigning genes to curators" with an "Assign Genes" button (`GeneList.vue:204-233`). On mobile that alert wraps one word per line (`admin-m-dash-genes.png`).
- [P2] **Status vocabulary is overloaded.** Three columns carry status chips: "Status" (Assigned/In progress, derived from `has_active_work`, `useScopeGenes.ts:70`), "Workflow" (No Precuration/Ready for Curation/…) and "Progress" (a 0–100 % bar computed from the Status column). Fix: one stage column (the pipeline stage) plus "updated x days ago". Drop Progress.
- [P2] **Chip confetti.** Every cell (curator, priority, status, workflow) is a coloured chip, with a DNA icon in front of every gene symbol and every chip. There is no tabular hierarchy; the gene symbol (the key) is the smallest-weight item. Fix: plain text cells, the gene symbol in medium weight with its HGNC ID under it in caption style, and colour only for the stage.
- [P2] **Card view** (`mdi-view-grid` toggle) adds a second, weaker layout for a table-shaped job, and on mobile the toggle overlaps the search field. Remove it; make the table responsive (stacked rows below 600 px).
- [P2] **The mobile toolbar breaks.** Fixed `style="max-width: 400px/200px"` inside `v-toolbar` (`GeneList.vue:4-40`) crushes the search and both filters to icon width, and "ASSIGN T…" is clipped. Fix: wrap the toolbar (`flex-wrap`), and put the filters in a bottom sheet on mobile.
- [P2] **No bulk actions or row selection** in the scope table (GeneAssignmentManager has `show-select`, this one does not). Assigning 30 genes to one curator means 30 Reassign dialogs.
- [P3] **The status filter options** ("Under Review", "Completed") can never match: `useScopeGenes` only produces `assigned`/`in_progress`.

### Curations tab (`/scopes/:id/curations`, `CurationList`)
Scores: D2 60 · D5 60 · D10 60 · D12 60 · D14 70 · others not assessed (owned by the curation area) → **view score 62**
Evidence: `admin-d-dash-curations.png`; CLS 0.043 on direct load (table shift); axe: `aria-progressbar-name`, 2× `aria-tooltip-name`.
- [P2] The tab badge "Curations 2" disagrees with the "Completed 1 / In progress 0" tiles on the same screen (draft/rejected curations are counted in one place only).

### Members tab (`MemberManagement.vue`, `InviteMemberDialog.vue`)
Scores: D1 55 · D2 60 · D3 60 · D4 50 · D5 50 · D6 65 · D7 60 · D8 65 · D9 60 · D10 45 · D11 60 · D12 50 · D13 60 · D14 90 · D15 n/a · D16 55 · D17 55 → **view score 59**
Evidence: `uxr-d-tab-members.png`, `pending-members.png`, `modal-d-invite-member.png`, `modal-d-member-remove.png`, `role-*-members.png`.
Findings:
- [P2] **Role is shown twice per row.** A coloured role avatar (edit icon for curator) and a role chip with the same icon carry the same information. Show the person (initials avatar) plus one role label; the ORCID should be a link, not "(ORCID: …)" text.
- [P2] **Invitation management is missing.** Pending rows show "Invited" but offer only "Change role" and "Remove member"; there is no "Resend" or "Revoke invitation" with the invite date or expiry (the API returns `expires_at`). The tile and the tab badge count 2 while 3 rows are listed (pending users are excluded without saying so).
- [P2] **The role change is a one-click menu item with no confirmation and no undo**, and its feedback uses a local snackbar (`MemberManagement.vue:173`) unlike every other toast.
- [P2] **The Invite dialog has a disabled "BY EMAIL · COMING SOON" tab** (`InviteMemberDialog.vue:50,102`), a dead affordance and AI-tell. It defaults the role to "Viewer" with no description of what each role can do, and Escape does nothing.
- [P2] **The "Remove member" dialog** has no title icon, no × button and default-variant buttons, and does not say what happens to that member's assigned genes.
- [P3] Curators and reviewers see the list with no action menu and no explanation that only scope admins manage members.

### Settings tab (`ScopeSettings.vue`)
Scores: D1 55 · D2 55 · D3 60 · D4 55 · D5 55 · D6 55 · D7 65 · D8 60 · D9 60 · D10 45 · D11 70 · D12 60 · D13 65 · D14 90 · D15 n/a · D16 50 · D17 60 → **view score 60**
Evidence: `uxr-d-tab-settings.png`, `modal-d-delete-scope.png`.
Findings:
- [P1] **The most consequential setting is buried.** The scope methodology (workflow pair) is configured only here, and the scope is unusable without it. Surface the "No workflow configured" state on the dashboard header and the Genes tab, not only in Settings.
- [P2] **Cards nested in cards.** An outlined "Workflow Configuration" card and an outlined "Basic Information" card sit inside the "Scope Settings" card, inside the tab card: four borders deep. Linked schemas are shown as tonal primary/secondary cards (decorative colour). Fix: a flat settings page with section headings and a sticky Save bar.
- [P2] **Saving is opaque.** "Save Settings" stays disabled until the form is dirty, but nothing explains why. Leaving the tab while dirty gives no warning (draft loss). Feedback goes through a local snackbar.
- [P2] **Danger Zone:** a red outline, a red heading and a red alert, plus a blue info alert inside it ("This scope has 1 active gene assignment"). The Delete dialog does require a checkbox when assignments exist (good), but Escape does not close it, and "Delete" should name the scope ("Delete UXR-test").
- [P3] `ScopeSettings.vue:133-140`: the "Only scope administrators can modify these settings" alert can never render, because the tab is hidden for non-admins (`ScopeDashboard.vue:195`). It is dead code.

### Gene modals (AddGeneModal, AssignCuratorModal, ReassignGeneModal, EditGeneAssignmentModal, RemoveGeneDialog, GeneDetailModal)
Scores: D1 60 · D2 60 · D3 60 · D4 55 · D5 50 · D6 n/a · D7 50 · D8 45 · D9 40 · D10 30 · D11 55 · D12 60 · D13 70 · D14 95 · D15 n/a · D16 55 · D17 55 → **score 56**
Evidence: `modal-d-*.png`, `modal-m-*.png`, modals-{d,m}.json (dCLS 0 for every open/close; no flicker), `d9b-05-ready-to-assign.png`.
Findings (in addition to the cross-cutting ones):
- [P1] **AddGeneModal** (Add Genes): see the Genes tab P0/P1 findings. The selected-gene preview shows only the HGNC ID and the symbol in green, the same information as the chip above it; the approved name, locus type and location are missing.
- [P2] **AssignCuratorModal** (Assign Genes to Curator):
  - It loads the whole catalogue (`getGenes({limit: 500})`, `:434`) and filters client-side, which will silently truncate at 500 genes.
  - Its file header promises an "Optional due date", but there is no due-date field (only in Edit).
  - The preview always says "at medium priority", because `priority !== 'normal'` compares against a value that never exists (`:259`).
  - The "1 gene(s) selected" alert repeats the chip count.
  - Assigning with `Promise.all` of N single POSTs: one failure leaves a partial assignment and a single error message. Use `POST /gene-assignments/bulk`.
- [P2] **EditGeneAssignmentModal** (Edit Gene Assignment):
  - The native `type="date"` input shows `mm/dd/yyyy` (US format in a German lab context) and has no label (axe `label` critical, `:151`).
  - A "Revalidate" button against HGNC sits next to the assignment fields, which mixes concerns.
  - The priority order is High/Medium/Low here but Low/Medium/High in the Assign modal.
- [P2] **Priority vocabulary:** "Medium" here, "Normal" in `/assignments` (`admin-d-assignments-manager.png`).
- [P3] **GeneDetailModal** (Gene detail) is the best-designed dialog in the area: clear sections and an HGNC link. Missing: in-scope context (current curator, stage, link to the curation).
- [P3] **RemoveGeneDialog** (Remove Gene from Scope): the copy is clear ("will not delete the gene … curations preserved"), and the destructive button is right-aligned with an icon. Escape does not work. The orange warning text fails contrast.

### GeneAssignmentManager (`/assignments`, `components/dynamic/GeneAssignmentManager.vue`)
Scores: D1 50 · D2 55 · D5 40 · D6 40 · D7 50 · D9 55 · D12 50 · D14 85 · D16 40 · D17 45 → **score 51**
Evidence: `admin-d-assignments-manager.png`; CLS 0.015; axe: `label` critical ×3, `aria-tooltip-name` ×3.
- [P1] **A duplicate assignment surface** with different rules from the scope Genes tab (see ScopeSelection P1). It shows the scope as a machine slug chip (`uxr-test`), uses "Normal" priority, and has icon-only actions (pencil, account-plus, eye) with no labels beyond aria.
- [P2] **Disabled "Rebalance Workload" and "Export" "Coming soon" buttons.** Ship them or delete them.

---

## Role matrix (UXR-test, observed)
| | Admin (app admin) | Curator (Alice) | Reviewer (Carol) |
|---|---|---|---|
| Tabs | Overview, Genes, Curations, Members, Settings | Overview, Genes, Curations, Members | Overview, Genes, Curations, Members |
| Genes toolbar | Add Genes, Assign to Curator | Add Genes, Assign to Curator | (nothing, no explanation) |
| Row menu | Start Precuration, Curation (disabled), Reassign, Edit Assignment, Remove from Scope | same minus Remove | **Start Precuration**, Curation (disabled) |
| Create Scope button | yes | yes | yes |
- [P2] Curators can reassign other curators' genes and edit assignments (`canAssignGenes = canCurate`, `GeneList.vue:344`); confirm that this is intended.
- Hidden actions are never explained; the disabled "Curation (requires approved precuration)" item is the only explained one, and it is good.

## Stability summary (D14)
- CLS on load: 0.004–0.046 (Genes tab 0.046 and Curations 0.043 come from `v-data-table` re-layout when rows arrive; TableSkeleton header widths differ from the final layout). Tab switches and modal open/close: 0.000.
- Flicker: the stat tiles render `0` before the statistics resolve. The dashboard replaces the whole page with a progress bar during load (no skeleton). The Genes empty state appears together with the table's "No data available".
- No horizontal page scroll at 390 px, but content is clipped inside the toolbar, tabs and chips (see the mobile findings).

---

## Top 10 recommendations (scopes and assignment)
1. **Mount a toast host** for `notificationStore.toasts` in `App.vue`, and delete the local snackbars. (P0: today every success and error message in this area is invisible.)
2. **Make "Add genes" scope-aware.** Reuse existing catalogue genes instead of failing with "already exists", rank the exact HGNC symbol first, and let the same dialog set curator, priority and due date. (P0/P1, `useAddGenes.ts`, `AddGeneModal.vue`.)
3. **Merge Add Genes + Assign to Curator into one flow**, add row selection with bulk "Assign curator / Set priority / Remove", and delete the `/scope-selection` wizard and the `/assignments` duplicate (or make `/assignments` a cross-scope read-only "My assignments" view).
4. **Fix tab deep links** (`ScopeDashboard.vue:147-200`): stable tab list and `router.replace`.
5. **One source of truth for scope counts**: a pipeline strip (Unassigned → Precuration → Curation → Review → Active) that refreshes after every mutation, replacing the 4 tiles, the progress bar and the Overview statistics list.
6. **Require a methodology (workflow pair) at scope creation**, and block or explain curation actions in the Genes tab while none is set.
7. **Enforce role-appropriate row actions** (no "Start Precuration" for reviewers), and explain hidden toolbar actions in one line ("Only curators and admins can add genes").
8. **Shared `BaseDialog`**: two widths, × close, Escape = Cancel, focus to the first field on open and back to the trigger on close, `[Cancel] … [Primary]` order. Fixes 9 dialogs at once.
9. **Unfix the footer** (`FooterBar.vue` `app`) and give mobile a real layout: a wrapping Genes toolbar, stacked table rows, collapsed stat strip, unclipped role chip.
10. **De-chip the Genes table**: text cells, one stage column, gene symbol + HGNC ID as the row anchor, colour reserved for the stage, no card view, no decorative DNA icons, consistent "Low/Medium/High" priority vocabulary everywhere.

## Bold redesign ideas
1. **Scope as a kanban-capable worklist.** The scope home *is* the gene list, grouped by pipeline stage (Unassigned, Precuration, Curation, In review, Active, Needs re-curation), with a table/board toggle. Drag a gene to a curator's swimlane to assign it. Overview and Statistics collapse into a one-line header: "PKD1 Kidney · SOP v11 · 42 genes · 7 in review · due 31 Dec".
2. **Paste-a-panel intake.** One textarea that accepts a gene list (symbols, HGNC IDs, PanelApp or GenCC export). It resolves each line against the local catalogue and HGNC, flags previous symbols and duplicates already in the scope, then shows a review table with a curator column pre-filled by round-robin or workload. One click commits everything through `/gene-assignments/bulk`.
3. **Curator workload sidebar.** On the Genes tab, a right rail lists scope curators with live counts (assigned / in progress / overdue) and their review load. Selecting rows and clicking a curator assigns them; the 4-eyes constraint (the reviewer is not the curator) is visible before work starts.
4. **Scope setup checklist instead of an empty dashboard.** A newly created scope shows a 4-step checklist (Methodology ✓/✗, Members invited/accepted, Genes added, First assignment) with inline actions, so a new scope admin never reaches the "No Schema Configured" dead end.
5. **Command palette for assignment.** `⌘K` → "assign PKD1 PKD2 to alice high due 2026-12-01" for power users who triage dozens of genes a week; every action is keyboard-reachable and undoable from a toast.
