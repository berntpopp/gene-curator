# Wave 10 monkey round 2: narrow re-check (origin/master afba66c4, UI :5190, API :8052, DB :5455)

Tester: re-check agent (Playwright MCP Chromium, curl/urllib). Desktop 1440x900, phone 390x844.
Screenshots (`r2-*.png`): /tmp/claude-1000/-home-bernt-popp-development-gene-curator/9c28a4b8-bf13-4193-9f9d-0a3aefa339b3/scratchpad/recheck/
Data created: users r2-cur2 (curator), r2-rev3 (reviewer), r2-sadmin (scope admin), r2-rev2 (reviewer, created in the UI);
Bob added as kidney-genetics reviewer; scope r2-public; genes PKD2, NPHS2, UMOD, PAX2, WT1, NPHS1, APOL1 (API) and HNF1B,
COL4A5, CLDN16 (UI intake); template "R2 Mini Curation" (published v2). KGDB Mendelian Curation is at methodology version 2
(reviewers_required 2, imported through the UI to test the two-reviewer flow); HNF1B is active (Limited, 6 points).

## 1. Round-1 findings

### API (MONKEY-API-R1.md)

| id | verdict | evidence |
|---|---|---|
| H1 | fixed | 6 parallel creates (3 users x2, WT1, same entity): 1x201, 1x200 (same user, idempotent), 4x409; one precuration exists |
| M1 | fixed | scope-admin PAT flipping a private scope with export_evidence_public on to public: 403 "needs a signed-in person"; anonymous export stays 404 |
| M2 | fixed | KGDB summary ends "... supports a STRONG gene-disease relationship." |
| M3 | fixed | 2 distinct variants, no recurrence: only band_margin/experimental_over_genetic flags, no hotspot |
| M4 | partially fixed | new assignments keep due_date (bulk 2026-12-15, single 2026-12-31); bulk assign onto an existing unassigned gene drops it (R2-2) |
| L1 | fixed | GET /curations/{id}/score returns `warnings` (3 entries) |
| L2 | fixed | submit 422 lists `probands[2].zygosity Required field is missing`, `segregation[0].families Value must be a whole number` |
| L3 | fixed | dry run of a type-clashing schema: action "refused" with its error |
| L4 | fixed | read-only token: import_methodology absent on /mcp and /mcp/full; RW token sees it on /mcp/full only |
| L5 | fixed | "   x   " -> "1 characters after trimming, min 3"; audit row has old and new values plus reason |
| L6 | open by design | curator adding a member: 403 "Requires admin role or higher" (clearer); 4-eyes refusals still 400 |
| L7 | fixed | two concurrent `scripts/backup.sh` runs in one second: both exit 0 (mktemp partials; same final name, last wins) |
| L8 | fixed | submit with PMID 99999999: 422 "PMID 99999999 not found in Europe PMC" (needs network) |

### UI (MONKEY-UI-R1.md)

| id | verdict | evidence |
|---|---|---|
| B1 | fixed | KGDB curation detail and reviewer page render tables, score trace, flags (r2-51, r2-52, r2-54) |
| B2 | fixed | P2 with blank points scores 1; probands 4.00 = capped c.494G>A 2 + P2 1 + P3 1 (r2-46) |
| B3 | fixed | UI-built flat schema: test with homozygous + heterozygous rows passes total 3 (r2-90) |
| B4 | fixed | Workflow picker on new precuration; APOL1 saved on KGDB Susceptibility schema, relationship "Susceptibility (risk allele)" (r2-36) |
| B5 | fixed | duplicate HNF1B entity: inline alert with "Open the existing precuration", no orphan draft (r2-35) |
| B6 | partially fixed | typing filters; clearing the box keeps the old filter (R2-1) |
| B7 | fixed | new template opens with section "Main"; Add section visible (r2-73) |
| B8 | fixed | Case row: "case_row requires blank_at" until Default is set, then No problems |
| B9 | not re-tested | no multiple-choice/list rule in the flows run |
| B10 | fixed | probands columns in authored order (Proband, Variant, Variant class, Zygosity, ...) |
| B11 | fixed | Templates at 390: scrollWidth 375 = clientWidth, actions wrap (r2-11x-phone-templates) |
| B12 | fixed | trace lists "Rules applied" (row rule, LOD step) and "Capped groups" (r2-46) |
| B13 | still broken | validation box gone, but an untouched new precuration still shows red "Required field is missing" on every required field (r2-31, r2-32) |
| B14 | fixed | required booleans are Yes/No radios; No clears the error |
| B15 | fixed | "31000021, 31000022" -> 2 chips; "VarSeq \| https://example.org/search?q=a,b&x=1,2 \| 31000020" stays one entry (r2-48) |
| B16 | not re-tested | |
| B17 | fixed | Total Fields 1 -> 2 live after adding a field |
| B18 | fixed | My work and header show "Autosomal dominant" |
| B19 | fixed | users sorted by name, stable across reloads; header count updated to 8 after create |
| B20 | still broken (follow-up) | curation row "AI second view" still leads to "No AI second view here" (r2-53); precuration rows no longer show it |
| B21 | fixed | anonymous /login: no API calls, no console errors |
| B22 | fixed | versions "v11.0", "SOP v11", "alpha" |

Totals: 28 fixed, 3 still broken (B13, B20, L6 by design), 2 partially fixed (M4, B6), 2 not re-tested (B9, B16).

## 2. KGDB methodology import

