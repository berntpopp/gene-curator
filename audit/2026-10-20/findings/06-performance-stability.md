# 06 - Performance and visual stability (D14, D15)

Auditor: web-performance pass, 2026-10-20/21. Read-only on project source.

## Method and caveats

- **Build:** `vite build` (Vite 7) into a scratch dir with `VITE_API_BASE_URL=http://localhost:4193`, served by a tiny Node static server
  (`data/06-perf/serve.mjs`: gzip, `immutable` cache for `/assets`, SPA fallback, `/api` proxied to the running backend on 8051).
  This keeps API calls same-origin, so no CORS change and no second backend were needed. Everything I started has been stopped.
- **Lighthouse 13.5** against the production build: 8 routes x desktop preset + mobile default (simulated slow 4G, 4x CPU), **3 runs each, median by Performance score**.
  Authenticated routes: headless Chrome with `--remote-debugging-port`, tokens and disclaimer acknowledgement written to localStorage first,
  then `--disable-storage-reset`, with the HTTP cache cleared over CDP before every run (so all runs are cold).
  Reports: `data/06-perf/lighthouse/<route>-<preset>.report.{json,html}`, all medians in `lighthouse/summary.json`.
- **Stability:** Playwright plus system Chrome at 1366x800 against the production build, logged in as admin, **31 routes** (every router path including all 5 scope tabs).
  Per route: layout shifts with source nodes, LCP, a rAF-sampled DOM timeline (main text length and height, spinners, skeletons, empty-state and error text, number of app-bar buttons, theme),
  all `/api` requests with timing and size, a 4 s video, then frames at 25 fps and contact sheets.
  Client-side navigation and INP: clicking the real app-bar links and menus, opening a dialog, typing in a search field, with `PerformanceObserver('event')`.
  Raw data: `data/06-perf/stability.json`, `nav.json`, `analysis.txt`. Scripts: `stab.mjs`, `stab-probe.mjs`, `nav.mjs`, `lh.mjs`.
- **Noise:** other agents were hitting the dev server and backend at the same time. Lighthouse scores were very stable (spread at most 3 points, except home mobile 44/45/54).
  The backend restarted or dropped one connection mid-run, so the Lighthouse batch was resumed. **The API is local with a tiny seed dataset:** every endpoint answered in 2-20 ms
  (HGNC external fetch 130-170 ms). No endpoint was slower than 300 ms, so the API latency numbers say nothing about production. What matters is the request **count and order**:
  each extra RTT on a real network turns into visible flicker.

## Scores (protocol anchors)

| Dim | Score | Why |
| --- | --- | --- |
| D15 Measured performance | **55** | Desktop 92-98, but mobile 45-69 on every route (target >= 75). Mobile LCP 5.1-6.0 s and FCP 4.5-4.9 s (target LCP < 2.5 s). TBT 0-16 ms is excellent. The cost is almost all render-blocking bytes, not runtime. |
| D14 Stability | **62** | 24 of 31 routes have CLS < 0.05 in the browser trace. Outliers: home (0.118 desktop, **0.733** in Lighthouse mobile), admin/workflows 0.162, admin/schemas 0.090, genes 0.058 (Lighthouse desktop 0.130), scope genes 0.055. Every hard load shows a logged-out app bar, a blank content area, icons popping in, and stat cards that read "0" before the real value. Deep links to two scope tabs bounce back to Overview. Interactions feel instant (INP-ish 16-24 ms). |

## Lighthouse (median of 3, production build)

