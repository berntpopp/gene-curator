# 01 - App shell, public and auth surfaces

Reviewer area: AppBar, navigation, FooterBar, MessageSnackbar, DisclaimerDialog, ErrorBoundary, LogViewer mount,
theme, page titles; views Home (anon + logged in), Login, Register, About, FAQ, NotFound, NotAuthorized, UserProfile.
Run 2026-10-20 against Vite dev (:5193) + API (:8051), headless Chromium 1.64, axe-core 4 (wcag2a/aa/21aa/22aa).

Evidence roots:
- Screens: `audit/2026-10-20/screens/01-shell/` (82 PNGs; naming `<view>-<role>-<desktop|mobile>-<dark|light>.png`)
- Data: `audit/2026-10-20/data/01-shell/` — `capture-anon_admin-dark_light.json` (CLS, layout-shift sources, text
  timeline, axe, console, failed requests per view/role/viewport/theme), `auth-flow.json`, `nav-ia.json`,
  `tab-order-home-anon.txt`, `video/` (+ `video/frames/`)
- Scripts (scratchpad, not in repo): `tools/shell/{capture,mobile,auth,auth2,auth3,lv,tab}.mjs`

Environment caveats:
- Dev DB drift: `bob.jones@genecurator.org` is application `admin` in the live DB (seed `004_seed_data.sql:777`
  says `user`). The "reviewer" nav therefore equals the admin nav in this run. The curator (Alice) is the only
  true non-admin role measured.
- D15 (Lighthouse) is not scored here: the protocol requires a production build, which this area run did not make.
- One capture (`notauth-anon-desktop-light`) hit `ERR_NETWORK_CHANGED` from Vite deps reload; ignored as dev artifact.
- Console on every view: only the vue-router `next()` deprecation warning (`router/index.ts:387-433`). No app errors.

---

## Cross-cutting: app shell (App.vue, AppBar, navigation, FooterBar, MessageSnackbar, DisclaimerDialog, LogViewer)

Scores: D1 45 · D2 50 · D3 55 · D4 50 · D5 55 · D6 45 · D7 50 · D8 55 · D9 45 · D10 55 · D11 50 · D12 30 · D13 20 · D14 40 · D15 n/a · D16 50 · D17 40 → **view score 46**

Evidence: `shell-viewport-{anon,admin,curator,reviewer}-{desktop,mobile}.png`, `flicker-reload-appbar-frames.png`,
`flicker-firstload-appbar-frames.png`, `nav-ia.json`, `tab-order-home-anon.txt`, `disclaimer-first-visit-{desktop,mobile}.png`.
axe on every page: `image-alt` critical (app-bar logo), `aria-tooltip-name` serious (footer Disclaimer tooltip),
`color-contrast` serious (app-bar title 2.85:1 and version line 2.14:1 in dark; version 3.06:1 in light).

Findings:
- [P0] **No mobile navigation at all.** At 390 px the app bar just overflows: for a curator, `CURATION`, theme
  toggle and the account menu sit at x=354-617 px, off-screen and unreachable (`nav-ia.json`, `shell-viewport-curator-mobile.png`).
  A mobile user cannot open Review Queue/My Work, cannot reach Profile, and **cannot log out**. The title collapses
  to "G… / V…" (`login-anon-mobile-light.png`). — Add `v-app-bar-nav-icon` + `v-navigation-drawer` below `md`
  (`useDisplay().mdAndDown`), render MainNavigation items as `BaseNavigationItem` list inside it (the component
  already says it is meant for "mobile nav" — `navigation/BaseNavigationItem.vue:1-30` comment); hide the version line
  and text labels on small screens. Files: `components/AppBar.vue:1-34`, `components/navigation/MainNavigation.vue:1-53`.
