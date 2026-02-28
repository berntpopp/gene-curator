---
phase: M1-security-review-workflow
plan: 04
type: execute
wave: 1
depends_on: []
files_modified:
  - backend/app/api/v1/endpoints/curations.py
  - backend/tests/api/test_curations.py
autonomous: true
gap_closure: true

must_haves:
  truths:
    - "Approve/Reject/Request Revision all work end-to-end"
    - "4-eyes principle enforced (cannot review own curation)"
  artifacts:
    - path: "backend/app/api/v1/endpoints/curations.py"
      provides: "Correct can_review logic using IN_REVIEW status"
      contains: "CurationStatus.IN_REVIEW"
    - path: "backend/tests/api/test_curations.py"
      provides: "Tests verifying can_review for IN_REVIEW curations"
      contains: "test_can_review"
  key_links:
    - from: "backend/app/api/v1/endpoints/curations.py"
      to: "CurationStatus.IN_REVIEW"
      via: "_can_user_review_curation status check"
      pattern: "curation\\.status != CurationStatus\\.IN_REVIEW"
    - from: "CurationDetailView.vue canReview computed"
      to: "backend can_review response field"
      via: "curation.value?.can_review"
      pattern: "can_review"
---

<objective>
Fix the critical blocker where `_can_user_review_curation()` always returns False for reviewable curations, and add tests to prevent regression.

Purpose: The function checks `curation.status != CurationStatus.SUBMITTED` but curations submitted for review have status `IN_REVIEW` (set by `submit_for_review()` in workflow_engine.py). This 1-line fix unblocks the entire review workflow — Approve and Request Changes buttons will render in CurationDetailView when `can_review` becomes True.

Output: Fixed status check + 3 new tests verifying can_review behavior.
</objective>

<execution_context>
@~/.claude/get-shit-done/workflows/execute-plan.md
@~/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/M1-security-review-workflow/M1-VERIFICATION.md
@backend/app/api/v1/endpoints/curations.py (lines 78-99: _can_user_review_curation function)
@backend/app/models/models.py (lines 74-81: CurationStatus enum)
@backend/tests/api/test_curations.py (existing test patterns)
@backend/tests/conftest.py (test fixtures: test_curation, test_user_curator, etc.)
</context>

<tasks>

<task type="auto">
  <name>Task 1: Fix _can_user_review_curation status check</name>
  <files>backend/app/api/v1/endpoints/curations.py</files>
  <action>
  In `backend/app/api/v1/endpoints/curations.py`, line 90, change:
  ```python
  if curation.status != CurationStatus.SUBMITTED:
  ```
  to:
  ```python
  if curation.status != CurationStatus.IN_REVIEW:
  ```

  This is the ONLY change needed. The comment on line 89 already says "Must be in review status/stage" — the code was simply using the wrong enum value.

  Do NOT change any other logic in this function. The 4-eyes check (line 86), admin bypass (line 94), and scope role check (lines 98-99) are all correct.
  </action>
  <verify>
  Run `cd /home/bernt-popp/development/gene-curator/backend && uv run python -c "from app.api.v1.endpoints.curations import _can_user_review_curation; print('Import OK')"` to confirm no syntax errors.

  Then run `cd /home/bernt-popp/development/gene-curator && make lint` to confirm linting passes.
  </verify>
  <done>Line 90 of curations.py reads `if curation.status != CurationStatus.IN_REVIEW:` and linting passes.</done>
</task>

<task type="auto">
  <name>Task 2: Add tests for _can_user_review_curation</name>
  <files>backend/tests/api/test_curations.py</files>
  <action>
  Add a new test class `TestCanReviewPermission` to `backend/tests/api/test_curations.py`. The class tests the `can_review` field in the GET /curations/{id} response.

  The existing test file already has:
  - `mock_rls_context` autouse fixture (patches set_rls_context)
  - `test_user_with_scope` fixture (user with "curator" scope role)
  - `scope_user_token` fixture (JWT for scope user)
  - conftest fixtures: `test_curation` (status=draft, created_by=test_user_curator), `test_user_admin`, `admin_token`, `test_scope`, `test_gene`, `test_workflow_pair`

  Add these tests:

  1. `test_can_review_true_for_in_review_curation` — Create a curation with `status="in_review"` created by a different user (test_user_curator). GET it as admin. Assert `can_review` is True.

  2. `test_can_review_false_for_draft_curation` — GET the default `test_curation` (status=draft) as admin. Assert `can_review` is False.

  3. `test_can_review_false_for_own_curation` — Create a curation with `status="in_review"` where `created_by` is the admin user. GET it as admin. Assert `can_review` is False (4-eyes principle).

  Use the existing Arrange-Act-Assert pattern. Import CurationNew from app.models.models (already imported at top of file). Use uuid4() for new curation IDs.

  To create an in_review curation, create a CurationNew directly in the fixture/test with `status="in_review"`, `workflow_stage="review"`. Set `created_by` to the appropriate user's ID.

  IMPORTANT: The conftest `test_curation` fixture sets `created_by=test_user_curator.id`. For tests where admin should NOT be the creator, use `test_user_curator` as creator. For the 4-eyes test, set `created_by=test_user_admin.id`.
  </action>
  <verify>
  Run `cd /home/bernt-popp/development/gene-curator/backend && uv run pytest tests/api/test_curations.py -v -k "can_review"` — all 3 new tests pass.

  Run `cd /home/bernt-popp/development/gene-curator/backend && uv run pytest tests/ -v` — all existing tests still pass (should be 101 + 3 = 104).

  Run `cd /home/bernt-popp/development/gene-curator && make lint` — no lint errors.
  </verify>
  <done>Three tests for can_review pass: True for in_review curations by others, False for draft curations, False for own curations (4-eyes). Total backend tests: 104 passing.</done>
</task>

</tasks>

<verification>
1. `cd /home/bernt-popp/development/gene-curator/backend && uv run pytest tests/ -v` — all tests pass (104 total)
2. `make lint` — no lint errors
3. Grep confirms the fix: `grep "CurationStatus.IN_REVIEW" backend/app/api/v1/endpoints/curations.py` shows the corrected line
4. Grep confirms no regression: `grep "CurationStatus.SUBMITTED" backend/app/api/v1/endpoints/curations.py` returns NO matches in `_can_user_review_curation`
</verification>

<success_criteria>
- _can_user_review_curation returns True for IN_REVIEW curations created by other users
- _can_user_review_curation returns False for own curations (4-eyes principle preserved)
- _can_user_review_curation returns False for non-IN_REVIEW curations
- 3 new tests pass, all existing 101 tests still pass
- Linting passes
</success_criteria>

<output>
After completion, create `.planning/phases/M1-security-review-workflow/M1-04-SUMMARY.md`
</output>