| Route | Preset | Perf (3 runs) | A11y | BP | SEO | LCP s | CLS | TBT ms | FCP s | SI s |
|---|---|---|---|---|---|---|---|---|---|---|
| home | desktop | **94** (94/94/94) | 88 | 100 | 92 | 1.00 | 0.112 | 0 | 0.88 | 0.88 |
| home | mobile | **45** (44/45/54) | 88 | 100 | 92 | 5.25 | 0.733 | 0 | 4.73 | 4.73 |
| login | desktop | **98** (98/98/98) | 89 | 100 | 92 | 0.96 | 0.039 | 0 | 0.86 | 0.86 |
| login | mobile | **69** (68/69/69) | 89 | 100 | 92 | 5.10 | 0.070 | 0 | 4.50 | 4.50 |
| dashboard | desktop | **97** (97/97/97) | 87 | 100 | 92 | 1.16 | 0.013 | 0 | 0.92 | 0.92 |
| dashboard | mobile | **66** (66/66/67) | 91 | 100 | 92 | 5.85 | 0.043 | 0 | 4.88 | 4.88 |
| scopes | desktop | **97** (97/97/97) | 83 | 100 | 92 | 1.12 | 0.010 | 0 | 0.90 | 0.90 |
| scopes | mobile | **67** (67/67/67) | 83 | 100 | 92 | 5.85 | 0.006 | 16 | 4.50 | 4.50 |
| genes | desktop | **92** (92/92/95) | 83 | 96 | 92 | 1.16 | 0.130 | 0 | 0.84 | 0.84 |
| genes | mobile | **67** (67/67/67) | 87 | 96 | 92 | 5.85 | 0.006 | 10 | 4.65 | 4.65 |
| scope-dashboard | desktop | **96** (96/96/96) | 78 | 100 | 92 | 1.20 | 0.010 | 0 | 0.92 | 0.92 |
| scope-dashboard | mobile | **66** (66/66/66) | 81 | 100 | 92 | 6.00 | 0.006 | 12 | 4.88 | 4.88 |
| curation-detail | desktop | **97** (96/97/97) | 87 | 100 | 92 | 1.17 | 0.010 | 0 | 0.85 | 0.85 |
| curation-detail | mobile | **67** (66/67/67) | 91 | 100 | 92 | 6.00 | 0.006 | 0 | 4.50 | 4.50 |
| admin-users | desktop | **97** (96/97/97) | 88 | 100 | 92 | 1.16 | 0.049 | 0 | 0.84 | 0.84 |
| admin-users | mobile | **66** (66/66/66) | 88 | 100 | 92 | 5.85 | 0.009 | 0 | 4.88 | 4.88 |

Common diagnostics on every route (mobile, from the median reports):

- **Render-blocking requests: about 2.6 s of estimated savings.** The 223 KB-gzip entry JS and the 113 KB-gzip CSS must download and parse before anything paints. The app is a pure client-rendered SPA with an empty `#app`.
- **Unused CSS: 105 KiB** (about 93% of the gzipped CSS). **Unused JS: 103-113 KiB** (about half the entry chunk).
- Total transfer is about 780 KiB per cold load. The single biggest asset is the **MDI icon font (woff2, 394 KiB)**.
- `layout-shifts` culprit on home: `main.v-main > div.v-container > div > div.v-container`, the hero logo pushing content down (mobile 0.733, desktop 0.112). The icon web font is also listed as a shift cause on `div.main-navigation` on every route.
- genes: Best Practices 96 because of a console error: `GET /api/v1/gene-catalogue/filters/scopes` returns **500** (reproduced with curl as admin).
- Accessibility 78-91: covered by the a11y track. The lowest score is the scope dashboard at 78.

## Per-route stability (hard load, production build, admin)

"Flicker events" come from the DOM timeline. "logged-out nav" means the app bar rendered the guest variant (3 buttons) before switching to the authenticated one (6 buttons). That is expected on login and register, which are guest routes.
"blank main" means the shell was painted while the content area was still empty, because the router guard was waiting for `/auth/me`. All timings are on localhost. Each phase lasts at least one network round trip in production.