- [P1] **Invisible LogViewer drawer steals keyboard focus and is exposed to screen readers.** After 5 visible tab stops on
  Home the next 25+ Tab presses land on off-screen controls inside the closed `v-navigation-drawer` at x≈1466-1996
  (`tab-order-home-anon.txt`); "Application Logs … Search logs …" is in the accessibility tree and in `#app` innerText on
  every page. — Mount the drawer with `v-if="logStore.isViewerVisible"` (or `disabled`/`inert` when closed) in
  `App.vue:19-20` / `components/logging/LogViewer.vue:2-5`; also hide the "Logs" footer button from non-admins in
  production (`FooterBar.vue:51-68`) — a log console is a developer tool, not a curator feature.
- [P1] **Logged-out flash + white theme flash on every hard refresh while logged in.** Frames at 20 fps
  (`flicker-reload-appbar-frames.png`): ~250 ms pure white page (dark theme user!), then an app bar with only
  `GENE CATALOGUE` and no theme/account buttons for ~150 ms, then the full nav pops in and shifts
  (`main-navigation` layout-shift in every logged-in capture). The text timeline shows the same on `/` and `/profile`
  (`auth-flow.json` → `hardRefresh`). Causes: `index.html` has no background colour/inline theme bootstrap;
  `isAuthenticated` starts `false` and only flips after `/auth/me` resolves (`stores/auth.ts:20-42`); the menu and
  icon font render before that. — (a) inline `<style>html,body{background:#1A1A2E}</style>` chosen from
  `localStorage.theme` in a tiny inline script in `index.html`; (b) add an `authStatus: 'unknown'|'authenticated'|'anonymous'`
  state set to `unknown` when a token exists and render a fixed-width nav skeleton (or nothing) while unknown;
  (c) don't mount `<router-view>` until the first guard resolves (`router.isReady()` before `app.mount`).
- [P1] **`/auth/me` is called twice on every load** (`auth-flow.json` → `corrupt.reqs`: two `GET /api/v1/auth/me`):
  once from `App.vue:86` `authStore.initialize()` and once from the guard `router/index.ts:391-401`. — Memoise the
  init promise inside the store (`initPromise ??= …`) and drop the call in `App.vue`.
- [P1] **Footer is `app` (fixed) and permanently eats 76 px desktop / 109 px (13 %) mobile viewport**
  (`nav-ia.json` footer `{h:109, position:fixed}`; visible covering the login dev-card and profile password form in
  every full-page shot). A copyright line and GitHub links do not deserve sticky real estate in a data-entry tool. —
  Remove `app` from `<v-footer>` (`FooterBar.vue:2`) so it sits at document end; replace `bg-grey-darken-3` (hard-coded,
  ignores theme, clashes with the light theme) with `color="surface"` + top border token.
- [P1] **Navigation IA is opaque for every role.** Top level (desktop): anon 1 item; curator 3 (Scopes, Gene Catalogue,
  Curation▾); admin 4 (+ Curation Setup▾). "Dashboard" — the logical home for a logged-in curator — is buried in the
  avatar menu (`router/index.ts:87`), "My Work" and "Review Queue" are hidden in a "Curation" dropdown, and Home (`/`)
  stays a marketing page after login. The 4-eyes pending-review badge lives inside the closed dropdown
  (`MainNavigation.vue:175-179`), so nobody sees it. No active-route indicator on top-level buttons; no breadcrumbs.
  — Flatten to: **My Work · Review (n) · Scopes · Genes**, admin-only **Setup**; send logged-in users from `/` to
  `/dashboard`; put the review badge on the top-level item.
- [P1] **Role label leaks the wrong role system.** The account menu shows `alice.smith… / user` (raw, lowercase,
  `UserMenu.vue:383-391` – terminology has no `USER` key) — the application role, which says nothing about what Alice can
  do. Her real capability (curator in kidney-genetics) is shown nowhere in the shell. — Show scope roles
  ("Curator · Kidney Genetics") or nothing; never the raw `user` app role.
