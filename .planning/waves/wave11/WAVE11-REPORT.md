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
| Release v0.13.0 | this PR (release/v0.13.0) |
| UI monkey findings and UX polish (fix/w11-ui-polish) | #608 |
| API/MCP monkey findings, polish queue, migration 086 (fix/w11-polish) | #609 |

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
  into its own function; audit-after-commit queued for polish.
- #605: blank curator call counts as unclassified; saved view written by upsert; drop indicator
  for drag reorder.
- #606: the MCP hint missed `segregation_assessment`; the field-id explanation was kept instead of
  the notes.
- #608: removing a source chip hid the next one.
- #609: scope-admin edits could approve their own edits (curation and precuration; fixed by
  `draft_edit` joining the correctors); 086 took inactive and foreign pairs.

## Monkey results

Round 1:

| Run | Critical | High | Medium | Low |
| --- | --- | --- | --- | --- |
| API/MCP | 0 | 0 | 2 | 9 |
| UI | 0 | 3 | 6 | 14 |

UX scores (out of 10): KGDB journey 5, builders 5, permissions 5, mobile 6, version move 7,
segregation 7, catalogue 8. Fixed in #608 (UI) and #609 (API/MCP).

TODO(owner): re-check results.

## KGDB readiness

TODO(owner): KGDB readiness.

## Remaining follow-ups

TODO(owner)