| Route | Final path | CLS | Largest shift source | Flicker events (hard load) | API calls | Duplicates | Slowest API |
|---|---|---|---|---|---|---|---|
| home | same | 0.118 | div.v-row.align-center.justify-center (0.107) | logged-out nav, blank main, spinner | 4 | /auth/me x2 | /curations/ 8 ms |
| login | same | 0.041 | div.v-row.align-center.justify-center (0.0408) | logged-out nav | 0 |  | -  |
| register | same | 0.039 | div.v-row.align-center.justify-center (0.039) | logged-out nav | 0 |  | -  |
| about | same | 0.048 | div.mb-6 (0.0369) | logged-out nav, blank main | 3 | /auth/me x2 | /curations/ 7 ms |
| faq | same | 0.011 | div.main-navigation (0.0109) | logged-out nav, blank main | 3 | /auth/me x2 | /curations/ 7 ms |
| dashboard | same | 0.011 | div.main-navigation (0.0109) | logged-out nav, blank main, spinner | 5 | /auth/me x2 | /scopes/ 7 ms |
| scope-selection | same | 0.011 | div.main-navigation (0.0109) | logged-out nav, blank main | 4 | /auth/me x2 | /curations/ 6 ms |
| scopes | same | 0.011 | div.main-navigation (0.0109) | logged-out nav, blank main | 4 | /auth/me x2 | /curations/ 6 ms |
| scopes-create | same | 0.011 | div.main-navigation (0.0109) | logged-out nav, blank main | 4 | /auth/me x2 | /curations/ 11 ms |
| scope-overview | /scopes/:id/overview | 0.012 | div.main-navigation (0.0109) | logged-out nav, blank main | 5 | /auth/me x2 | /scopes/:id 14 ms |
| scope-genes | same | 0.055 | div.v-data-table-footer (0.0434) | logged-out nav, blank main, empty-state text | 8 | /auth/me x2, /curations/ x2 | /scopes/:id 13 ms |
| scope-curations | same | 0.018 | div.main-navigation (0.0109) | logged-out nav, blank main | 6 | /auth/me x2, /curations/ x2 | /scopes/:id 10 ms |
| scope-members | /scopes/:id/overview | 0.012 | div.main-navigation (0.0109) | logged-out nav, blank main | 6 | /auth/me x2 | /scopes/:id/statistics 11 ms |
| scope-settings | /scopes/:id/overview | 0.012 | div.main-navigation (0.0109) | logged-out nav, blank main | 7 | /auth/me x2 | /scopes/:id 12 ms |
| review-queue | same | 0.011 | div.main-navigation (0.0109) | logged-out nav, blank main, skeleton | 4 | /auth/me x2, /curations/ x2 | /curations/ 13 ms |
| curation-detail | same | 0.011 | div.main-navigation (0.0109) | logged-out nav, blank main, spinner | 8 | /auth/me x2, /validation/schema/:id/json-schema x2 | /validation/schema/:id/json-schema 13 ms |
| curation-edit | same | 0.026 | div.v-row (0.0134) | logged-out nav, blank main, skeleton, empty-state text | 11 | /auth/me x2, /curations/:id x2 | /scopes/:id 20 ms |
| curation-new | same | 0.013 | div.main-navigation (0.0109) | logged-out nav, blank main, skeleton, empty-state text | 8 | /auth/me x2 | /scopes/:id 19 ms |
| precuration-new | same | 0.012 | div.main-navigation (0.0109) | logged-out nav, blank main, spinner, skeleton | 12 | /auth/me x2, /validation/schema/:id/json-schema x5 | /scopes/:id 11 ms |
| genes | same | 0.058 | div.v-container.v-locale--is-ltr (0.0271) | logged-out nav, blank main, skeleton, error alert | 7 | /auth/me x2 | /gene-catalogue/ 20 ms |
| admin-genes | same | 0.011 | div.main-navigation (0.0109) | logged-out nav, blank main, skeleton | 4 | /auth/me x2 | /genes/ 15 ms |
| gene-detail | same | 0.011 | div.main-navigation (0.0109) | logged-out nav, blank main, spinner | 5 | /auth/me x2 | /external-validation/hgnc/fetch/HGNC:18040 129 ms |
| gene-summary | same | 0.011 | div.main-navigation (0.0109) | logged-out nav, blank main, empty-state text | 5 | /auth/me x2 | /auth/me 6 ms |
| assignments | same | 0.020 | div.main-navigation (0.0109) | logged-out nav, blank main, spinner | 7 | /auth/me x2 | /gene-assignments/ 16 ms |
| assignments-create | /scope-selection | 0.011 | div.main-navigation (0.0109) | logged-out nav, blank main | 4 | /auth/me x2 | /auth/me 7 ms |
| admin-schemas | same | 0.090 | div.v-data-table-footer (0.079) | logged-out nav, blank main | 4 | /auth/me x2 | /curations/ 7 ms |
| admin-workflows | same | 0.162 | div.v-card.v-theme--dark.v-card--density-defa (0.1508) | logged-out nav, blank main | 7 | /auth/me x2 | /workflow/peer-reviewers 16 ms |
| validation | same | 0.011 | div.main-navigation (0.0109) | logged-out nav, blank main, empty-state text | 3 | /auth/me x2 | /auth/me 32 ms |
| profile | same | 0.019 | div.main-navigation (0.0109) | logged-out nav, blank main | 7 | /auth/me x2, /users/:id x2, /users/:id/activity x2 | /users/:id/activity 8 ms |
| admin-users | same | 0.040 | div.v-data-table-footer (0.0288) | logged-out nav, blank main, spinner | 5 | /auth/me x2 | /curations/ 7 ms |
| not-found | same | 0.011 | div.main-navigation (0.0109) | logged-out nav, blank main | 3 | /auth/me x2 | /curations/ 7 ms |

