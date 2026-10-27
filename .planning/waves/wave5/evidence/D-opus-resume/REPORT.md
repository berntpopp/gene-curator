# D resumed independent review

PR445: actual Claude Code claude-opus-5-5, is_error=false.
Session: `c01a6d5e-4428-4680-9912-f09d92c1045e`. Read-only review; no new tests were run by reviewer.

I'm done reviewing. **Verdict: FIX.** One change needs work before this ships. Everything else you asked me to check holds up.

**Head reviewed:** `4e7cf15519d51d2c8360895141756df9e88cb2d4`

**What this change does:** The backend and frontend now share one set of rules for when a field is shown and when it is required, and both run the same test cases. Every route into review now checks required fields against the item's pinned methodology version. Those routes are submit, direct transition, bulk and precuration complete. Editable forms now fill in the default values a schema declares, even when the user never touches the field.

## Must fix

1. **Some curations can never be submitted, and the user cannot fix it**
   - **Where:** `backend/app/services/review_guards.py` lines 586–600 (`check_review_content`) and `backend/app/crud/precuration_required.py` `_fields`.
   - **What happens:** The seeded SOP v11 curation schema marks `entity_definition.disease_name`, `mondo_id` and `mode_of_inheritance` as required and read-only (`020_complete_sop11_schema.sql` lines 30–54). Before this change, curations were never checked against field definitions. Now every route into review refuses a curation whose own evidence has no `entity_definition`.
   - **Trigger:** A curation that was not filled in by the approval step. Examples:
     - one made through the form's create path (`useCurationSubmission.ts` lines 75–81 send only the form's evidence);
     - a re-curation copied from an active curation that had no `entity_definition`;
     - a workflow pair whose mapping uses dotted source keys (Standard_ClinGen in `018`), which `_prefill_curation_data` cannot look up;
     - every existing curation in a deployed database that lacks it.
     
     The normal path still works: the seeded pair maps flat precuration fields at approval.
   - **User impact:** The form check says the curation is valid. `_validate_fields` skips a missing parent object, so Submit stays enabled. The server then returns 400 listing three read-only fields, and the user has no way to fill them. Four Postgres fixtures had to add `entity_definition` to keep passing, which shows the product path hits this.
   - **Minimal fix:** In `check_review_content`, for a curation with a `precuration_id`, check required fields against the evidence with `entity_definition` filled in from the linked precuration using the existing `disease_fields` helper. The curation's own values win, which is the same fallback `get_disease_fields` already uses for display. The alternative is a backfill migration plus prefill on create.
   - **Required test:** A Postgres test as `app_user`, run through submit, direct and bulk:
     - a curation created via `POST /curations` with a `precuration_id`, no `entity_definition`, and a precuration that has the disease: it enters review;
     - the same curation when the precuration has no disease: it is refused and the row does not change.

## Should fix

2. **No `app_user` test for re-review from ACTIVE**
   - **Where:** `backend/tests/unit/scope/test_review_content.py` (`test_a_re_review_of_an_active_curation_requires_complete_content`).
   - **Gap:** ACTIVE→REVIEW is only tested on SQLite, and only through `validate_transition`. The code itself has no ACTIVE exception: the check runs for any target of REVIEW in `_validate_stage_requirements`, before anything is written.
   - **Fix:** Add one case to the Postgres route matrix: an admin moves an ACTIVE curation with missing content to review. Assert that it is refused and that `_item_state` does not change.

## Checked and fine

- **Condition rules:**
  - `false` is not `0`, `true` is not `1`, and `"1"` is not `1`.
  - A missing value is not the same as `null`.
  - `visible_when` takes precedence over `show_when`, and a `null` `visible_when` falls back to `show_when`.
  - A malformed condition holds, so the field stays required.
  - Fields under a hidden parent are hidden, including array rows.
  - `required_when` is applied, and a false condition means the field is not required.
  - A required boolean set to `false` counts as answered; a missing one does not.
  - Python and TypeScript match on these. The shared case table runs on both sides.
- **Pinned version:** the pin wins over later edits to the working schema, and a pin that cannot be read fails closed.
- **No mutation on refusal:** curation submit validates before it claims the lock version. Precuration submit rolls back the claim. The Postgres tests assert status, stage, lock version, evidence and `is_draft` are unchanged after a refusal.
- **D1:** no new admin bypass and no RLS changes. The bulk test runs as a platform admin and is still content-checked.
- **Defaults:**
  - Explicit `false`, `0`, `""` and `null` are kept, and the input object is not mutated.
  - Arrays, evidence tables and read-only fields are skipped. Every editable form passes `definition`, so read-only fields are always skipped.
  - Data or a schema that arrives late is still picked up.
  - Switching between read-only and editable resets cleanly.
  - The seeded `lumping_splitting_applicable` declares `default: false`.

## Not blocking

- Existing precuration drafts that never stored `lumping_splitting_applicable` are now refused by bulk, direct and complete until someone opens and saves them. The refusal message is clear. A one-line backfill would avoid this.
- Defaults are emitted before the workspace records its "saved" starting point. An old draft that is missing a default shows as "saved" until the user saves it. Submit from the form saves first, so this does no harm.
- `DynamicNestedField` does not apply a `visible_when` placed on the array's `items` config itself; the backend does. No seeded schema uses this.

I did not run any gates or tests, and I did not open `_validate_object_field`. I'm basing "the form check says valid" on `_validate_fields` skipping a missing parent object.

Raw JSON is retained locally and ignored. Findings require reproduction, scoped fixes, actual Opus delta review, and relevant browser recheck before merge.
