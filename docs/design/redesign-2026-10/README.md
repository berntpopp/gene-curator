# Gene Curator redesign 2026-10

The target design for every page, modal and admin builder, plus the config architecture behind it. Use it to implement
and to check an implementation against the intended look.

- Live design canvas (owner access): https://claude.ai/artifact/Si7MT8F8rmjbUYZShNKUdm
- Epic: #264 · Config architecture and migration: [`CONFIG-ARCHITECTURE.md`](CONFIG-ARCHITECTURE.md)
- Why: UI/UX review `audit/2026-10-20/UI_UX_REVIEW.md` (51/100) and the code reviews in [`research/`](research/)
- `renders/` (PNG) and `source/` (`.dc.html` mock-ups) are **gitignored, local only**. Regenerate renders with
  `node source/_render/render.mjs source renders` from this folder (needs `playwright`; see the script header).

## Screens and issues

| Screen | Render | Issue |
| --- | --- | --- |
| Design language (tokens, type, classification mark, status, actions, inputs, delete list) | `Main.png` | #261 (tokens), #251, #250, #254, #255 |
| App shell: side rail, scope switcher, mobile bottom tabs | `MyWork.png`, `Phone.png` | #272 |
| Sign in | `SignIn.png` | #274 |
| My work inbox | `MyWork.png`, `Phone.png` | #277 (#226) |
| Curation workspace | `Curation.png` | #278 |
| Review as diff + approve dialog | `Review.png`, `ModalApprove.png` | #279 |
| Gene case file | `Gene.png` | #280 (#230) |
| Scope page + add genes and assign | `Scope.png`, `ModalAddGenes.png` | #281 |
| Gene catalogue (genes × scopes, scope picker) | `Catalogue.png` | #276 |
| Shared data table (search, chips, density, columns, pagination, URL state) | `Catalogue.png`, `Scope.png` | #275 |
| Command palette | `ModalPalette.png` | #273 |
| Delete with impact and type-to-confirm | `ModalDelete.png` | #249 |
| Methodologies, lineage, derive | `Methodologies.png`, `ModalDerive.png` | #282, #265, #271 |
| Workflow builder: canvas, table, code | `Workflows.png`, `Workflows-table.png`, `Workflows-code.png` | #282, #268, #269 |
| Stage form builder (opened from a workflow stage) | `FormBuilder.png` | #282, #267 |
| Point system: user-defined model, caps, bands, tests, trace | `Scoring.png` | #282, #266, #270 |
| Curation template studio | `Studio.png` | #282, #267 |

Bugs found while mapping the config system: #262 (engine-name lookup), #263 (double-counted total).

## Visual rules (summary of `Main.png`)

- **Colour:** cool-grey neutrals (canvas `#F4F5F7`, surface `#FFFFFF`, border `#DCE0E6`, ink `#141A33`, muted `#565E70`);
  navy `#1E2A5E` for actions and the rail (`#121833`); teal `#0B7A83` for focus, selection and links. Signal colours
  (done `#1F7A4D`, attention `#9A5B00`, failure `#B3261E`) only where action is needed. Dark theme uses the same hues.
- **Classification** is one mark everywhere: 4 bars, strength = filled bars (Definitive 4 … Limited 1, none hollow);
  only Disputed (amber) and Refuted (red) get a hue. Always with its label.
- **Type:** IBM Plex Sans 13 px body / 18 px line, Plex Mono for IDs, symbols and numbers, `tabular-nums`; sentence case;
  never upper-case buttons.
- **Density:** 200 px rail, 20 px gutters, rows 34 px compact / 44 px comfortable; every table has search, filter
  chips, pagination and keeps its state in the URL.
- **Elevation:** flat cards with a 1 px border; shadows only on overlays; no hover lift, gradients, glass or
  decorative icons in titles.
- **Dialogs:** 440 / 560 / 800 px; title as a question or action; Cancel (text) before the primary; destructive
  actions name the impact and offer a safer alternative.

## Checking an implementation

Take a screenshot of the implemented route at the render's size (1440 wide; phone 390 × 844) with seed data and
compare it side by side with the render. Differences in sample data are expected; differences in layout, hierarchy,
colour roles, density and copy tone are not. Sample identifiers in the mock-ups (PMIDs `31000001…`, "Example A et al.")
are placeholders, not real references.
