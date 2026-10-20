# 05 – Administration (users, schemas, schema editor, workflows, admin gene DB, log viewer, access control)

Reviewer: admin-area agent · Date: 2026-10-20/21 · Protocol: `audit/2026-10-20/PROTOCOL.md`
Scripts: scratchpad `tools/admin/*.mjs` (Playwright 1.64 headless, axe-core 4). Raw data: `audit/2026-10-20/data/05-admin/`
(`views.json`, `dialogs.json`, `states.json`, `nonadmin.json`, `task3.json`, `logviewer.json`). Screens: `audit/2026-10-20/screens/05-admin/`.

**Environment notes (please read before acting on these findings)**
- The app's default theme is **dark** (`main.ts:22`, `localStorage.theme || 'dark'`). Screens are dark unless the file is named `*-light.png`.
- `bob.jones@genecurator.org` has `application_role = admin` in the running DB (`/auth/me`, `updated_at 2026-10-20T21:50Z`), but the seed (`004_seed_data.sql:773-780`) says `'user'`. Someone changed it during today's audit, probably another agent using the Edit User dialog. I did **not** revert it. I tested non-admin blocking with alice (curator) and carol (viewer). The seed value should be restored.
- Records I created (all prefixed UXR): users `uxr-77859@`, `uxr-58248@` (invited as curator to scope `uxr-test`), `uxr-40493@example.org`; workflow pair `UXR-pair-53760` (set inactive). Schema creation failed, so no schema records exist (see F-S1).
- I did not run Lighthouse (D15) for the admin views: they are lazy routes in the same bundle and are covered by the global Lighthouse pass. D15 = n/a below.
- axe numbers per view **exclude** 3 shell-wide violations present on every page: `image-alt` (critical, logo `img`), `color-contrast` (serious, `.version-info`, `.clickable` in the app bar) and `aria-tooltip-name` (serious, `#v-tooltip-v-35`). They are reported once in F-X5.

---

## Summary scores

| View / modal | Route / file | View score |
| --- | --- | --- |
| User Management | `/admin/users` · `views/UserManagement.vue` | **50** |
| Schema Management | `/admin/schemas` · `views/SchemaManagement.vue` | **48** |
| Schema Editor | `/admin/schemas/:id/edit` · `views/SchemaEditor.vue` | **36** |
| Workflow Management | `/admin/workflows` · `views/WorkflowManagement.vue` | **50** |
| Admin Gene Database | `/admin/genes` · `views/GenesTable.vue` | **49** |
| Not Authorized | `/not-authorized` · `views/NotAuthorized.vue` | **60** |
| Log Viewer drawer | `components/logging/LogViewer.vue` | **52** |
| Admin dialogs (user create/edit/details/delete, schema create, workflow create/view/edit) | inline in the views above | **55** |

Admin-area mean (unweighted, all "x1" per protocol): **50 / 100**: "poor, users struggle". The main blocker is that **schema authoring does not work at all from the UI** (F-S1, F-S2). The rest is a stock Vuetify CRUD shell with native `prompt()`/`confirm()` dialogs, silent failures and no relationship between the objects the admin manages.

### Primary task timing (D9)

| Task | Result | Clicks / keys / time (scripted) | Notes |
| --- | --- | --- | --- |
| Invite/create a user and give them a (scope) role | **Succeeds, across 2 unrelated surfaces** | ~10 clicks, ~45 keys, ~14 s scripted (realistic human: 60-90 s) | No nav link to `/admin/users`, so the URL must be typed. Create User only sets the app role (`user`/`admin`). Scope roles need Scopes → scope → Members tab → Invite. The user then stays **"Invited" (pending)** until they log in and accept; an admin cannot grant a role directly. `task1-*.png` |
| Create a new schema version from an existing one | **FAILS (P0)** | Duplicate: 1 click → "Failed to duplicate schema". New Schema: 4 fields → "Failed to create schema" | Every seeded schema fails the server's own validator (missing `label`), and "New Schema" posts an empty skeleton that the backend rejects. `task2-after-duplicate.png`, `task2-created-skeleton.png` |
| Pair a precuration + curation schema into a workflow | Succeeds | 6 clicks, 14 keys, 5.4 s | Fast. But it accepts a duplicate of an existing pair without warning, fixes the version at `1.0.0`, and the pair **vanishes from the UI once set inactive** (F-W2). `task3-created.png` |

### Access control (non-admins)