Observations from the contact sheets in `screens/06-perf/contact-*.png` (frames every 40 ms from navigation start):

1. **Every hard load, about 40 ms:** the app bar shows only "GENE CATALOGUE" (guest navigation), footer links have no icons, and the logo is missing. About 80 ms: the full authenticated nav appears and the nav buttons shift (CLS 0.011 on `div.main-navigation` on **every** authenticated route). About 120-280 ms: the AppBar logo pops in. See `contact-dashboard.png` and `contact-home.png`.
2. **Blank content area** between shell paint and route render on every protected route (40-120 ms locally). The router guard awaits `/auth/me` before resolving the route, while `App.vue` has already rendered the shell.
3. **home** (`contact-home.png`): hero without logo, then "Loading statistics..." spinner, then stat cards. The logo arrives at about 240 ms and pushes the whole hero down (CLS 0.107; 0.733 on mobile Lighthouse, where the image arrives much later relative to the text).
4. **scope members/settings deep link** (`contact-scope-members.png`): renders the Members tab, then the `v-window` **slides back to Overview** about 300 ms later. The URL ends at `/overview`. Stat cards read `0 / 0 / 0 / 0` and then `0 / 2 / 0 / 3`.
5. **curation-new / curation-edit** (`contact-curation-new.png`): three different layouts within 400 ms. First a generic `card` skeleton, then an interim layout with a red **"0.00 - No Known Disease Relationship"** score card and grey bars, then the real form with header card, tabs and a score sidebar. The intermediate verdict is misleading as well as unstable.
6. **genes** (`contact-genes.png`): stat tiles show `0 0 0`, then `3 3 2`. A red **"Internal server error"** alert is inserted above the table (pushing it down by 92 px) because of the 500 on `filters/scopes`. The data-table footer pops in late. The footer "Logs" link also grows a red error badge.
7. **admin/workflows** (`contact-admin-workflows.png`): the table shows "Workflow Pairs (0) / Loading items... / 0-0 of 0", then 3 rows. The table grows by about 120 px and pushes the "Workflow Stages Configuration" card down (CLS 0.151, the worst in-app shift).
8. **Pre-JS paint is white:** `index.html` has no background and no inline splash, while the default theme is dark. On a desktop LAN this is one frame. On mobile it is the whole 4.5 s before FCP, then a white-to-dark switch.

### Client-side navigation and responsiveness (`nav.json`)

| Interaction | Max event duration (click/key to next paint) | What happens |
| --- | --- | --- |
| App bar: Dashboard -> Scopes | 16 ms | Old page stays about 70 ms, then a partial page, then rows at about 100 ms. `/scopes/` is **re-fetched** although the dashboard just loaded it. |
| App bar: -> Gene Catalogue | 16 ms | Skeleton (10 rows), then the error alert and data. 4 parallel requests. |
| Menu: Curation -> Assignments | 24 ms | Spinner, then data. |
| Menu: Curation setup -> Schemas | 24 ms | Content swap with no intermediate state. |
| Open "Add user" dialog (admin/users) | 24 ms | Dialog at about 50 ms, no shift. |
| Type "BRCA" in gene search | 16 ms per key | One debounced request, but the **table body is replaced by a 10-row skeleton**: height 1018 -> 1208 -> 1018 px on every search. |

