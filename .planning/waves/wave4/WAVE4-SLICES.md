# Wave 4 — methodology epic (#264) remaining slices

Base: origin/master after #407 (042) and #410 (043, TRUNCATE guard). New migrations start at 044, numbered in
planned merge order (renumber on rebase if order changes). Owner decisions: #269 shrunk (no language; JSON/YAML +
SchemaValidator + validate endpoint + cheap static checks); #271 shrunk (derived_from_version_id pointer + derive).

## Shared contracts (fixed so parallel slices agree)

- **Pinned definition read:** `db.get(MethodologyVersion, row.methodology_version_id).snapshot`. No helper module.
  For a not-yet-existing row (create), latest version of the schema (`ORDER BY version DESC LIMIT 1`), which is
  what the 042 pin trigger will pick.
- **Runtime reads the snapshot; only the admin editor reads live `curation_schemas`** (the working copy;
  `POST .../versions` publishes it).
- **Point model** (W4E): `scoring_configuration.point_model`; absent -> template file for
  `scoring_configuration.engine` (`backend/app/scoring/templates/clingen_sop_v11.json`). Existing v1 snapshots keep
  scoring identically, no data migration.
- **Workflow** (W4W): existing vocabulary `workflow_states.<stage>.allowed_transitions: [stage...]` plus
  `workflow_states.review.reviewers_required: int (1-5, default 1)`. Snapshot without valid transitions ->
  default table in code (today's `valid_transitions`). Not-author (D1) is hard-wired, never configurable.
- **Version tests** (W4T): `scoring_configuration.tests: [{name, evidence_data, expect: {total?, class?}}]`, inside
  an existing snapshot key, so `SNAPSHOT_KEYS`/`methodology_snapshot()` stay unchanged.
- **`frontend/src/types/api.generated.ts`** is never hand-merged. Slices that change OpenAPI merge serially; the
  later one rebases and reruns `make api-types`. Order: Wave A W4C -> W4V; Wave B W4T -> W4G; Wave C W4S.
- Tests use the real seeded shapes (`014/016/020_*.sql`); new fixtures in the slice's own test files, not
  `conftest.py`.

## Wave A (6 parallel, BASE origin/master after 043)

### W4C — pinned versions readable + derive. Refs #265, Closes #271 (shrunk)
Goal: any authenticated user can read a version (forms render pinned versions). Derive copies a version into a new
inactive schema whose v1 records `derived_from_version_id`. Frontend "Duplicate" becomes Derive.
AC:
- `GET /schemas/methodology-versions/{id}` returns the snapshot to any active user (404 if missing);
  `GET .../curation-schemas/{id}/versions` readable by active users. Publish stays admin-only.
- `POST .../curation-schemas/{id}/versions/{vid}/derive {name, version}` (app admin) creates an inactive schema
  from the snapshot; its v1 has `derived_from_version_id = vid`, `created_by = caller`.
- Migration 044: `publish_initial_methodology_version()` reads
  `NULLIF(current_setting('app.derived_from_version_id', true), '')::uuid`; derive sets it with
  `set_config(..., true)`. Idempotent, self-recording.
- Postgres tests: derived v1 carries the pointer; non-admin derive refused by RLS; pointer immutable; the setting
  does not leak into a later insert in a new transaction.
- API test: PUT on a schema leaves the pinned version snapshot unchanged (#265 "409" criterion; no route edits a
  version).
- Frontend: `duplicateSchema` calls derive (store test).
Owns: `backend/app/api/v1/endpoints/schemas.py`, `backend/app/crud/schema_repository.py`,
`backend/app/schemas/schema_repository.py`, `backend/app/models/methodology.py`, `database/sql/044_*.sql`,
`backend/tests/api/test_methodology_versions_api.py`, `backend/tests/postgres/test_methodology_versions.py`,
`frontend/src/api/schemas.ts`, `frontend/src/stores/schemas.ts` (+ `__tests__`), `views/SchemaManagement.vue`,
`api.generated.ts` (first in Wave A). Migration 044. Size M.
Cut: `sha`, `reason`, `tracks_upstream`, upstream diff/pull, separate `methodologies` table.

### W4E — one scoring interpreter driven by the point model. Refs #266
Goal: backend interpreter for item points, category/section caps, `combine: max`, ordered bands with `requires`,
asserted-class override, and a trace. Replaces ClinGen constants and duplicate backend calculators. Save stores
`computed_scores` (+ `trace`) from the row's pinned version.
AC:
- Golden parity: all existing ClinGen tests (`test_clingen_*`, `test_scoring_engines`,
  `test_curation_score_persistence`) pass through the interpreter with the ClinGen template.
- Boundary tests per band (Limited 1-6, Moderate 7-11, Strong 12-18, Definitive needs `replicated`) and per cap.
- A test schema whose `point_model` adds a new category scores it with no code change.
- `_computed`, `calculate_score`, `enforce_clingen_point_ranges` read the pinned snapshot (latest on create);
  `crud/gene_catalogue.py` reads the stored result only.
- `ClinGenEngine` constants and duplicate paths deleted; ClinGen-only per-item rules (LOD table, legacy evidence
  shapes) stay as a small item adapter selected by engine name.
Owns: `backend/app/scoring/**`, `backend/app/crud/curation.py`, `backend/app/crud/gene_catalogue.py`,
`backend/tests/unit/test_clingen_*.py`, `test_scoring_engines.py`, `test_curation_score_persistence.py`, new
`backend/tests/unit/test_point_model*.py`. No migration, no OpenAPI change. Size L.
Cut: shared caps across sections (unless parity needs them), qualitative/GenCC engines stay, version sha,
normalising the 4 legacy shapes (waits for production census).

### W4W — workflow transitions and reviewer gate from the pinned version. Refs #268
Goal: allowed transitions and `reviewers_required` come from the pinned snapshot with fallback; the competing
`manage_workflow_transitions` trigger is dropped; precuration submit check reads pinned `validation_rules`.
AC:
- Seeded flow unchanged incl. precuration -> review (regression tests green).
- `reviewers_required: 2` does not activate after 1 approval, does after 2; the author never counts (D1, admins
  included).
- A snapshot that forbids an edge -> 4xx, no state change.
- Migration 045 drops the trigger + function; Postgres test drives submit/approve/reject as app_user and asserts
  `stage`, `status`, `submitted_at` exactly as Python set them.
- A failed notification rolls back the transition (extend `test_workflow_atomicity`).
Owns: `backend/app/crud/workflow_engine.py`, `crud/review_round.py`, `crud/activation.py`, `crud/precuration.py`,
`crud/precuration_required.py`, `api/v1/endpoints/workflow.py`, `schemas/workflow_engine.py`,
`database/sql/045_*.sql`, `backend/tests/unit/scope/test_workflow_*.py`, `backend/tests/api/scopes/test_workflow_*.py`,
`test_precuration_workflow_regressions.py`, new `backend/tests/postgres/test_workflow_config.py`.
Migration 045. Size L.
Cut (sign-off): expert-panel stage, `assign`/`recurate after` effects, `when expr` language, configurable not-author
gate, stage renaming.

### W4V — one schema validator + cheap static checks. Refs #269 (shrunk), Closes #408
Goal: `crud/schema_validators.py` delegates to `core/schema_validator.py` (one vocabulary);
`_apply_validation_rules` accepts seeded list shapes; static checks; `validate-evidence` validates against a given
`methodology_version_id` (default latest).
AC:
- #408 repro on the seeded precuration schema: no "Error applying rule" warning; `custom_validators` pattern applied.
- Static checks return diagnostics with a JSON path: transition targets are known stages; `reviewers_required`
  1-5; `point_model` categories have numeric caps, bands ordered; `required_fields`/`custom_validators` name
  existing fields; evidence_table columns have a type.
- `test_seeded_schemas_valid` (Postgres) green; validator's `_calculate_clingen_scores` fallback deleted.
Owns: `backend/app/core/schema_validator.py`, `core/schema_rules.py`, `core/schema_validation_result.py`,
`crud/schema_validators.py`, `api/v1/endpoints/schema_validation.py`, `schemas/validation.py`,
`backend/tests/unit/test_schema_validator*.py`, `test_schema_validators*.py`,
`backend/tests/api/test_schema_validation_api.py`, `frontend/src/api/validation.ts`, `stores/validation.ts`
(+ tests), `api.generated.ts` (second in Wave A, after W4C). No migration. Size M.
Cut: language, parser, compiler, formatter, CodeMirror, `/format`, `/compile`, positions beyond JSON path.

### W4F — form interpreter primitives in the generic renderer. Refs #267
Goal: `componentRegistry.ts` maps type -> editor, compact cell, empty value; adds `evidence_table` field whose
columns are fields; steps; `visible_when`/`required_when` (equals/in only). DynamicForm renders from raw
`field_definitions` passed in.
AC: Vitest: a config-only new field/table renders; evidence cells labelled, visible focus, commit on blur (no store
write per keystroke); conditions hide/require fields; precuration renders from seeded config.
Owns: `frontend/src/components/dynamic/**`. No migration, no backend change. Size L.
Cut: computed fields, expression language, form builder UI.

### W4X — re-curation prefill fix. Closes #409
Goal: prefill copies only `evidence_data` (no top-level disease fields) and carries the source `precuration_id`
into the create payload.
AC: Vitest on `loadPrefill` and the create payload; API test: a curation created with `precuration_id` returns the
disease in header data; no duplicate entries in the change list.
Owns: `frontend/src/components/forms/SchemaDrivenCurationForm.vue` (+ spec),
`frontend/src/views/curation/CurationFormView.vue`. Size S. Review diff UI stays in #399.

## Wave B (after Wave A merges)

### W4G — ClinGen and precuration forms from pinned config; delete `components/clingen/**`. Closes #267, #265
Goal: forms fetch `GET /schemas/methodology-versions/{record.methodology_version_id}` (latest for new records) and
render through W4F. Migration 046 publishes ClinGen v2 with `field_definitions` corrected to the 17 column arrays.
Delete `components/clingen/**` and the frontend `use_dynamic_form` switch. Live score = debounced backend preview.
AC (monkey round 2 additions): 046 also (a) corrects the v1 field definitions so validate-evidence accepts real ClinGen data (`genetic_evidence` is an object, not an array; monkey bug 5) and enforces item ranges such as `proband_counted_points`; (b) embeds the CORRECTED ClinGen point_model in every ClinGen v1 snapshot, with Models + Rescue as one category capped at 4 per SOP v11 (owner decision), fixing the template file the same way; (c) recomputes stored computed_scores for pinned ClinGen curations (owner-run, logged) and the PR lists which curations change class. Forms pass the row's `methodology_version_id` to validate-evidence (render and validate from the same pinned snapshot; review of #413); port the PMID lookup + unknown-PMID save block, default points on new rows, ScoreSummary and LumpingSplitting sections from `components/clingen/**` before deleting it (W4F follow-ups); a curation pinned to v1 renders v1, a new one v2; the 4 seeded tables match today's columns (snapshot test
written before deletion); 046 idempotent and publishes exactly one version (Postgres); bundle shrinks, allowlist
updated.
Owns: `frontend/src/components/clingen/**` (delete), `components/forms/**`, `views/curation/CurationFormView.vue`,
`database/sql/046_*.sql`, `api.generated.ts` (second in Wave B). Migration 046. Deps: W4C, W4F, W4X. Size L.
Open decision: v1 snapshots carry drifted ClinGen columns (see owner decision below).

### W4T — version tests gate publish; trace and upgrade preview. Closes #270, #266 (backend), #269
Goal: publish runs the W4V validator and the version's `tests`, refuses with 422 + failures.
`GET /curations/{id}/score` returns `trace`. `GET .../curation-schemas/{id}/versions/{vid}/impact` re-scores
curations pinned to older versions with `vid` and lists total/class changes (read-only).
AC: a definition that strips required workflow states (e.g. `workflow_states` = only `{review: {reviewers_required: 9}}`) or has an out-of-range `reviewers_required` is refused (monkey bug 6); failing test or invalid definition -> publish refused, no row inserted (Postgres); trace sums equal total;
impact list correct for a 3-curation fixture and RLS-limited to visible curations.
Owns: `endpoints/schemas.py`, `crud/schema_repository.py`, `schemas/schema_repository.py`, `endpoints/curations.py`
(score route only), `schemas/curation.py` (`CurationScoreResponse`), their tests, `api.generated.ts` (first in
Wave B). No migration. Deps: W4C, W4E, W4V. Size M.
Cut: upgrade apply job (would re-pin), separate `/explain`, `/format`, `/test` endpoints.

## Wave C

### W4S — frontend reads stored scores and shows the trace. Closes #266, Refs #264
Goal: delete/replace `curationScores.ts`, `useSchemaScoring.ts`, `useScoring.ts`, `ScorePreview` with stored
`computed_scores` and backend preview; trace shown in `CurationScoreBreakdown` (detail and review).
Owns: `frontend/src/views/curation/curationScores.ts`, `useCurationClassification.ts`, `CurationDetailView.vue`,
`composables/useSchemaScoring.ts`, `composables/useScoring.ts`, `components/curation/CurationScoreBreakdown.vue`,
`components/evidence/ScorePreview.vue`, `components/dynamic/ScoreDisplay.vue` (moved from W4F after Wave A), tests.
Deps: W4T, W4G. Size M. After merge: close epic #264.

## Out of scope
#282, editable part of #284, #216, #218, #219, #105, #86, #104, #373-#381, #386, #390-#394, #399, #403, #406.

## Owner decisions
(recorded below as they are made)
- 2026-10-21: all planner cuts accepted (no expert panel, effects, expression language; ClinGen item adapter
  stays; GenCC/qualitative engines stay; no sha/reason/methodologies table; impact preview only).
- 2026-10-21: ClinGen v1 drift -> **fix v1 in place**: 046 corrects the column definitions inside the ClinGen v1
  snapshots as a one-time, owner-run, logged migration step (immutability trigger disabled only inside that
  migration). Pins never move; scores unchanged (same evidence_data paths). W4G no longer publishes a v2 for this.

## Follow-ups collected in Wave A (file as issues at wave end unless absorbed)
- Catalogue disease filter/list read only top-level evidence_data.disease_name (gene_catalogue.py:163,274,387-393); first curations never have it (#411 review).
- 003_schema_views.sql:318-319 reads computed_scores.genetic_evidence_score, never written (#416 review).
- Derive toast should say "Derived from vN (unpublished edits not included)" (SchemaManagement.vue:294); SchemaEditor.vue "Duplicate schema" label -> Derive (#412).
- Concurrent derive/create with same name passes the 400 check (no unique constraint) (#412).
- Backend ignores required_when (frontend enforces); frontend nested children ignore conditions (backend applies); array-index paths and null-vs-missing differ between backend and frontend condition evaluation (#414 review).
- recompute_scores skips rows with unknown evidence keys (custom categories) (#416).
- Precuration store fetch is paged: approved precuration past page 1 is missed for re-curation link (falls back safely) (#411).
- EvidenceTableField addRow focus lookup: CSS.escape column title (#415).
- -> W4G AC (already added): validate-evidence with pinned methodology_version_id; port PMID lookup/unknown-PMID block, default points, ScoreSummary, LumpingSplitting.
- 2026-10-21 (monkey round 2): Models + Rescue share one category capped at 4 (SOP v11) -> **fix + recompute**: corrected point_model embedded in ClinGen v1 snapshots in 046 (same in-place exception), template file fixed, stored scores recomputed, affected curations listed.
- Approve stays visible to a reviewer who already approved this round when reviewers_required > 1: return can_review=false / approvals_remaining from endpoints/curations.py and hide the button in CurationDetailView.vue (#418).
- Curator editing workspace scores client-side with fixed SOP caps (ClinGenCurationForm.vue ScorePanel, ScorePreview/useScoring.ts) -> W4G backend preview (#417 review).
- "Unknown field type: external_reference" warning on precuration Mondo ID (monkey round 2).
- AGENTS.md: reword to "A required boolean never blocks (unset counts as false); a required field whose show_when/visible_when is false is not required." (#418 review)
- 2026-10-21: W4G split into W4D (backend: 046 in-place v1 correction, corrected point_model incl. Models+Rescue cap 4, template fix, recompute + class-change report) and W4G (frontend: forms from pinned config, delete components/clingen/**, backend score preview). W4G rebases on W4D for the corrected field definitions.
- 2026-10-21 (#420 review, SOP v11 PDF p.38/p.20): **fix both in 046**: (a) case-control = single-variant (0-6) + aggregate (0-6) summed, category cap 12 (genetic total still 12); (b) AR "other variant type": each variant 0-1.5, summed per proband, proband cap 3. Same in-place treatment as Models+Rescue; recompute reports class changes.
- OWNER CALL at wave end: SOP v11 p.17/p.20 score AR variants per variant: a blank biallelic "other variant type" row should default to 0.2 (2 x 0.1), AR null to 3 (2 x 1.5); app defaults per proband (0.1 / 1.5) -> under-scores (safe side). (#420 review)
- Postgres test running pg_temp.clingen_046 against a custom point model and the old template (#420 review; verified by script only).
- Scorer does not clamp single rows to their range; relies on the 422 at save (pre-existing).
- 2026-10-22 (monkey round 3): contradictory evidence -> **only by impact**: Disputed (or Refuted if that impact option exists) only when a contradictory row's Impact says so; "Note only" never changes the class. Migration 047 fixes ClinGen v1 snapshots in place (same exception as 046) and syncs the working copy's scoring_configuration/point_model + field definitions to the corrected v1 (monkey bug 5). Recompute reports class changes.
- Footer: owner confirmed "bottom of window on short pages, after content on long pages" (not always visible).
- Follow-ups (monkey round 3, minor pre-existing): case-level tables in half-width column need horizontal scroll at 1440, HGVS clipped, card titles cut at 390, table description printed twice; Save/Submit bar scrolls away on long forms; read-only detail renders evidence as input-styled fields; MONDO search returns animal diseases; invite dates in UTC vs local elsewhere.
- clingen.py PMID warning: rows with only proband_not_counted_points > 0 are worded as "scored" (they do not count); add tests for experimental rows and legacy flat lists (#422 review).
- Monkey round 4 (low): "0 pending reviews" chip cut off at 390; scope role chip ("curator") nearly invisible; "Restore unsaved changes?" offered after the server copy changed with no local edits; restoring would overwrite newer server data (likely pre-existing; check and file).
- Backend does not verify PMIDs on submit (frontend-only gate); consider a server-side check (#425/#426).
- usePmidLookup BATCH 50 can exceed the 10 s client timeout for uncached unknown PMIDs (backend checks Europe PMC one by one) -> timed-out batch blocks nothing; consider BATCH 10 (#426 review). A table that starts read-only and later becomes editable never runs the on-load check.
- Submit holds the curation row lock while waiting on Europe PMC (up to 20 s); bulk transitions run lookups per item sequentially (#427).