| Route | alice (curator) | carol (viewer) |
| --- | --- | --- |
| `/admin/users`, `/admin/schemas`, `/admin/schemas/:id/edit`, `/admin/workflows` | Redirect → `/not-authorized` ✔ | Redirect → `/not-authorized` ✔ |
| `/admin/genes` | **Page renders, with "Add Gene" and edit pencils** ✘ | **Same** ✘ |
| API `GET /users/`, `/users/statistics` | 403 ✔ | 403 ✔ |
| Main nav | "Curation Setup" menu hidden ✔ | hidden ✔ |

Evidence: `nonadmin-carol-admin-users.png`, `nonadmin-carol-admin-genes.png`, `data/05-admin/nonadmin.json`.

---

## Cross-cutting findings (all admin views)

- **[P1] F-X1 User Management is an orphan route.** `/admin/users` has no `showInDropdown`/`showInUserMenu` meta (`router/index.ts:339-347`) and nothing links to it (grep finds no other reference). An admin cannot find user management without knowing the URL. Fix: add it to the "Curation Setup" menu, renamed **"Administration"** (Users · Schemas · Workflows), or add an admin section to the user menu.
- **[P1] F-X2 Native `prompt()`/`confirm()` used for destructive and security actions.** Reset password uses `prompt()` with the password shown in plain text and no confirm field (`UserManagement.vue:558`). Delete schema uses `confirm()` (`SchemaManagement.vue:326`, `SchemaEditor.vue:373`), and so does delete workflow (`WorkflowManagement.vue:442`). These dialogs are unstyled and cannot show impact ("used by 3 workflow pairs and 12 curations"). Cancelling the password prompt shows a red **"Password must be at least 8 characters long"** error (`user-reset-password-after-cancel.png`), because `null` is treated as too short (`:559`). Fix: one shared `ConfirmDialog` with impact text and type-to-confirm for deletes, plus a real Reset Password dialog (masked, confirm field, or better a "send reset link" action).
- **[P1] F-X3 Inactive schemas and workflow pairs disappear from the admin UI.** The API defaults to `active_only=true` (`backend/app/api/v1/endpoints/schemas.py:43,226`) and the frontend never overrides it (`api/schemas.ts:9,74`). Setting a schema to "Inactive" in the editor, or a pair to inactive, removes it from the list with no way back. I verified this with `UXR-pair-53760`, which is only visible via `?active_only=false`. The Schema "Status" filter options *Draft/Deprecated* (`SchemaManagement.vue:250-254`) can never match anything, and "Draft" is impossible anyway (`utils/schemaTransformer.ts:60-61`). Fix: pass `active_only=false` from admin views, show a status column/filter that works, and keep a lifecycle of draft → active → retired.
- **[P1] F-X4 Dialog focus does not return to the trigger.** In all 8 dialogs tested, Escape closes the dialog ✔, but focus lands on `<body>` instead of the button that opened it (`dialogs.json` → `focusAfterClose`). The Tab cycle also passes through `<body>` once per loop before re-entering the dialog (`tabSeq` shows `!BODY`). Keyboard and screen-reader users lose their place in the table. Fix: use Vuetify's `activator` slot, or store and restore `document.activeElement` in a shared dialog wrapper; set `retain-focus` (default) and an initial focus target on the first field.
- **[P2] F-X5 Shell-wide axe violations on every admin page:** `image-alt` (critical, the logo has no `alt`), `color-contrast` ×2 (`.version-info` "Version 0.3.0 - Build: dev" and `.clickable` in the app bar), `aria-tooltip-name` ×1. The view-specific extras are listed per view below.
- **[P2] F-X6 Mobile (390 px) is broken on every admin view.** The page header puts a `size="large"` primary button next to an `text-h4` title without wrapping, so the button overflows to x≈496 (horizontal scroll: users 32 px, schemas 28 px, editor 83 px, workflows 106 px). The top nav has no hamburger and clips "CURATION" off-screen. The fixed footer (~110 px) covers content mid-page (`users-mobile.png`, `workflows-mobile.png`). Fix: a shared `PageHeader` component with `flex-wrap`, a nav drawer below `md`, and a non-fixed footer.
- **[P2] F-X7 Errors are generic or leak raw backend text.** "Failed to create schema" hides the useful 400 detail ("Field 'x' missing required property: label"). The users list on a 500 shows the raw `detail` ("boom") in a snackbar *and* "No users found" plus four `0` stat tiles (`state-users-error.png`), which is a false empty state. The editor 404 shows "Failed to load schema: Request failed with status code 404" with no way back except the browser (`state-editor-404.png`). Fix: inline error panels with Retry, mapped human messages, and the backend `detail` shown for 4xx validation errors.
- **[P2] F-X8 Inconsistent page frames.** Users, schemas and workflows use `v-container fluid`, while the admin gene DB uses a fixed `v-container` (`GenesTable.vue:4`) with a separate "Search & Filters" card. Primary buttons differ: `size="large"` with `prepend-icon` vs `<v-icon start>`. Cancel is `variant="text"` (users) vs `"outlined"` (schemas/workflows). The success colour on Save is `success` in the editor and `primary` elsewhere.
- **[P3] F-X9 Console noise:** `VUE_ROUTER_R0025 next() callback deprecated` is logged 5-10× on every navigation (`router/index.ts:388`). There were no console errors or failed requests on any admin view.