- [P2] Disclaimer: 237-word persistent `alertdialog` on first visit, before the user knows what the app is
  (`disclaimer-first-visit-desktop.png`). Initial focus goes to the overlay container, not the heading/button; Esc does
  nothing (intended, but there is no visual hint); on mobile the only button is 1 000 px below the fold
  (`disclaimer-first-visit-mobile.png`, button y=1814). It uses hard-coded `rgba(0,0,0,.87)` text colours
  (`DisclaimerDialog.vue:163-375`) and a fake 300 ms "loading" delay (`:336-342`). — Shrink to 3 bullets + "Read full
  disclaimer" link, add `scrollable` so actions stay pinned, drop the fake delay, use theme tokens.
- [P2] Logo and title are click targets made of `<div>`/`<span>` with `@click` (`AppBar.vue:3-16`): not focusable
  (tabIndex −1), no alt text (axe critical `image-alt`). Hover `scale(1.05)` on the logo is decorative. — Wrap logo+title
  in one `<router-link to="/" aria-label="Gene Curator home">`, `alt=""` on the image.
- [P2] App-bar title/version contrast fails AA in dark mode (white on `#5C9CE6` = 2.85:1). The dark theme's primary is
  too light to carry white text. — Use a darker app-bar surface in dark mode (e.g. `surface` + primary accent line) or a
  primary of ≥ #2F6FC0; move "Version: 0.3.0 - Build: dev" (hard-coded ref, `AppBar.vue:65-66`) to the About page or
  the account menu.
- [P2] Theme defaults to **dark** and ignores `prefers-color-scheme` (`main.ts:22`; `auth-flow.json` → OS light → dark).
  — `localStorage.theme ?? (matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light')`. Toggle icon shows
  the *current* state (sun when light), ambiguous — use an icon for the target state plus a tooltip.
- [P2] Snackbar stacking/feedback: login failure produces the same error three times (field message, inline alert,
  snackbar — `login-wrong-password.png`); after logout the stale "Login successful!" toast is still on screen and there
  is no "Signed out" confirmation (`auth-flow.json` → `logout.snack`). UserProfile ships its own private `v-snackbar`
  (`UserProfile.vue:200-207`) instead of `useNotifications`. — One notification channel; clear toasts on route/auth change.
- [P2] Typography: `App.vue:119` sets `font-family: 'Roboto'` and `index.html:141` preconnects to Google Fonts, but no
  font stylesheet is ever loaded, so the UI renders in whatever system Roboto/Arial exists. Uppercase-tracked Material
  buttons everywhere ("GENE CATALOGUE", "CURATION SETUP") read as 2018 Material demo. — Self-host one variable font
  (Inter/Roboto Flex via `@fontsource`), set `text-transform: none` on `.v-btn` globally via Vuetify defaults.
- [P2] ErrorBoundary's secondary action is labelled "Go to Dashboard" but the function is `goHome`
  (`ErrorBoundary.vue:33,107-110`) — fine target, misleading name; it is only used in the two schema-driven forms,
  so route-level errors still white-screen. — Wrap `<router-view>` in `App.vue:7` with ErrorBoundary keyed on route.
- [P3] No route transitions; no skip-to-content link; global styles in `App.vue:117-180` define unused helpers
  (`.gene-table`, `.info-card`, `.form-container`) and a `--v-theme-primary` scrollbar using raw var without `rgb()`
  (invalid, so it silently falls back).

---

## Home `/` — logged out (views/Home.vue)

Scores: D1 35 · D2 45 · D3 55 · D4 45 · D5 55 · D6 50 · D7 35 · D8 50 · D9 45 · D10 50 · D11 n/a · D12 45 · D13 45 · D14 35 · D15 n/a · D16 20 · D17 30 → **view score 42**

Evidence: `home-anon-desktop-{dark,light}.png`, `home-anon-mobile-{dark,light}.png`. CLS desktop 0.07, **mobile 0.30
(dark) / 0.74 (light)** — sources `v-container.py-8` (stats section) and the hero text/buttons. axe: 4 serious/critical
nodes (shell only). Console: router deprecation only.

