# Wave 10 monkey round 3: re-check of R2-1..R2-8, M4, B6, B13 (origin/master ab07af6a, UI :5190, API :8052, DB :5455)

Tester: round-3 re-check agent (Playwright MCP Chromium 1440x900, urllib against the API). Fresh database.
Screenshots (`r3-*.png`): /tmp/claude-1000/-home-bernt-popp-development-gene-curator/9c28a4b8-bf13-4193-9f9d-0a3aefa339b3/scratchpad/recheck3/
Setup: KGDB bundle imported through the UI (7 Create/Update rows), then a copy with KGDB Mendelian Curation
reviewers_required 2 imported through the UI ("Publish new version", rest Unchanged). Users r3-sadmin (kidney scope admin),
r3-rev2 (reviewer), r3-late; Bob added as kidney reviewer. Genes HNF1B, UMOD, PKD2, NPHS2, WT1, PAX2 (API).
WT1 curation (schema v2): CLDN16 test evidence, scope-admin disease correction on the draft (POST .../disease-correction 200),
submitted to Bob; PAX2 curation with compound het / lof / missense / CNV detectability submitted to r3-rev2.

| id | verdict | evidence |
|---|---|---|
| M4 | fixed | single create with curator + due 2026-12-31 stores it; bulk (UMOD existing unassigned + NPHS2 new) stores 2026-12-15 on both (DB row checked) |
| B6 | fixed | Users: typing "bob" filters to Bob, no console errors; clearing restores the full list (r3-01) |
| B13 | mostly fixed | untouched new precuration: no "Required field is missing", no error box (r3-02); residual: Disease entity tab shows red "MONDO disease is required" on the MONDO picker before any input (r3-03) |
| R2-1 | fixed | type "bob", create r3-late via API, clear box: 7 users listed incl. R3 Late User (r3-01) |
| R2-2 | fixed | bulk onto unassigned UMOD: GET shows due_date 2026-12-15, curator Alice, priority high |
| R2-3 | fixed | fresh WT1 KGDB draft: score panel "No Known Disease Relationship 0.00 / 18 points" with breakdown on first render (r3-06) |
| R2-4 | fixed | Approve dialog reads "Checked against KGDB Mendelian Curation" (r3-08) |
| R2-5 | fixed | corrector (r3-sadmin) sees "You corrected the disease entity, so another reviewer must approve it (4-eyes)" (r3-07); Bob sees "Needs 2 approvals; yours is one of them" before approving; API corrected_disease true only for r3-sadmin |
| R2-6 | fixed | curation form, focus on body, clean and dirty: Escape opens nothing, text kept; Escape inside menus closes the menu only |
| R2-7 | mostly fixed | Evidence changes show "Compound heterozygous", "Loss of function", "Missense", "CNV: whole-gene or exon deletion"; read-only tables print "—" (18 cells, 0 "none"); residual: nested select "MANE status" in Evidence changes still shows raw "select" (label "MANE Select", shown correctly under Evidence details) (r3-09) |
| R2-8 | fixed | existing draft edited to a duplicate entity, Save draft: only the "already have an open precuration" alert, no "Form Validation Errors" box (r3-05) |
| Escape in dialog | fixed | Escape closes "Discard this draft?" (draft stays, MOI kept, API status draft), "Leave without saving?" (stays on form, text kept) and the Approve dialog |

## New bugs

| id | sev | steps | expected | actual |
|---|---|---|---|---|
| R3-1 | low | New precuration, open Disease entity tab without touching anything | neutral field | MONDO picker red with "MONDO disease is required" (its own rule, not DynamicForm's) (r3-03) |
| R3-2 | low | Curation in review with diagnostics.recommended_transcript.mane_status = select, open detail | "MANE Select" | Evidence changes card shows raw "select"; nested-object selects are not mapped to option labels (r3-09) |

Console: only the expected 409 on the duplicate-entity save. No 5xx.
Not checked: second approval completing the WT1 curation; phone width.