| step | result |
|---|---|
| UI Import methodology, dry-run plan | 4 templates + 2 pairs Create, scope default Update; "Nothing is written until you confirm" (r2-01) |
| Confirm | toast names each object: "KGDB Mendelian Precuration published as version 1; ... Scope default kidney-genetics updated" |
| REST re-import (dry run and write) | all 7 items "unchanged" |
| Bundle with reviewers_required 2 | plan: one row "Publish new version", others Unchanged; toast "KGDB Mendelian Curation published as version 2" (r2-03, r2-04) |
| Broken bundle | banner "The file cannot be imported", row-anchored errors, "Refused"/"Blocked" chips, Import disabled (r2-05) |

## 3. KGDB flows unblocked by B1

| step | result |
|---|---|
| Intake HNF1B, COL4A5, CLDN16 (+PKD2 in scope, 1 unknown) with Alice + due 2026-12-01 | "3 genes added, 1 already in scope"; due date stored on all 3 |
| Precuration HNF1B (Mendelian), APOL1 (Susceptibility picked by hand) | both submitted; Bob approves both from the queue with a confirm dialog |
| Curation HNF1B: P1 de novo, P2 blank points, P3 compound het (phase confirmed), P4 recurrent variant, segregation 2 fam / LOD 3.2, detectability list cells incl. URL with commas | live score 6.00 Limited; LOD 3.2 -> 2 points; group cap 3 -> 2; data stored as entered |
| Scope admin disease correction (API, draft) | 200; then submit |
| Detail page | renders; tables, rules_applied, capped groups, flags band_margin + hotspot |
| Reviewer (Bob) Approve | item Accept gating works; "Approval recorded; more reviewers must approve"; "You approved; 1 more needed" |
| Corrector (r2-sadmin) | page shows "No actions available"; API assign/transition 400 "you corrected this curation's disease entity" |
| Second reviewer r2-rev2 (created in UI) | "Curation approved and activated"; status Active |

## 4. Polished flows (#587)

| flow | R1 | R2 | top remaining friction |
|---|---|---|---|
| Schema builder | 4 | 7 | Tests still need hand-written evidence JSON; Create stays on the list (no jump to editor); Text/String and Single choice/Choice (enum) duplicates remain |
| Import methodology | 7 | 8 | raw OS file chooser with no explanation; "Publish new version" rows give no diff of what changed |
| KGDB curation | 3 | 7 | score panel hidden until the first edit (R2-3); red required errors on an untouched precuration (B13) |
| Intake | 7 | 8 | resolve step does not flag genes already in scope; My work has no Due column |
| User Management | 6 | 7 | clearing search keeps the old filter (R2-1) |
| Catalogue / phone | 7 | 8 | phone "No genes match" empty state sits off-screen inside the horizontally scrolling table |

Builder checks that passed: Evidence table / Group by / Points column / condition Column and Values are pickers fed by the
schema's own table (r2-84, r2-86); section key "probands" -> "Unknown evidence field: probands.probands" and 2 errors (r2-87);
publish dialog with validator report and impact; "Published version 2". Score panel states: populated panel, rules, caps and
flags correct once shown. Users: name sort, scope display names, remove-role confirm (r2-15), create with first scope role
(toast "User created and added to Kidney Genetics as reviewer"). Catalogue: Disagreements chip sets `?agreement=disagree`.
Phone 390: templates, scope dashboard (2x2 stats), users, curation detail, my work, catalogue: no horizontal page overflow.

## New bugs

| id | sev | steps | expected | actual | screenshot |
|---|---|---|---|---|---|
| R2-1 | medium | User Management: type "bob", wait, delete the text (or Refresh) | full list returns | list stays filtered to Bob; a user created meanwhile is not listed. `debouncedSearch` empty branch calls `fetchUsers()` but never `usersStore.clearSearch()`, so `paginatedUsers` keeps `searchResults` (views/UserManagement.vue:436) | r2-13-users-cleared-search.png |
| R2-2 | low | POST /gene-assignments/bulk with curator + due_date for a gene already in the scope without curator (UMOD) | due_date stored | curator and priority set, due_date null; crud/gene_assignment.py bulk "existing without curator" branch ignores due_date | (API) |
| R2-3 | medium | Open a fresh KGDB curation draft (APOL1, HNF1B) at 1440 | score panel at 0 points from the start (a2a54dc1) | no panel and no score request until the first edit; panel then pops in (layout shift). CurationFormView `scoreShown` only flips when `frame.score` arrives | r2-41, r2-120, r2-121 |
| R2-4 | low | Reviewer Approve dialog on a KGDB curation | methodology-neutral label | "Checked against SOP v11" | r2-55-approve-dialog.png |
| R2-5 | low | Corrector (scope admin who corrected the disease) opens the in-review curation | reason why approval is blocked | "No actions available"; the first reviewer is not told 2 approvals are required until after approving | r2-59-corrector.png |
| R2-6 | low | Curation form, focus outside any menu, press Escape | nothing / close menu | "Discard unsaved changes?" dialog | r2-45-scrim.png |
| R2-7 | low | Curation detail / review page | labels and blanks hidden | Evidence changes shows raw enum values (compound_heterozygous, cnv_whole_gene_or_exon_deletion, lof); read-only tables print "none" in every empty cell | r2-51, r2-52 |
| R2-8 | low | Duplicate-entity precuration, Save draft | only the duplicate alert | also a "Form Validation Errors" box for a draft | r2-35-duplicate.png |

Severity count: medium 2, low 6.

## Console and network

This session: only expected 409s (duplicate precuration). No 5xx, no uncaught errors. The browser log still holds R1
entries (query.trim TypeError, 401s) from before this session.

## Not tested

B9, B16; precuration/curation forms at 390 px; approvals_require_session; review through MCP; disease-correction dialog in
the UI (only reachable for a legacy gap, done through the API); L8 depends on Europe PMC being reachable.