---

## Views

### User Management (`/admin/users` · `views/UserManagement.vue`, `views/user-management/*`)
Scores: D1 50 · D2 55 · D3 60 · D4 55 · D5 55 · D6 30 · D7 55 · D8 55 · D9 45 · D10 55 · D11 40 · D12 55 · D13 40 · D14 70 · D15 n/a · D16 40 · D17 40 → **view score 50**
Evidence: `users-desktop.png`, `users-mobile.png`, `users-light.png`, `dlg-user-*.png`, `menu-user-actions.png`, `state-users-*.png`. CLS 0.031 desktop / 0.005 mobile. axe: shell-only on the page; the details dialog adds `aria-input-field-name` ×2 and `aria-required-children` ×2 (`v-list` used as a layout). Console: no errors. Mobile h-scroll 32 px.
Findings:
- [P1] Orphan route, no navigation entry (F-X1).
- [P1] Scope roles are invisible and unmanageable here. The table shows only `user`/`admin` (app role). Gene Curator's real permissions are scope memberships, so an admin cannot answer "what can Alice do?" from this page. The create dialog has no "add to scope as curator/reviewer" step, so the "create user and give them a role" task needs a second surface (Scopes → Members → Invite) and ends as a *pending* invitation. Fix: add a "Scopes" column (chips like `kidney-genetics · curator`) and a "Scope memberships" section in the create/edit dialog that writes accepted memberships directly when an admin does it.
- [P1] Reset Password uses `prompt()` (F-X2): plaintext, no confirm, an error toast on cancel (`UserManagement.vue:557-570`).
- [P1] No self-protection. The row menu offers Deactivate/Delete for the signed-in admin's own row and for the last admin (`:203-221`), with no UI guard. Fix: disable those items with a tooltip ("You can't delete your own account" / "At least one admin is required").
- [P2] Meaningless stat tiles (AI smell). The four tiles take ~170 px above the table and push it below 4 screens on mobile. "Recent (30d)" is **always 0**: the API returns `total_users, active_users, inactive_users, role_distribution` and has no `recent_registrations` field (`:78`). It showed 0 right after a user was created today (`task1-user-created.png`). While loading, all tiles render `0` and then jump to the real values (flicker, `state-users-slow.png`). Fix: delete the tiles and show counts as filter tabs above the table ("All 7 · Active 7 · Inactive 0 · Admins 2").
- [P2] Card hover-lift on every `v-card`, including the table card and stat tiles (`:601-608` `transform: translateY(-2px)`). This decorative motion makes the whole table jump on hover and makes non-interactive tiles look clickable. Delete it.
- [P2] Role chips are loud: `admin` is red (`error`) and `user` blue (`userManagementHelpers.ts:13`). Red reads as a problem or danger. Use neutral or tonal chips, with admin as an outline.
- [P2] "Last Login" values are ~2 h in the future: Bob's `last_login` is `2026-10-20T23:50:45Z` while `updated_at` (same login) is `21:50:45Z`. The backend stores local time with a `Z` suffix. The UI then shows "Oct 21, 2026, 01:51 AM" next to a created time of "Oct 20, 11:56 PM". Fix the backend timestamp (use `datetime.now(UTC)`) and show relative times ("2 h ago").
- [P2] On a 500 the page shows "No users found" plus four zeros, which is a false empty state (F-X7).
- [P3] Search is a 50%-width outlined field with a lone "Refresh" button (`:88-112`). There are no filters for role or status and no bulk actions. The avatar is the same generic `mdi-account` icon for every user (`:130-132`); use initials.
- [P3] The details dialog repeats data already in the row (email, role, dates). Its "Activity Summary" shows `0 Genes Created / 0 Curations Created / 0 Total Contributions` for everyone (`UserDetailsDialog.vue:45-61`). Either show real recent activity (last curations, reviews, scopes) or drop it.