Findings:
- [P1] **Textbook "AI smell" landing page.** Gradient hero (`Home.vue:244-254`, primary→secondary 135°), logo + H1 +
  "Advanced platform for genetic information curation and management with ClinGen compliance", four identical icon
  stat tiles, a "Key Features / Comprehensive tools for genetic data management" grid of six identical cards with
  64 px coloured icons and filler copy ("Powerful search capabilities…", "Comprehensive CRUD operations…",
  "Modern Architecture: Three-tier architecture with PostgreSQL, FastAPI, and Vue 3 for performance and scalability"),
  and hover-lift on every card (`:264-273`). Tech-stack bragging and "CRUD" are developer jargon aimed at no curator.
  "Dyadic names" is not a term curators use. — Replace with a quiet product page: one sentence of what it is, a live
  search box for genes, the public curation counts as a compact inline line, and "Sign in". Delete the features grid.
- [P1] **Stats load causes a big layout jump on mobile** (CLS 0.74): a 64 px spinner + "Loading statistics..."
  (`Home.vue:70-76`) is replaced by four 160 px cards. — Render a fixed-height skeleton matching the final grid
  (`v-skeleton-loader type="card"` × 4, same cols) or reserve min-height.
- [P2] Broken icon: "Modern Architecture" uses `mdi-architecture`, which does not exist in @mdi/font (verified) — an
  empty 64 px gap in the card (`Home.vue:188`, visible in `home-anon-desktop-dark.png`).
- [P2] Hero subtitle `text-medium-emphasis` on the gradient is light-grey on mid-blue; hero buttons "BROWSE GENES"
  (primary on primary-gradient) have little separation from the background. Hard-coded `color: white` (`:250`).
- [P2] Stat tiles are "meaningless stat tiles": "2 Curated Genes / 2 Active Curations / 2 Clinical Scopes /
  1 Pending Review" with no link, no time frame, no definition of "curated". — Make each a link to the filtered list or drop.
- [P3] `.gap-4`, `.h-100` re-implemented locally though Vuetify ships `ga-4` and `h-100` utilities (`:256-262`).

## Home `/` — logged in (same component)

Scores: D1 35 · D2 30 · D3 55 · D4 45 · D5 50 · D6 35 · D7 30 · D8 40 · D9 25 · D10 45 · D11 n/a · D12 45 · D13 40 · D14 35 · D15 n/a · D16 20 · D17 25 → **view score 37**

Evidence: `home-admin-desktop-{dark,light}.png`, `home-admin-mobile-dark.png`; CLS desktop 0.05, mobile 0.74.

Findings:
- [P1] **A logged-in curator lands on the marketing page.** The only personalised content is a "Recent Activity" card
  that contains no activity — just "Welcome back, admin@genecurator.org!" and a role chip (`Home.vue:105-128`).
  The secondary CTA is "Manage Genes" (`GeneAdmin`, an admin DB screen) for *every* logged-in user including curators.
  — Redirect authenticated users from `/` to `/dashboard` (or make Home the dashboard: my assignments, items awaiting
  my review, recently edited curations).
- [P2] Role chip colours encode `admin=error(red)`, `curator=warning(orange)` (`Home.vue:224-231`): red/orange for
  roles reads as alarm. Also shows app role `user`/`admin`, never the scope role.

## Login `/login` (views/Login.vue)

Scores: D1 55 · D2 65 · D3 60 · D4 55 · D5 60 · D6 60 · D7 50 · D8 65 · D9 55 · D10 50 · D11 15 · D12 50 · D13 55 · D14 60 · D15 n/a · D16 55 · D17 n/a → **view score 55**