INP-class responsiveness is good: no long tasks, Lighthouse TBT 0-16 ms. Perceived slowness comes from fetch-then-render sequencing, not from the CPU.

## Network (per load, see table above)

- **`GET /auth/me` twice on every hard load.** The router guard (`router/index.ts:392-396`) and `App.vue:88` (`onMounted -> authStore.initialize()`) both call it, and `initialize()` has no in-flight guard (`stores/auth.ts:33-48`).
- **`GET /curations/?curation_status=in_review&limit=200` on every page and every 60 s**, only to compute the review badge count client-side (`stores/workflow.ts:308-320`, `components/navigation/MainNavigation.vue:102-114`). Fine at 3 rows. With real data it becomes the largest payload on every page.
- **`/validation/schema/:id/json-schema` x2 per DynamicForm and x5 on precuration-new.** `DynamicForm.vue:481-492` (watch with `immediate`) and `DynamicForm.vue:524-527` (`onMounted`) both call `validationStore.generateJsonSchema()`, which has no cache check (`stores/validation.ts:92-106`). The getter `getJsonSchema` already exists.
- **profile:** `/users/:id` x2 and `/users/:id/activity` x2. `views/UserProfile.vue:344-358` uses both a `watch(..., {immediate:true})` and `onMounted`.
- **scope genes/curations, review-queue:** `/curations/` x2 (one is the badge call, one is the view).
- **edit curation:** `/curations/:id` x2. Up to 11-12 API calls on the curation and precuration forms.
- **`/schemas/curation-schemas` returns 37.9 KB** (the full schema list with field definitions) on settings, workflows, schemas and the curation form, just to populate selects.
- **Errors on load:** `/gene-catalogue/filters/scopes` 500 (genes); `/genes/:id/summary` 404 (gene-summary, rendered as an empty state).
- **Redirects:** `/assignments/create` -> `/scope-selection`; `/scopes/:id/members` and `/scopes/:id/settings` -> `/overview` (bug, see P1-4).
- **UserMenu never loads notifications on hard load.** `components/navigation/UserMenu.vue:170-174` only fetches if `isAuthenticated` is already true at mount, which it never is on a cold load, and there is no watcher. This is a functional bug found while tracing requests.
- No endpoint above 300 ms on this dataset. Waterfalls: protected routes cannot start their data fetches until `/auth/me` returns, so it is always one serial RTT before any view data.

## Bundle analysis (production build)

| Asset | Raw | Gzip |
| --- | --- | --- |
| Entry JS `index-*.js` | **674 KB** | **223 KB** |
| All JS (entry + 60 lazy chunks) | 1,265 KB | 362 KB |
| Entry CSS `index-*.css` | **800 KB** | **113 KB** |
| All CSS | 811 KB | 114 KB |
| MDI font woff2 (also ships .woff 588 KB, .ttf 1.3 MB, .eot 1.3 MB) | 394 KB | n/a |
| logo.png (192x192, shown at 48-120 px, preloaded `fetchpriority=high`) | 32 KB | n/a |

Entry chunk composition (source-map-explorer): **Vuetify 431 KB (64%)**, of which components are 319 KB, composables 70 KB, util 25 KB and directives 10 KB. After that: app src 58 KB, axios 51 KB, @vue/runtime-core 50 KB, vue-router 24 KB, reactivity and runtime-dom 32 KB, pinia 3.5 KB.