### Schema Management (`/admin/schemas` · `views/SchemaManagement.vue`)
Scores: D1 50 · D2 60 · D3 55 · D4 55 · D5 55 · D6 50 · D7 45 · D8 35 · D9 30 · D10 40 · D11 30 · D12 55 · D13 45 · D14 75 · D15 n/a · D16 45 · D17 35 → **view score 48**
Evidence: `schemas-desktop.png`, `schemas-light.png`, `schemas-mobile.png`, `dlg-schema-create.png`, `task2-*.png`, `state-schemas-*.png`. CLS 0.009 desktop / 0.076 mobile. axe: shell-only. Native confirm on delete was captured in `dialogs.json`.
Findings:
- **[P0] F-S1 "New Schema" always fails.** The dialog posts `field_definitions: {}, workflow_states: {}, ui_configuration: {}` (`SchemaManagement.vue:353-361`). The backend rejects this with 400 "Missing required field: field_definitions … Missing required workflow state: draft, submitted". The user sees only "Failed to create schema" (`task2-created-skeleton.png`). Fix: create from a server-valid template (minimum `workflow_states` draft/submitted, one example field with a `label`) or relax the validator for `is_active=false` drafts, and surface the backend `detail`.
- **[P0] F-S2 "Duplicate" fails for every seeded schema.** All 4 seed schemas fail the server's own validator (`POST /curation-schemas/{id}/validate` → `is_valid:false`: fields missing `label`, `evidence_summary` "invalid type: string"). The client-side duplicate (`stores/schemas.ts:164-181`) re-posts them and gets 400 → "Failed to duplicate schema" (`task2-after-duplicate.png`). As a result, **an admin cannot create a new version of any existing methodology**. Fix: (a) fix the seeds in `database/sql/004_seed_data.sql` so they validate, with a postgres test that asserts every seeded schema passes `/validate`; (b) add a server-side "New version" endpoint that copies the schema, bumps the version and sets the copy to draft.
- [P1] There is no version model. "Duplicate" creates "Name (copy)" with the **same version and same active flag** (`stores/schemas.ts:166-178`). With the validator fixed, this would create a second *active* schema of the same methodology that curators would immediately see. The UI has no lineage ("v1.1 supersedes v1.0"), no diff and no "used by N workflow pairs / M curations". Fix: a "New version" action (semver bump picker, draft by default, changelog field) and a version history list per methodology.
- [P1] Inactive schemas vanish (F-X3). The Status filter (Draft/Active/Deprecated) is dead UI.
- [P1] Delete has no impact check (native `confirm`, `:326`). Deleting a schema referenced by workflow pairs or curations needs to show those references and block or require a typed confirmation.
- [P2] Chip confetti (AI smell). Each row has three chips: Type (outlined, green/blue), Status (flat green) and **Version as a chip** (`:91-93`). Version is data, not a status; render it as tabular text `1.0.0`. Keep one status indicator.
- [P2] Identifiers are shown as display names: `ClinGen_SOP_v11`, `Standard_Precuration`. Add a human `display_name` ("ClinGen Gene-Disease Validity SOP v11").
- [P2] Copy: "Schema Management · Manage curation methodologies and schema definitions" vs nav label "Templates" (`router/index.ts:285`). One concept has three names. Pick **Methodologies** (or Templates) everywhere. The 404 branch says "This feature is under development" (`:401`), which is stale filler.
- [P3] Search, type and status filters sit in a separate card above a table that has its own card title "Schemas (4)". Merge them into the table toolbar.

### Schema Editor (`/admin/schemas/:id/edit` · `views/SchemaEditor.vue`)
Scores: D1 30 · D2 40 · D3 35 · D4 50 · D5 45 · D6 50 · D7 35 · D8 15 · D9 20 · D10 20 · D11 25 · D12 45 · D13 30 · D14 70 · D15 n/a · D16 50 · D17 20 → **view score 36**
Evidence: `schema-editor-desktop.png`, `schema-editor-desktop-full.png` (first 6000 px of a **44,035 px** page), `schema-editor-editmode.png`, `schema-editor-invalid-json.png`, `schema-editor-after-validate.png`, `state-editor-404.png`. CLS 0.009. axe adds `scrollable-region-focusable` (the `<pre>` JSON block cannot be reached by keyboard). Mobile h-scroll 83 px.