Evidence: `login-anon-{desktop,mobile}-{dark,light}.png`, `login-empty-submit.png`, `login-wrong-password.png`,
`login-retry-after-error.png`, `login-success-redirect.png`, `focus-login-field.png`; CLS 0.037 desktop / 0.067 mobile
(card re-centres when the dev card mounts). Success with `?redirect=/profile` lands on `/profile` in ~270 ms. ✓

Findings:
- [P0] **One wrong password locks the form until page reload.** Backend detail "Incorrect email or password" contains
  the word "email", so `Login.vue:485-487` writes it into `fieldErrors.email`; that makes the form invalid, the submit
  button is `:disabled="!formValid"` (`:335`), and `fieldErrors` are only cleared inside `handleLogin`, which returns
  early when the form is invalid (`:458`). Verified: after correcting the password (and even retyping the email and
  closing the alert) the button stays disabled, Enter does nothing, and even the dev quick-login buttons fail
  (`auth3.mjs` output; `login-retry-after-error.png`). — Clear `fieldErrors` in a `watch(credentials, …)`; never map a
  generic credential error onto a field; do not disable submit — validate on submit instead.
- [P1] Error shown three times (red outlined email field + "Incorrect email or password" under it + tonal alert +
  snackbar "Login failed. Please check your credentials.") — `login-wrong-password.png`. — Keep only the inline alert,
  placed above the fields, `role="alert"`.
- [P2] Empty submit: button is pre-disabled (pale blue, looks broken, 1.9:1 against card); pressing Enter in the empty
  form gives no feedback at all; errors only appear after blur (`auth-flow.json` → `emptyEnterMessages: []`). — Enable
  the button and show errors on submit.
- [P2] No `autocomplete="username"/"current-password"` on the fields (`:292-316`) — password managers guess. No
  autofocus on email (initial focus `BODY`). The heading is an `h2` with no `h1` on the page. The card is
  `min-height:100vh` *inside* `v-main` (`:512-520`), so the page always scrolls and the dev card ends under the fixed footer.
- [P2] Glassmorphism on a flat background (`backdrop-filter: blur(10px)` + 135° gradient, `:513-529`) — invisible effect,
  pure decoration. "Login" as title and button; use "Sign in" consistently (Register links back with "Sign In", the app
  bar icon is labelled "Sign in").
- [P3] Dev quick-login shows names ("Login as Alice Smith/Bob Jones/Carol Williams") without the role they represent
  in this DB; label them "Curator (Alice)" etc. The 4th (Carol, viewer) has no matching row in `login.mjs`.

## Register `/register` (views/Register.vue)

Scores: D1 55 · D2 65 · D3 60 · D4 55 · D5 45 · D6 60 · D7 50 · D8 55 · D9 55 · D10 50 · D11 50 · D12 50 · D13 55 · D14 60 · D15 n/a · D16 55 · D17 n/a → **view score 55**

Evidence: `register-anon-{desktop,mobile}-{dark,light}.png`; CLS 0.035 / 0.065.

Findings:
- [P1] Password policy contradicts itself across the app: Register requires ≥ 6 chars + lower + upper + digit
  (`Register.vue:135-141`), Login enforces ≥ 6 (`Login.vue:442-445`), Profile change requires ≥ 8 with no class rules
  (`UserProfile.vue:252-253`). Rules are revealed one failure at a time. — One shared rule set from the backend
  constants, shown as a checklist under the field.
- [P2] Open self-registration with no explanation of what an account grants. FAQ says "Contact your system
  administrator to request an account… assigned the 'viewer' role" — contradicts both the form's existence and the
  code (it creates `role: 'user'`, `Register.vue:119-125`). After sign-up the user lands on the marketing Home with
  zero scopes and no "ask to join a scope" path.
- [P2] Same pre-disabled submit pattern and missing `autocomplete` ("name", "email", "new-password") as Login.

## About `/about` (views/About.vue)

Scores: D1 40 · D2 50 · D3 60 · D4 55 · D5 55 · D6 55 · D7 25 · D8 n/a · D9 n/a · D10 n/a · D11 n/a · D12 45 · D13 60 · D14 60 · D15 n/a · D16 20 · D17 25 → **view score 45**