- **Routes are lazy:** 29 `() => import()` in `router/index.ts`, so each view is its own chunk. The largest are CurationFormView 108 KB, GeneList 72 KB and DynamicForm 70 KB, all lazy. That part is fine.
- **Vuetify is not tree-shaken.** `main.ts:15-16` imports `* as components` and `* as directives` and passes them to `createVuetify` (`main.ts:81-82`). This puts **every** Vuetify component in the entry chunk, even though `vite-plugin-vuetify({ autoImport: true })` is already configured in `vite.config.js:7` and would import only what templates use. The full component CSS ships too, which is most of the 800 KB CSS.
- **Full MDI icon font:** `main.ts:19` imports `@mdi/font/css/materialdesignicons.css`: 418 KB raw CSS with 7,481 icon classes, plus the 394 KB woff2. The source uses **171 distinct `mdi-*` names**, about 2% of the set. The font loads late, so icons pop in and buttons shift (seen in Lighthouse `layout-shifts` and in the contact sheets).
- **Web fonts:** none are actually loaded. `App.vue:123` sets `font-family: 'Roboto'` and `index.html:141-143` preconnects and dns-prefetches `fonts.googleapis.com`/`fonts.gstatic.com`, but no stylesheet is requested. Result: no FOIT or FOUT, but a wasted preconnect and typography that falls back to whatever sans-serif the OS has (Arial on Windows, DejaVu on Linux), so the UI looks different per platform. The `Roboto Mono` used in 4 evidence components falls back the same way.
- **Unused CSS:** about 105 KiB gzip according to Lighthouse, about 93% of the CSS.

## Root causes (file:line)

| # | Cause | Location | Symptom |
| --- | --- | --- | --- |
| R1 | All Vuetify components and directives registered globally, which defeats `autoImport` | `frontend/src/main.ts:15-16, 81-82` (plugin in `vite.config.js:7`) | 431 KB Vuetify in the entry chunk, 800 KB CSS, mobile FCP 4.5-4.9 s |
| R2 | Full MDI webfont and CSS | `frontend/src/main.ts:19` | 394 KB font plus 418 KB CSS, icon pop-in, `main-navigation` shift on every route |
| R3 | Auth resolved twice and after shell render; the guard blocks the route while the shell already shows the guest UI | `frontend/src/App.vue:84-88`, `frontend/src/router/index.ts:388-396`, `frontend/src/stores/auth.ts:33-48` | `/auth/me` x2, logged-out nav flash, blank main, serial RTT before any data |
| R4 | `v-tabs` bound to a route-param computed, while the Members and Settings tabs are `v-if`'d on role data that is not loaded yet, so Vuetify falls back to the first tab and the setter pushes `/overview` | `frontend/src/views/scope/ScopeDashboard.vue:147, 181, 195, 305-316, 390-398` | Deep link or reload on members/settings lands on Overview, with a slide animation |
| R5 | Whole-view `v-if="loading"` swaps to a thin progress bar or spinner, then the full layout | `ScopeDashboard.vue:31`, `CurationDetailView.vue:35`, `Dashboard.vue:28`, `GeneDetail.vue:22`, `SchemaEditor.vue:3`, `AssignmentDetail.vue:3`, `ScopeList.vue:106`, `GeneSummaryView.vue:13`, `MemberManagement.vue:47` | Layout pops from 0 to full height. Not a CLS hit because it is the first content, but a visible jump. |
| R6 | Skeleton does not match the final layout, and the intermediate form renders with default scores | `views/curation/CurationFormView.vue:24` (`type="card"`), `components/forms/SchemaDrivenCurationForm.vue:5, 38, 181` | Three layouts in 400 ms; a red "No Known Disease Relationship 0.00" flashes |
| R7 | Stats rendered as `\|\| 0` before data arrives | `ScopeDashboard.vue:80, 138`, `GeneCatalogueView.vue:19` (`summary.totalGenesCurated` defaults to 0) | Users see "0 genes" before the real number; reads as wrong data |
| R8 | Images without intrinsic size | `views/Home.vue:7`, `views/Login.vue:7`, `views/Register.vue:7`, `views/About.vue:7`, `components/AppBar.vue:4-11` (`v-img` with only `max-width`/`max-height`) | Home CLS 0.107 desktop and 0.733 mobile; login 0.041; register 0.039; about 0.048 |
| R9 | Data table with no reserved height; error alert inserted above the table | `views/WorkflowManagement.vue:22-28` (and the stages card below it), `views/SchemaManagement.vue`, `views/UserManagement.vue:122-125`, `views/GeneCatalogueView.vue:132-136` | workflows 0.151, schemas 0.079, users 0.029, genes 0.027+0.020 |
| R10 | Search swaps the table body for a 10-row skeleton | `views/GeneCatalogueView.vue:384-386` (`#loading` slot) | 190 px height jump on every keystroke-debounced query |
| R11 | Duplicate fetch triggers (an `immediate` watcher plus `onMounted`), no store-level cache or in-flight dedupe | `components/dynamic/DynamicForm.vue:481-492, 524-527`, `stores/validation.ts:92-106`, `views/UserProfile.vue:344-358` | json-schema x5, users x2, activity x2 |
| R12 | Review badge computed by downloading up to 200 curations, polled every 60 s | `stores/workflow.ts:308-320`, `components/navigation/MainNavigation.vue:102-129` | An extra list request on every page; grows with data |
| R13 | No pre-JS background or splash; dark is the default theme | `frontend/index.html` (no `<style>`), `main.ts:22` | White screen for the full FCP time on mobile, then dark |
| R14 | Backend 500 on catalogue scope filter | `GET /api/v1/gene-catalogue/filters/scopes` | Error alert on the core Genes page; Best Practices 96 |