**Can a schema author understand and edit fields, scoring and UI layout without writing JSON? No.** The "editor" is a read-only `JSON.stringify` dump (`:112`, `:139`) and, in edit mode, two plain `v-textarea`s (`:114-124`, `:141-149`). It has no field list, no field form, no type picker, no preview of the rendered form, no scoring table and no layout editor.
Findings:
- [P0] Save failures are silent. `saveSchema` catches errors and only `logger.error`s (`:322-325`). There is no snackbar or inline error, and the page stays in edit mode with the spinner gone. Because the server validator rejects all current seeds (F-S2), **any save of an existing schema fails invisibly**, so the admin believes nothing happened or retries forever. Fix: show the backend `detail` inline next to the offending field or JSON line.
- [P0] "Validate Schema" gives no feedback. The request returns `200 {is_valid:false, errors:[…6 errors]}` and the result is only logged (`:335-347`; `validateVisibleFeedback: []` in `dialogs.json`). The single most useful diagnostic in the admin area is invisible. Fix: show a results panel listing errors and warnings, each linking to the field.
- [P1] There is no structured editor (D8 15). Required: (1) a **field list** (name, label, type, required, help text) with add/reorder/remove; (2) per-field form controls (type select from the dynamic-form registry, options for enums, HPO/MONDO ontology binding); (3) a **scoring table** (category → max points → default points, the ClinGen matrix); (4) a **layout panel** for sections/tabs; (5) a **live preview** using the same `DynamicForm` curators see. Keep "Edit JSON" as an advanced tab.
- [P1] `ui_configuration`, `validation_rules` and `workflow_states` cannot be edited at all, and the Scoring card is hidden when `scoring_configuration` is null (`:132`), so scoring can never be added to a schema that has none. The validator also warns "UI configuration missing 'sections' – form may not render properly" for 3 of 4 seeds, and that is unfixable from the UI.
- [P1] An invalid scoring JSON is only logged (`:300-307`); Save then throws in `JSON.parse` (`:319`), which is caught and logged, so again nothing happens.
- [P1] The view page is 44,035 px tall. It is a full JSON dump with no collapse, no search and no line numbers. Fix: a collapsible field tree, with JSON behind a tab.
- [P2] Edit-mode JSON uses a **proportional font**. `font-family="monospace"` is not a `v-textarea` prop (`:120`, `:147`), so indentation does not line up (`schema-editor-invalid-json.png`). The JSON parse error appears below a 20-row textarea, out of view, and gives a character position ("line 11 column 29") without highlighting the line. Use a code editor (CodeMirror 6 with the JSON language and schema-aware lint) if JSON stays.
- [P2] Statistics card: "Last Modified: **1/1/1970**" because `formatDate(null)` → epoch (`:266-268`). "Required Fields: **0**" for ClinGen SOP v11 because `required` is not stored on fields (`:272-273`). Both are misleading.
- [P2] The Actions card stacks four full-width outlined buttons in four different colours (info, secondary, warning orange for *Duplicate*, error). Duplicate is not a warning. Fix: a primary "Save" in the header, with Validate as secondary and Export/Duplicate/Delete in an overflow menu.
- [P2] Duplicate and delete failures are silent (`:360-369`, `:371-382`). "Go back" uses `$router.back()`, which leaves the app on a deep link; navigate to `SchemaManagement` instead.
- [P2] `{{ schema.schema_type }} schema v1.0.0` subtitle is lowercase and repeats the "Schema Type" field. The title switches "View Schema:" / "Edit Schema:" while sitting on the `/edit` route.