Evidence: `about-anon-desktop-light.png`; CLS 0.043 / 0.10; axe adds **critical `aria-required-children`** and serious
`aria-input-field-name` on the static `v-list` (`About.vue:213-238`, `role="listbox"` without options).

Findings:
- [P1] Copy is developer changelog, not product: "a sophisticated Vue.js-based platform … has undergone a major
  architectural transformation … migrate to a modern three-tier architecture" (`About.vue:203-207`); tech-stack chips
  (Vue 3, Vuetify 3, Vite, Pinia, FastAPI…) as decoration. Contradicts README positioning ("methodology-agnostic").
  — Rewrite: what it is for, which SOP versions/methodologies are supported, who maintains it, how to cite, contact,
  version/build (move it here from the app bar).
- [P2] Static feature list rendered as interactive `v-list` → axe critical. Use `<ul>` or `v-list` with `role="list"`
  / `:nav="false"` and `lines`.

## FAQ `/faq` (views/FAQ.vue)

Scores: D1 55 · D2 60 · D3 60 · D4 60 · D5 60 · D6 50 · D7 35 · D8 50 · D9 45 · D10 n/a · D11 n/a · D12 55 · D13 70 · D14 85 · D15 n/a · D16 55 · D17 45 → **view score 56**

Evidence: `faq-anon-desktop-dark.png`; CLS ≈ 0.

Findings:
- [P1] **Answers are factually wrong about the UI**: "Notifications appear in the bell icon in the top navigation bar"
  (there is no bell; the count is a badge on the avatar), "Use the scope selector in the navigation" (none exists),
  "New users are assigned the 'viewer' role" (they get app role `user`; viewer is a scope role), "three user roles:
  Viewers/Curators/Administrators" (conflates the two role systems; reviewers and scope admins missing), bulk import in
  "Gene Administration" (menu item does not exist). (`FAQ.vue:20-79`). Wrong help is worse than none.
- [P2] Answers are HTML strings rendered via `v-html` with "•" characters as fake bullets and `<br/>` (`:12`, `:20-79`).
  No grouping (Getting started / Curation / Review / Admin), no search, no deep links (`#review-workflow`), no link to
  the actual screens. — Move content to markdown or structured data, render real lists, add anchors and "Go to …" links.

## NotFound `/some-missing-page` (views/NotFound.vue)

Scores: D1 50 · D2 70 · D3 60 · D4 45 · D5 55 · D6 55 · D7 60 · D8 n/a · D9 n/a · D10 n/a · D11 n/a · D12 55 · D13 70 · D14 80 · D15 n/a · D16 55 · D17 n/a → **view score 59**

Evidence: `notfound-admin-desktop-dark.png`; title "Page Not Found | Gene Curator" ✓; CLS ≈ 0.

Findings:
- [P2] 120 px **red** error icon for a 404 (`NotFound.vue:5`) signals danger rather than "wrong address". Copy does
  not echo the bad path or suggest search. Two equal-weight buttons ("Go Home"/"Browse Genes", primary vs grey
  secondary). — Neutral icon, show the requested path, a gene search box, one primary action.
- [P3] NotFound and NotAuthorized are copy-pasted twins with local `.gap-3`/`.fill-height` overrides — extract one
  `StatusPage` component.

## NotAuthorized `/not-authorized` (views/NotAuthorized.vue)

Scores: D1 50 · D2 70 · D3 60 · D4 50 · D5 55 · D6 50 · D7 45 · D8 n/a · D9 n/a · D10 n/a · D11 n/a · D12 55 · D13 70 · D14 80 · D15 n/a · D16 55 · D17 n/a → **view score 57**

Evidence: `notauth-admin-desktop-dark.png`, `notauth-anon-mobile-dark.png`.

