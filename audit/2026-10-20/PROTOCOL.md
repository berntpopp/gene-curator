# Gene Curator UI/UX Review Protocol (2026-10-20)

Repeatable protocol so this review can be rerun and scores compared over time.
Previous run: `audit/UX_AUDIT_REPORT.md` (2026-02-28, 1-10 scale, weighted 5.3/10).

## 1. Environment

- Stack: `make hybrid-up`, `make backend` (API :8051), `make frontend` (Vite :5193). Seed data from `database/sql/004_seed_data.sql`.
- Roles: admin `admin@genecurator.org`, curator `alice.smith@genecurator.org`, reviewer `bob.jones@genecurator.org` (all `admin123`).
- Tooling (scratchpad, not in repo): Playwright 1.64 headless Chromium, axe-core 4, Lighthouse 13 (`npx lighthouse`), Impeccable detector (`impeccable detect`).
- Auth states: `node login.mjs` in the tools dir writes `state-{admin,curator,reviewer}.json` (localStorage tokens) for `browser.newContext({ storageState })`.
- Lighthouse runs against a production build (`vite build` + `vite preview`), never the Vite dev server, because dev mode serves unbundled modules.

## 2. Evidence captured per view / modal

| # | Evidence | How |
| --- | --- | --- |
| E1 | Screenshots desktop 1440x900 and mobile 390x844, full page | Playwright `page.screenshot({ fullPage: true })` |
| E2 | Dark theme screenshot (if the app has a toggle) | toggle or `emulateMedia({ colorScheme: 'dark' })` |
| E3 | Cumulative Layout Shift during load + 3 s and during the main interaction | `PerformanceObserver({ type: 'layout-shift', buffered: true })`, sum entries without `hadRecentInput`, record shifted node selectors |
| E4 | Flicker: content that appears, disappears and reappears (spinner->empty state->data, FOUC, theme flash) | Playwright `recordVideo` + ffmpeg frames at 20 fps, or a MutationObserver timeline of visible text |
| E5 | Console errors / warnings and failed requests | `page.on('console')`, `page.on('requestfailed')`, HTTP >= 400 |
| E6 | axe-core violations (WCAG 2.2 AA) | inject `axe.min.js`, `axe.run()` |
| E7 | Keyboard: Tab order, visible focus, Escape closes modals, focus returns to trigger | manual scripted Tab presses + screenshot of focus |
| E8 | States: loading, empty, error (API down / 403 / 404), long content, validation errors | route interception (`page.route`) to force states |
| E9 | Task timing: clicks and seconds for the view's primary task | scripted walk-through |

## 3. Scoring

Each view gets 0-100 on every applicable dimension. Anchors:
**90-100** exemplary, would ship in a best-in-class product · **75-89** good, minor polish ·
**60-74** adequate, noticeable friction · **40-59** poor, users struggle or the design looks dated/generic · **0-39** broken.

| Code | Dimension | What 90+ looks like |
| --- | --- | --- |
| D1 | Visual design and modernity | Intentional, current, calm; not a stock Vuetify/Material demo |
| D2 | Visual hierarchy and layout | One obvious primary action; scan path clear; consistent spacing rhythm |
| D3 | Typography | Clear type scale, readable line length, tabular numbers in data |
| D4 | Color and theming | Semantic, restrained color; status colors meaningful; dark mode correct |
| D5 | Consistency | Same patterns for the same jobs across views (tables, dialogs, buttons, chips) |
| D6 | Information architecture and navigation | User always knows where they are and how to get to the next step |
| D7 | Clarity and copy | Plain domain language, no jargon leakage, helpful empty/error text |
| D8 | Learnability | First-time curator succeeds without docs; affordances obvious |
| D9 | Efficiency | Few clicks, keyboard paths, bulk actions, sensible defaults, remembered filters |
| D10 | Feedback and system status | Loading, saving, success and failure always visible and specific |
| D11 | Error prevention and recovery | Validation inline and early, destructive actions confirmed/undoable, drafts safe |
| D12 | Accessibility | 0 serious/critical axe issues, AA contrast, full keyboard use, labelled controls |
| D13 | Responsiveness | Usable at 390 px, no horizontal scroll, tables adapt |
| D14 | Stability (perceived performance) | CLS < 0.05, no flicker, skeletons match final layout, instant-feeling transitions |
| D15 | Measured performance | Lighthouse perf >= 90 desktop / >= 75 mobile, LCP < 2.5 s, TBT < 200 ms |
| D16 | Authenticity (no "AI smell") | No generic gradient hero, emoji-as-icons, filler marketing copy, identical card grids, decorative noise |
| D17 | Domain fit | Matches how ClinGen/GenCC curators actually work (evidence, scores, provenance, review) |

Also score Nielsen's 10 heuristics 0-4 for the app as a whole.
View score = mean of applicable dimensions. App score = mean of view scores weighted by usage
(curation form/detail and scope dashboard x3, gene/curation lists x2, everything else x1).

## 4. Severity

- **P0** blocks a task or loses data · **P1** major friction or a11y failure on a core path ·
  **P2** noticeable polish/consistency issue · **P3** nice to have.

## 5. Finding format (every agent)

```
### <View or modal> (route / component path)
Scores: D1 nn · D2 nn · ... (n/a where not applicable)  → view score nn
Evidence: screenshot paths, CLS value, axe counts, console errors
Findings:
- [P1] <what> — <why it matters> — <concrete fix, file:line if known>
```

## 6. Outputs

- `audit/2026-10-20/findings/<area>.md` per review area
- `audit/2026-10-20/screens/<area>/...png`
- `audit/2026-10-20/data/` raw JSON (Lighthouse, axe, CLS)
- `audit/2026-10-20/UI_UX_REVIEW.md` synthesized report with recommendations