### Workflow Management (`/admin/workflows` · `views/WorkflowManagement.vue`)
Scores: D1 50 · D2 50 · D3 55 · D4 50 · D5 55 · D6 50 · D7 50 · D8 55 · D9 70 · D10 55 · D11 35 · D12 55 · D13 35 · D14 45 · D15 n/a · D16 45 · D17 50 → **view score 50**
Evidence: `workflows-desktop.png`, `workflows-light.png`, `workflows-mobile.png`, `dlg-workflow-*.png`, `task3-*.png`, `state-workflows-*.png`. **CLS 0.191 desktop / 0.103 mobile** (worst in the area): the table card, footer and headers shift at ~900 ms when two-line schema chips replace the loading row. axe: the view dialog adds `color-contrast` ×5 (grey subtitle text on the dark card, the "Active" chip), `aria-input-field-name`, `aria-required-children`. Mobile h-scroll 106 px.
Findings:
- [P1] F-W1 The "Workflow Stages Configuration" section is a static constant styled as configuration. It renders `WORKFLOW_STAGES` from the store (`stores/workflow.ts:104`) as five identical outlined cards (`:89-116`). Nothing is configurable, it is the same for every pair, and the cards end under the fixed footer. It is an identical card grid with decorative icons. It also leaks the role id `scope_admin`, which does not match the documented scope role `admin` (AGENTS.md: "admin, curator, reviewer, viewer"). Fix: replace it with a single horizontal stepper inside each pair's detail ("Entry → Precuration (Standard_Precuration v1.0.0) → Curation (ClinGen SOP v11) → Review (4-eyes) → Active"), or delete it.
- [P1] F-W2 Inactive pairs vanish (F-X3). Toggling "Active" off in Edit Workflow removes the pair from the table permanently (as far as the UI goes). Confirmed with `UXR-pair-53760`.
- [P1] There is no duplicate-pair or usage guard. A pair identical to `Qualitative_Complete_Workflow` was created without a warning. Delete uses `confirm()` and does not say which scopes use the pair (`:441-458`). The version is hard-coded to `1.0.0` (`:473`).
- [P2] The schema selects list names only (`item-title="name"`), with no version or status (`task3-curation-options.png`). Once versions exist, "ClinGen_SOP_v11" will appear twice with no way to tell the entries apart. Show `name · v1.1.0 · draft`.
- [P2] The pair→schema link is not navigable. The `Pre:`/`Cur:` chips (hard-coded `color="blue"`/`"green"`, `:40-46`) should link to the schema editor. The abbreviations "Pre"/"Cur" are unclear, and the stacked chips cause the CLS above.
- [P2] Hard-coded stage colours `blue/orange/green/purple/success` (`:375-384`) instead of theme tokens; the purple "Peer Review" eye icon is low contrast in dark mode.
- [P2] **Missing icon**: `mdi-workflow` does not exist in the installed `@mdi/font` (0 matches). The table card title and the nav menu item "Workflows" (`router/index.ts:308`) render an empty 24 px gap (`workflows-desktop.png`, left of "Workflow Pairs (3)").
- [P3] The View dialog is a `v-list` of label/value pairs with the value in low-contrast subtitle style. The values are the important part; invert the emphasis.

### Admin Gene Database (`/admin/genes` · `views/GenesTable.vue`)
Scores: D1 45 · D2 45 · D3 55 · D4 55 · D5 40 · D6 30 · D7 45 · D8 40 · D9 40 · D10 55 · D11 50 · D12 55 · D13 65 · D14 80 · D15 n/a · D16 50 · D17 40 → **view score 49**
Evidence: `genes-desktop.png`, `genes-light.png`, `genes-mobile.png`, `nonadmin-carol-admin-genes.png`, `state-genes-error.png`. CLS 0.009. axe shell-only.
Findings:
- [P1] **No role guard.** The route has `requiresAuth: true` but no `requiredRoles` (`router/index.ts:213-220`), so viewers and curators (carol, alice) get "Gene Database" with "Add Gene" and edit pencils (`GenesTable.vue:11-17,138-144`). Home also links every signed-in user here as "Manage Genes" (`Home.vue:22-29`).
- [P1] **"Add Gene" and "Edit" do nothing.** "Add Gene" links to the same route (`:13`). Edit pushes `?edit=<id>` (`:289-291`), which no code reads. These are dead affordances on the only "admin" gene surface.
- [P1] IA duplication. This view overlaps `/genes` (Gene Catalogue), `/genes/:id` and scope gene lists. It shows *less* data than the catalogue (symbol + an always-empty "Location" column showing "—" for all 13 genes) and has a different layout and container width. There are two BRCA1 rows (HGNC:1000 and HGNC:1100), and no admin tool exists to spot or merge duplicates. Fix: delete this route and fold admin gene actions (add via HGNC lookup, edit, merge duplicates, refresh from HGNC) into the Gene Catalogue behind an admin toolbar. If it stays, make it a real admin tool with HGNC-sync status, a duplicate detector and bulk import.
- [P2] Layout: the "13 genes" count is an outlined chip, the sort select floats mid-row away from the table (whose columns are also sortable, two competing sort controls), and "Clear All" is vertically misaligned with the inputs. Pagination is duplicated (v-data-table footer plus a separate `v-pagination`, `:165-173`).
- [P2] Error state: on a 500 it shows "No genes available in the database", a false empty state (`state-genes-error.png`).