Findings:
- [P2] "You don't have permission to access this page." — doesn't say which page, which role is needed, or how to get
  it (request scope access / contact scope admin). Anonymous visitors see it too with no "Sign in" action.
  The guard sends here only for app-role failures (`router/index.ts:423-428`); scope-role denials happen elsewhere, so
  this page does not cover the common case.

## UserProfile `/profile` (views/UserProfile.vue)

Scores: D1 45 · D2 40 · D3 55 · D4 50 · D5 45 · D6 55 · D7 45 · D8 60 · D9 55 · D10 50 · D11 40 · D12 40 · D13 60 · D14 65 · D15 n/a · D16 45 · D17 35 → **view score 49**

Evidence: `profile-admin-desktop-{dark,light}.png`, `profile-admin-mobile-dark.png`; CLS 0.017 / 0.024; axe:
**2× critical `aria-required-children`, 2× serious `aria-input-field-name`** (static info `v-list`s), label contrast
4.29:1 on password fields (light). Text timeline shows "Full Name: Not specified" before the real name loads
(`auth-flow.json` → `hardRefresh` t=513→645 ms).

Findings:
- [P1] Identity repeated three times (header name+chip+email, then "Account Information" list with email, name,
  role chip again) while the information a curator actually needs — **scope memberships and per-scope roles,
  pending invitations, ORCID, institution, expertise** (all in the `users` table) — is absent. — Replace the list with
  "Scopes & roles" table and an editable ORCID/institution section.
- [P2] "Activity Summary" is five zero rows ("Genes Created 0 … Total Contributions 0" with a star icon) — meaningless
  stat list; "Genes Created/Updated" is not a curator concept. — Show recent curations/reviews with links, or drop.
- [P2] Change password: no confirm field, no show/hide, min 8 vs Register's 6, button disabled until valid, private
  snackbar (`UserProfile.vue:154-207`). Full-screen `v-overlay` spinner (`:195-198`) blocks the page on load instead of a skeleton.
- [P2] Displays raw `admin`/`user` lowercase role in two chips; `Last Login` shows the current session, not the previous one.

---

## Auth flow end-to-end (summary of measured behaviour)

| Step | Result | Verdict |
| --- | --- | --- |
| First visit | 237-word blocking disclaimer, focus on overlay container, button below fold on mobile | P2 |
| Empty submit | Button disabled; Enter silent; errors only on blur | P2 |
| Wrong password | Error ×3 (field, alert, toast); **form then permanently disabled** | **P0** |
| Successful login with `?redirect=` | Redirects to `/profile` in ~270 ms, toast "Login successful!" | OK |
| Logout | Back on Home, tokens cleared, **no confirmation**, stale "Login successful!" toast still shown; browser Back shows `/profile` URL with Home content | P2 |
| Hard refresh while logged in | ~250 ms white flash (dark theme), ~150 ms logged-out nav, then nav pops in | P1 |
| Corrupt both tokens, open `/assignments` | `/auth/me` 401 ×2, refresh 401 → silent bounce to `/login` with **no "session expired" message and the `redirect` lost** | P1 |
| Corrupt access token only | Silent refresh works, lands on `/assignments` | OK |

Fix for the expiry case: in the 401 handler of `api/client` push `{ name: 'Login', query: { redirect, reason: 'expired' } }`
and have Login show "Your session expired. Sign in to continue."

## Nielsen heuristics (this area, 0-4)

| # | Heuristic | Score | Note |
| --- | --- | --- | --- |
| 1 | Visibility of system status | 2 | Toasts exist; logged-out flash, no session-expired message, no logout confirmation |
| 2 | Match with real world | 1 | Marketing/tech copy; app role "user" shown instead of curator/reviewer |
| 3 | User control and freedom | 1 | Login lockout after one typo; mobile users cannot log out |
| 4 | Consistency and standards | 2 | 3 password policies, Login/Sign in, two snackbar systems |
| 5 | Error prevention | 2 | Pre-disabled submits instead of guidance |
| 6 | Recognition rather than recall | 2 | Key destinations hidden in dropdown/avatar menu |
| 7 | Flexibility and efficiency | 1 | No shortcuts beyond Ctrl+Shift+L (logs), Home is a detour |
| 8 | Aesthetic and minimalist design | 1 | Gradient hero, feature grid, fixed footer, version string in app bar |
| 9 | Help users recover from errors | 1 | Triple error, locked form, generic 403 |
| 10 | Help and documentation | 1 | FAQ factually wrong about the UI |