Checked and not a problem: router-view has no transition (`App.vue:7`), so route changes are instant swaps. Theme is read from localStorage before `createVuetify` (`main.ts:22, 84`), so there is no light/dark flash after JS runs. `Dashboard.vue:100` starts with `loading=false` but sets it synchronously in `onMounted`, and no empty-state flash was measured.

## Prioritized fixes

| P | Fix | Where | Expected impact |
| --- | --- | --- | --- |
| **P1** | Drop `import * as components/directives` and let `vite-plugin-vuetify` auto-import. Optionally use `styles: { configFile }` to trim SASS. | `main.ts:15-16, 81-82` | Entry JS 674 KB -> about 300-350 KB raw (Vuetify 431 KB -> about 120 KB for the ~40 components used), CSS 800 KB -> about 250-300 KB. Mobile FCP/LCP about -1.5 to -2 s; mobile Perf about 66 -> 80+ (estimate). |
| **P1** | Replace `@mdi/font` with `@mdi/js` (Vuetify `mdi-svg` iconset, only the 171 used icons) or a subset font | `main.ts:19`, icon usages | -394 KB font and -60 KB gzip CSS. Removes icon pop-in and the `main-navigation` shift (0.011 CLS on every authenticated route). |
| **P1** | Give every logo `v-img` an intrinsic size (`width`/`height` or `aspect-ratio="1"`), or a plain `<img width height>`. Stop preloading the 192 px logo at high priority, or ship a 2x-sized copy. | `Home.vue:7`, `Login.vue:7`, `Register.vue:7`, `About.vue:7`, `AppBar.vue:4` | Home CLS 0.73 -> ~0 on mobile (Perf 45 -> about 65 before the bundle fixes); login/register/about CLS -0.04 |
| **P1** | Fix scope tab deep links: compute tab visibility from data that is already known, or render all tabs and disable them; do not let `v-tabs` write the fallback back to the route; ignore setter calls before the scope loads | `ScopeDashboard.vue:147, 181, 195, 305-316` | Reload or bookmark of Members/Settings works; removes the slide-back flicker |
| **P1** | Single auth bootstrap: memoize `initialize()` (store the promise), call it once (the guard only), and render the app bar user area and protected content only after it settles, with a neutral placeholder instead of the guest variant | `stores/auth.ts:33-48`, `App.vue:88`, `router/index.ts:392-396`, `components/navigation/*` | -1 request per load; removes the logged-out nav flash and the nav reflow on every hard load |
| **P1** | Fix the 500 on `/gene-catalogue/filters/scopes` (backend) and render filter-load errors inline in the filter, not as a page-level alert above the table | backend endpoint, `GeneCatalogueView.vue:132-136` | Genes page loses its error banner and 0.047 CLS; Best Practices 100 |
| **P2** | Reserve table space: keep `min-height` on data tables in a loading state (`loading-text` row or skeleton rows of real row height), render the footer from the start | `WorkflowManagement.vue:22-28`, `SchemaManagement.vue`, `UserManagement.vue:122`, `GeneCatalogueView.vue`, scope genes table | workflows CLS 0.16 -> <0.02, schemas 0.09 -> <0.02, users 0.04 -> <0.01 |
| **P2** | Layout-matching skeletons for curation create/edit (header card + tabs + score sidebar), and do not render the score card or verdict until the schema and data are loaded | `CurationFormView.vue:24`, `SchemaDrivenCurationForm.vue:5, 38` | One transition instead of three; no false "No Known Disease Relationship" |
| **P2** | Show skeleton or em-dash for stats until loaded instead of `\|\| 0` | `ScopeDashboard.vue:80, 138`, `GeneCatalogueView.vue:19`, Home stats | No "0 genes" misinformation flash |
| **P2** | Search keeps the current rows and uses the table's `loading` bar instead of the `#loading` skeleton slot when rows already exist | `GeneCatalogueView.vue:384-386` | Removes a 190 px jump per search |
| **P2** | Dedupe fetches: cache JSON schemas by id in `validationStore` and remove the duplicate `onMounted` call; one trigger in UserProfile; reuse loaded `scopes` in the store across views (stale-while-revalidate) | `DynamicForm.vue:481-492, 524-527`, `stores/validation.ts:92`, `UserProfile.vue:344-358`, `stores/scopes.ts` | Precuration 12 -> about 8 requests, profile 7 -> 5; instant back-navigation to lists |
| **P2** | Add a count endpoint for pending reviews (or `limit=1` plus total) instead of downloading 200 curations; refetch only on focus or visibility | `stores/workflow.ts:308`, `MainNavigation.vue:102-114`, backend | Removes the largest-growing request from every page |
| **P2** | Inline a background and theme bootstrap in `index.html` (`<style>html,body{background:#1A1A2E}</style>` plus a 3-line script reading `localStorage.theme`) and a minimal splash | `frontend/index.html` | No white-to-dark flash during the 4.5 s mobile FCP |
| **P2** | Replace whole-view `v-if="loading"` swaps with in-place skeletons of the final layout (at least the scope dashboard, curation detail, gene detail) | R5 list | Smoother first render; less "pop" at 100-300 ms |
| **P3** | Remove the unused Google Fonts preconnect, or self-host Roboto/Roboto Mono (woff2, `font-display: swap`, preload one weight) if the brand needs it | `index.html:141-143`, `App.vue:123` | Consistent typography across OSes; saves one wasted connection |
| **P3** | Fix the UserMenu notification load (watch `isAuthenticated`) | `UserMenu.vue:170-174` | Notifications actually load after a cold start |
| **P3** | Trim `/schemas/curation-schemas` for select lists (summary projection) | backend schemas endpoint | -38 KB on 4 views |
| **P3** | Drop `.eot`/`.ttf`/`.woff` font formats from the build (woff2 is enough for all supported browsers); this goes away entirely with `@mdi/js` | build | -3.2 MB on disk (not transferred, since browsers pick woff2) |

Expected combined result (estimate, not measured): mobile Lighthouse 66 -> 85-90 on app routes, LCP about 2.5-3 s on simulated slow 4G, CLS < 0.05 everywhere. With the bootstrap and skeleton fixes, a hard load would make one visual transition instead of four or five.

## Artifacts

- Lighthouse: `audit/2026-10-20/data/06-perf/lighthouse/*.report.{html,json}`, `summary.json`
- Stability and network: `audit/2026-10-20/data/06-perf/stability.json`, `nav.json`, `analysis.txt`, `stab-table.md`, `lh-table.md`
- Contact sheets (16 frames, 40 ms apart): `audit/2026-10-20/screens/06-perf/contact-{home,dashboard,genes,admin-workflows,admin-schemas,scope-members,scope-genes,curation-new}.png`