### Not Authorized (`/not-authorized` · `views/NotAuthorized.vue`)
Scores: D1 55 · D2 65 · D3 60 · D4 60 · D5 60 · D6 50 · D7 50 · D8 60 · D9 60 · D10 n/a · D11 60 · D12 65 · D13 70 · D14 85 · D15 n/a · D16 55 · D17 50 → **view score 60**
Evidence: `nonadmin-carol-admin-users.png`.
Findings:
- [P2] The redirect replaces the URL with `/not-authorized` (`router/index.ts:425`). The user loses the address they tried, and Back returns to the forbidden page, which redirects again. Fix: render the 403 in place (keep the URL) or pass `?from=`.
- [P2] The copy is generic: "You don't have permission to access this page." It should say *which* permission ("Only platform administrators can manage users.") and who to contact (list admins or a mailto), and the primary action should go back to the previous page or the user's scopes. "Browse Genes" is irrelevant.
- [P3] The 120 px orange lock icon plus `text-h3` is oversized and alarm-styled for a routine permission message. Use a calm 48 px icon and body-size text.

### Log Viewer (`components/logging/LogViewer.vue`, opened from footer "Logs")
Scores: D1 55 · D2 55 · D3 60 · D4 55 · D5 50 · D6 45 · D7 45 · D8 50 · D9 60 · D10 60 · D11 60 · D12 40 · D13 50 · D14 85 · D15 n/a · D16 45 · D17 40 → **view score 52**
Evidence: `logviewer-admin.png`, `logviewer-curator.png`, `data/05-admin/logviewer.json`.
Findings:
- [P2] The developer tool is exposed to every user. The footer "Logs" link and a red unread badge (e.g. "5" after a failed duplicate) appear for curators too. It shows DEBUG lines such as "API Request: GET /auth/me", correlation IDs and "Disclaimer store initialized". Fix: show it only to admins or when `?debug=1`, and default the level filter to Warning+.
- [P2] Keyboard: opening it leaves focus on the footer button and Escape does not close the drawer (`stillOpen: 1`). axe adds 6 contrast failures (x-small chips such as `Memory: 5.83KB`, `Usage: 15/100`).
- [P3] "Memory: 5.83KB", "Usage: 15/100" and the "Max log entries" select are developer metrics that take a third of the drawer header.