---

## Top 10 recommendations (shell / public / auth)

1. **Fix the login lockout** (P0): clear `fieldErrors` on input, don't map generic credential errors to a field, stop
   disabling submit (`views/Login.vue:329-336, 457-494`). Add a test: wrong password → fix → submit succeeds.
2. **Ship a responsive nav drawer** below `md` with all menu items, account and logout (`AppBar.vue`, `MainNavigation.vue`).
3. **Unmount the closed LogViewer** and hide the Logs button outside dev/admin (`App.vue:19-20`, `FooterBar.vue:51-68`).
4. **Kill the auth/theme flash**: inline theme background in `index.html`, `authStatus: 'unknown'` state, await
   `router.isReady()` + single memoised `initialize()` (removes the duplicate `/auth/me`).
5. **Logged-in `/` → `/dashboard`**, and flatten the IA to My Work · Review (badge) · Scopes · Genes · Setup (admin).
6. **Replace the marketing Home** (gradient hero, Key Features grid, tech-stack claims) with a quiet public page: gene
   search, one-line purpose, sign-in. Delete the About tech-stack chips and rewrite About for curators.
7. **Un-fix the footer** (`FooterBar.vue:2` drop `app`), theme it with tokens, move version/build into About/account menu.
8. **One feedback channel**: route all messages through `useNotifications`, one inline alert per form, clear toasts on
   auth change, add "Signed out" and "Session expired — sign in again" (with preserved `redirect`).
9. **Fix a11y basics in the shell**: logo/title as one focusable `router-link` with alt, AA contrast for app-bar text
   in dark theme, static `v-list`s → semantic lists (About, Profile), `h1` on Login/Register/Profile,
   `autocomplete` attributes, focus into dialogs.
10. **Rewrite FAQ and Profile around real roles**: correct FAQ answers (no bell, no scope selector, viewer vs user),
    show scope memberships/roles on Profile, one shared password policy, respect `prefers-color-scheme`.

## Bold redesign ideas

1. **Work-first shell with a left rail.** Replace the Material top bar with a slim left rail (desktop) / bottom tab
   bar (mobile): *Inbox* (assignments + reviews waiting on me, with counts), *Scopes*, *Genes*, *Setup* (admin). A
   scope switcher sits at the top of the rail and scopes every list — the "scope selector" the FAQ already promises.
2. **Command palette (⌘K / Ctrl+K)** as the primary navigation: jump to gene by HGNC symbol/ID, open "my curation of
   PKD1", "review queue", "new precuration for <gene> in <scope>". Curators think in gene symbols, not menus.
3. **Public landing = the gene catalogue.** Logged-out `/` becomes a single search field over curated
   gene-disease assertions with classification badges (Definitive/Strong/…/Refuted, ClinGen colours) and provenance
   ("approved by 2 reviewers, SOP v11, 2026-09"). That is the product's credibility, not a feature grid.
4. **Identity = scope roles.** The avatar menu and Profile show a compact "Curator · Kidney Genetics / Reviewer ·
   Cardio" matrix with pending invitations to accept, so users always know what they can do where (and why a
   NotAuthorized happened, with a "Request access" button that notifies the scope admin).
5. **Quiet clinical visual language**: neutral surfaces, one accent, sentence-case buttons, tabular numerals,
   classification and workflow-stage colours as the only saturated colours; drop gradients, glass, hover-lifts and
   decorative 64 px icons app-wide.
