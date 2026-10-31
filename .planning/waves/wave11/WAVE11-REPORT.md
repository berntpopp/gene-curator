# Wave 11 report

## Owner decisions (2026-10-31)

Step 0 is answered; do not ask again.

- Release: **v0.13.0** (not v1.0.0).
- #284: allowed pairs plus the full capability matrix as data, `owner_scope_id` on methodologies, versions and
  workflows, every write endpoint via `require(...)`, RLS matching the matrix (W11E).
- #282: canvas dropped; #282 closes after the table builders (W11D).
- #447: build SOP v11 family/method-aware segregation; a clinical spec agent reads the PDF first (W11F).
- Already decided before the wave: L6 done (#592); allowed pairs yes; #105 = adopted marker + bulk adopt, no fetch;
  #591 and #593 as their issues say; per-row import diff yes.
- Orchestrator call: #596 (generated example export page, opened after the prompt) goes to W11C with the export work.
- Owner (mid-wave): fix every finding end to end in this wave, open no new issues. Add a configurable synopsis per
  curated entity (like sysndd): a schema key names one text field as the synopsis; export `synopsis` and show it on the
  public gene page and curation detail with the same visibility as evidence; new ClinGen/KGDB bundles use
  `evidence_summary` (W11C).

## Checkpoints

- Batch 1 (master 6b5fb7e9, after #598-#602): make ci green (Vitest 2955 passed, backend and Postgres lanes green).
- Batch 2 (master 78b97b98, after #603-#606): make ci green.

## Polish-PR queue (fix in the post-monkey polish PR)

- MCP instructions: restore the explicit error-code list (unauthorized, rate_limited, upstream_unavailable, internal,
  response_too_large) and the get_my_review_assignments queue line trimmed in #601.
- Provenance export: add a bare-date test (contribution("curator", a, "2026-10-02") -> ...T00:00:00Z) and normalize
  offset datetimes to Z so docs/EXPORT.md "UTC with Z" holds for every input (#602 review nit).
- Curation classification hybrid (#605): SQL trim strips spaces only, Python strip() also tabs/newlines; use
  regexp/btrim with whitespace class or strip only spaces in Python so both agree for "\t" (not reachable via API).
- Permissions (#604): capabilities.audit() commits after the change is already committed (a failed audit insert
  returns 500 for a saved change); write the audit row in the same transaction. Drop the empty TYPE_CHECKING block in
  services/scope_permissions.py:34-35; fix the deps.py:325 docstring period.

## Issues

| Issue | PR |
| --- | --- |
| L6 4-eyes status codes (Wave 10 follow-up) | #592 |
| Save 409 message (follow-up to #592) | #594 |
| #105 ClinGen adoption | #598 |
| #282 table builders, draft diagnostics, schema lock | #599 |
| #591 move curations to a newer methodology version | #600 |
| Wave 10 follow-ups (B20, B21, R3-1, R3-2, due_date, invitations, 085, ...) | #601 |
| #593 provenance, synopsis; #596 example export page | #602 |
| KGDB susceptibility tiering (kidney-genetics-db#473) | #603 |
| #284 capability matrix, scope-owned configuration, allowed pairs | #604 |
| #276 catalogue column order, With results, saved view | #605 |
| #447 SOP v11 segregation | #606 |
| UI monkey findings and UX polish (fix/w11-ui-polish) | #608 |
| API/MCP monkey findings, polish queue, migration 086 (fix/w11-polish) | #609 |
| #610 KGDB lumping/splitting decision could not be submitted | #616 |
| #611 select, date and length validation in evidence-table cells | #616 (part), #619 |
| #612 stale MCP instructions and tool help on the KGDB pairs | #616, #620 (auto reviewer pick skips correctors) |
| #613 adoptions exported 0 points, lost agent credit, no diagnostics | #618, #621 (edit and new round in one transaction) |
| #614 susceptibility risk allele, undetermined MOI, CI columns, association score | #619 |
| #615 KGDB bundle at prompt iteration 8, README, `mondo_id` normalised | #619 |
| Re-check findings and remaining UX nits (fix/w11-final) | #617 |
| Release v0.13.0 | #607 (release/v0.13.0) |

## Migrations

| Migration | PR | What |
| --- | --- | --- |
| 078_methodology_version_move | #600 | pin may move forward to a later version of the same schema, platform admin only |
| 079_clingen_adoption | #598 | `curations.clingen_adoption` JSONB marker |
| 080_audit_log_agent | #602 | `audit_log.change_metadata.agent` + `actedOnBehalfOf`; `curations.row_provenance` |
| 081_curation_schema_lock_version | #599 | `curation_schemas.lock_version` |
| 082_capability_matrix | #604 | `role_capabilities`, `owner_scope_id`, `scope_workflow_pairs`, RLS helpers on the matrix |
| 083 | - | unused (#606 needed none) |
| 084_user_view_preferences | #605 | per-user saved views, own-row RLS, no DELETE |
| 085_methodology_versions_public_read | #601 | anyone reads methodology versions (anonymous export `methodology.version`) |
| 086 (allowed pairs backfill) | #609 | each scope's allowed pairs from its existing work: default, curations' pairs, active pairs of its precurations' schemas |
| 087 | - | unused (#618 needed none) |
| 088_susceptibility_allele_key | #619 | `risk_allele` joins the susceptibility entity key; UNDETERMINED / MULTIFACTORIAL MOI keys; stops on open precurations it would merge |
| 089_review_comments_inactive_scope_read | #617 | members read an inactive scope's review comments (SELECT only) |

## Reviews

Must-fix findings caught in review, from the fix commits on each PR (and the coordinator's
review notes; findings left for later were fixed in #608 and #609).

- #592, #594: #594 itself is the review follow-up of #592 (every 409 read as a stale save).
- #598: no user ids in the export; a concurrent adopt (race) is a 409.
- #599: a PUT without `lock_version` overwrote; the draft stuck after a 409.
- #600: frontend diff-cover 89% raised to 98% with tests.
- #601: in-scope gene flags resolved in one query; typed public summary; boolean length limits ignored.
- #602: source ids warn at save and MCP write; one VA-Spec contribution builder; no email
  fallback in names; contribution dates in the export's Z format; assessors only for visible
  approving reviews; latest software write picked by datetime.
- #603: every susceptibility rule guarded by an embedded test (13/13 mutations caught);
  re-import writes a changed description and plans it as `update`; `band_margin` respects
  `section_min`.
- #604: frontend diff-cover 81% raised to 94%; scope-default step of `import_bundle` extracted
  into its own function; audit-after-commit queued for polish (fixed in #609).
- #605: blank curator call counts as unclassified; saved view written by upsert; drop indicator
  for drag reorder.
- #606: the MCP hint missed `segregation_assessment`; the field-id explanation was kept instead of
  the notes.
- #608: removing a source chip hid the next one.
- #609: scope-admin edits could approve their own edits (curation and precuration; fixed by
  `draft_edit` joining the correctors); 086 took inactive and foreign pairs.

- #616: none blocking once #611 became Refs (its bundle part moved to #619).
- #617: a review comment could be edited in a frozen (inactive) scope.
- #618: a version move re-scored adoptions; old adoption rows exported 0 points.
- #619: double halving of unknown-phase compound hets; functional sub-caps not enforced by the
  engine; 088 could merge duplicates (now stops listing ids); the step check blocked ClinGen
  LODs (now only scoring points keep their step).

## Monkey results

Round 1:

| Run | Critical | High | Medium | Low |
| --- | --- | --- | --- | --- |
| API/MCP | 0 | 0 | 2 | 9 |
| UI | 0 | 3 | 6 | 14 |

UX scores (out of 10): KGDB journey 5, builders 5, permissions 5, mobile 6, version move 7,
segregation 7, catalogue 8. Fixed in #608 (UI) and #609 (API/MCP).

Round 2 re-check at d1267b62: 32 of 34 findings fixed, 2 partial (MUI-15: the `PMID:` prefix
is stored; MUI-18: raw keys left in two places), none still broken. Every round-1 untested item
passes: #594 (an author in an inactive scope sees the read-only reason), the anonymous gene
page synopsis, plain objects, viewer and reviewer buttons, a scope admin who edited cannot
approve, the row side sheet, source chip kind detection, and the 390 px sticky Save bar.
Two new lows: an inactive-scope member gets 403 on review-comments, audit-trail and diff; the
source chip accepts junk as `Database`.

| UX area | R1 | R2 |
| --- | --- | --- |
| KGDB journey | 5 | 7 |
| Builders | 5 | 8 |
| Permissions | 5 | 8 |
| Mobile | 6 | 7 |
| Version move | 7 | 8 |
| Segregation | 7 | 8 |
| Catalogue | 8 | 8 |

The partials, the two new lows and the remaining UX nits go into the final fix PR
(fix/w11-final, #617).

## KGDB readiness

Checked end to end on a fresh stack:

- Bundle import: dry run, write, idempotent re-import, a new version on change.
- Intake with curator and due date.
- Bulk ClinGen adoption from GeneFoundry records, confirmed under 4-eyes, with the `adoption`
  export block.
- Mendelian and Susceptibility curations with source cells (ClinVar, PMID, DOI) and the
  approved susceptibility tiering.
- An MCP-written curation with an agent block, shown in History and the export.
- Approval by two reviewers.
- Version move with an active curation.
- Export with `synopsis`, `contributions` and sources, validating against the JSON Schema
  snapshot and `docs/examples/export-page.json`.

KGDB QA round (kidney-genetics-db#448): KGDB's own QA of this stack filed #610–#615
(lumping/splitting submit, cell validators, MCP help, adoption export and diagnostics,
susceptibility risk allele, bundle at prompt iteration 8). All six are closed by #616, #618 and
#619, with follow-ups #620 and #621.

## Remaining follow-ups

None after fix/w11-final (#617) and #620.

Orchestration notes:

- `merge.sh` did not delete remote branches; they were deleted through the API.
- Subagents cannot write report files; findings were relayed in their replies.
- GitHub shows the SSH-signed tags as unverified until the key is added as a signing key.