### Admin dialogs (grouped)
Scores: D1 55 · D2 60 · D3 60 · D4 60 · D5 50 · D6 n/a · D7 55 · D8 60 · D9 60 · D10 50 · D11 45 · D12 50 · D13 55 · D14 90 · D15 n/a · D16 60 · D17 45 → **score 55**
Evidence: `dlg-user-create.png`, `dlg-user-create-validation.png`, `dlg-user-details.png`, `dlg-user-edit.png`, `dlg-user-delete.png`, `dlg-schema-create.png`, `dlg-workflow-create.png`, `dlg-workflow-create-select.png`, `dlg-workflow-view.png`, `dlg-workflow-edit.png`. CLS on open/close: 0 for all. Escape closes all ✔; focus return ✘ (F-X4).
Findings:
- [P2] The Create User "Create" button stays disabled until the form is valid (`UserManagement.vue:288`). The disabled text (~#4a5a80 on #232538) is near-invisible, and the user isn't told *why* it is disabled until they blur each field. Keep it enabled and validate on submit.
- [P2] Create User asks the admin to set a password for someone else and has no "send invitation email" option. The app-role select offers "User/Admin" with no explanation that scope roles are separate. Add helper text: "Admins manage the platform. Curator/reviewer rights are granted per scope."
- [P2] The Edit User dialog has no "unsaved changes" guard; Escape discards edits silently. That applies to all edit dialogs.
- [P3] Dialog titles mix `text-h5` (users) with the default size (schemas, workflows). Some headers use icons (workflow view/edit) and others don't.

---

## Nielsen heuristics (admin area, 0-4)

| # | Heuristic | Score | Why |
| --- | --- | --- | --- |
| 1 | Visibility of system status | 1 | Save and validate in the schema editor are silent; stat tiles show 0 while loading |
| 2 | Match with real world | 2 | snake_case schema ids, `scope_admin`, "Pre/Cur", JSON as the authoring UI |
| 3 | User control and freedom | 1 | Inactive items vanish; no undo; native dialogs; Back loops on 403 |
| 4 | Consistency and standards | 2 | Three names for schemas; mixed button and dialog styles; two gene DB views |
| 5 | Error prevention | 1 | No impact checks on delete, no self-delete guard, duplicate pairs allowed |
| 6 | Recognition rather than recall | 1 | Users page needs a typed URL; schema fields must be recalled as JSON keys |
| 7 | Flexibility and efficiency | 2 | Workflow pairing is fast; no bulk actions or keyboard shortcuts |
| 8 | Aesthetic and minimalist design | 2 | Stat tiles, chip confetti, static stage-card grid, hover lift |
| 9 | Help users recover from errors | 1 | Generic or raw messages, false empty states, no retry |
| 10 | Help and documentation | 1 | No inline help on field definitions, scoring or the role model |

---

## Top 10 recommendations (prioritised)

1. **Make schema authoring work (P0).** Fix the seeds so they pass `/validate` (add a postgres test that every seeded schema validates). Create new schemas from a valid template. Show backend `detail` on create, duplicate and save failures. (`SchemaManagement.vue:353`, `stores/schemas.ts:164`, `SchemaEditor.vue:322`, `004_seed_data.sql`)
2. **Show Validate results and save errors in the editor (P0).** Results panel with clickable errors; never `logger.error` only. (`SchemaEditor.vue:300-347`)
3. **Add a real "New version" flow:** server-side copy, semver bump, draft by default, changelog, "used by" list, version history. Replaces the client-side "(copy)" duplicate.
4. **Fetch inactive items in admin views (`active_only=false`)** with a working status filter (draft/active/retired), so nothing disappears. (`api/schemas.ts:9,74`)
5. **Put User Management in the navigation** under a single "Administration" menu (Users · Methodologies · Workflows) and guard `/admin/genes` with `requiredRoles: ['admin']`, or remove that route. (`router/index.ts:213,339`)
6. **Make scope roles visible and assignable from User Management** (Scopes column, membership editor in create/edit, direct grant for admins) so "create user and give them a role" is one flow.
7. **Replace `prompt()`/`confirm()`** with a shared ConfirmDialog (impact text, type-to-confirm) and a proper Reset Password flow. Add guards against self-delete and against removing the last admin.
8. **Fix dialog focus management** (return focus to the trigger, no `<body>` stop in the Tab cycle) in a shared `AppDialog` wrapper; make the LogViewer Escape-closable and admin-only.
9. **Strip the AI-smell decoration:** user stat tiles (one of them always 0), card hover-lift, version-as-chip, the static "Workflow Stages Configuration" card grid, the 120 px lock icon. Replace them with count tabs and an inline pipeline stepper.
10. **Fix mobile and stability:** a wrapping `PageHeader`, nav drawer below `md`, non-fixed footer, and reserved row height in the workflow table to remove the 0.19 CLS. Also fix the missing `mdi-workflow` icon, the 1/1/1970 date, the 2 h-future `last_login` and the false empty states on API errors.

## Bold redesign ideas

1. **Methodology Studio.** Replace the JSON editor with a three-pane builder: left, a field tree (sections → fields, drag to reorder); centre, a property inspector (label, type from the dynamic-form registry, required, ontology binding, help text, scoring points); right, a **live preview of the exact curation form curators will see**, with a "simulate scoring" toggle that fills sample evidence and shows the computed classification. JSON is an "Advanced" tab with schema-aware lint. Publishing a version runs `/validate` and shows a diff against the previous version.
2. **Methodology as a versioned object, not a row.** One page per methodology (e.g. "ClinGen Gene-Disease Validity") with a version timeline (v1.0.0 active, v1.1.0 draft), "used by" (workflow pairs → scopes → curation counts) and a guided "Promote to active" that explains the migration impact on in-flight curations.
3. **Workflow canvas.** Show each workflow pair as a horizontal pipeline (Entry → Precuration[schema vN] → Curation[schema vN] → 4-eyes Review → Active) whose nodes link to their schemas and show which scopes use the pipeline. Creating a pair means picking two nodes on that canvas, with duplicates flagged inline.
4. **People and access matrix.** Replace the user table with a users × scopes matrix where each cell is the scope role (admin/curator/reviewer/viewer/pending). Changing a cell grants the role directly, a row header handles platform-admin status, and a side panel shows the user's recent curations and reviews. This answers "who can do what where" on one screen.
5. **Admin command palette (⌘K):** "invite user…", "new version of ClinGen SOP", "pair schemas…", "deactivate user…", each opening the right focused dialog. This gives a fast keyboard path for the handful of admin chores, without separate pages for each.

---
I did not run Lighthouse or axe at 390 px (axe ran on desktop dark and light). I also did not test the LogViewer's download/clear actions or a real schema edit-and-save on a seed schema, which would have altered seed data. Risk: Bob's application role is currently `admin` in the dev DB, not the seeded `user`, and other agents' "reviewer" findings may be affected by that.
