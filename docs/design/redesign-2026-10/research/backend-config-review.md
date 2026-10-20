# Backend + database configuration review (gap to config-driven "methodology" DSL)

Date: 2026-10-21. Read-only review of `master` @ 02608ac plus the running dev DB (port 5454).
Scope: database tables/JSON/triggers, backend schema/validation/workflow/scoring code, open issues.
Frontend is out of scope except where it duplicates backend logic.

## TL;DR

- The "config" exists in five JSONB columns on `curation_schemas`, but **almost none of it is read at
  runtime**. Workflow is hard-coded Python (`crud/workflow_engine.py`), scoring is hard-coded Python
  (`scoring/clingen.py` constants), and the only scoring key read is `scoring_configuration.engine`,
  and only by the stats view and `SchemaValidator`, which fails to match it.
- There are **five independent ClinGen score calculators** (engine, `crud/curation.py`,
  `crud/gene_catalogue.py`, `core/schema_validator.py`, plus two in the frontend). They disagree, and the
  DB `verdicts` block disagrees with all of them (#157).
- **Persisted scores are wiped**: trigger `calculate_schema_scores` overwrites `computed_scores` /
  `computed_verdict` on every non-draft write (#234). In the dev DB, 0 of 8 curations have a verdict.
- **Three validators with three type vocabularies**; none accepts the seeded schemas (`string`, `enum`,
  `integer`, no `label`) (#207, #227).
- **No version pinning**: curations point to `workflow_pair_id`, the pair points to a schema row, and
  `PUT /schemas/curation-schemas/{id}` mutates that row in place even when it is in use.
- `evidence_data` has **4 different shapes** across the 8 dev curations. Migration must normalise.
- Recommended path: new `methodologies` + `methodology_versions` (immutable, compiled JSON + DSL source +
  hash) tables. Pin `curations/precurations.methodology_version_id`. Write one Python interpreter for
  each layer (workflow, forms/validation, scoring). Delete the trigger placeholder, the duplicate
  calculators, the three validators and the engine registry. ClinGen becomes a config plus test fixtures.

---

## 1. Database

### 1.1 Tables (live `information_schema`; DDL in `database/sql/001_schema_foundation.sql`)

| Table | Config-relevant columns | Notes |
| --- | --- | --- |
| `curation_schemas` | `name`, `version` (varchar), `schema_type` (enum precuration/curation/combined), `field_definitions` jsonb NOT NULL, `validation_rules` jsonb `{}`, `scoring_configuration` jsonb NULL, `workflow_states` jsonb NOT NULL, `ui_configuration` jsonb NOT NULL, `based_on_schema_id`, `institution`, `is_active`, `schema_hash` NOT NULL, `use_dynamic_form` | UNIQUE(name, version). **No RLS.** No scope ownership: schemas are global. |
| `workflow_pairs` | `precuration_schema_id`, `curation_schema_id`, `data_mapping` jsonb, `workflow_config` jsonb | UNIQUE(name, version). No RLS. |
| `schema_selections` | user/scope/institution → preferred pair/schemas | 0 rows; effectively unused. |
| `scopes` | `default_workflow_pair_id`, `scope_config` jsonb | `scope_config` is only echoed into API/trigger context, never interpreted. |
| `precurations` | `precuration_schema_id` NOT NULL, `status`, `workflow_stage`, `evidence_data`, `computed_scores`, `computed_fields`, `version_number`, `record_hash` | Pins the **schema row** (mutable). |
| `curations` | `workflow_pair_id` NOT NULL (**no `curation_schema_id`**), `evidence_data`, `computed_scores`, `computed_verdict` varchar, `computed_summary`, `computed_fields`, `lock_version`, `version_number`, `record_hash` | Pins the **pair**, which points at a mutable schema. |
| `active_curations` | `gene_id`, `scope_id`, `curation_id`, `replaced_curation_id`, `archived_*` | Partial UNIQUE (gene_id, scope_id) WHERE archived_at IS NULL. |
| `reviews` | `status` (pending/approved/rejected/needs_revision), `recommendation` varchar, `feedback_data`, `review_round`, `due_date` | No "required reviewers" config. |
| `evidence_items` (009) | per-item `evidence_category`, `evidence_data`, `computed_score` | 0 rows. This is a parallel store that `015_migrate_evidence_data.sql` was meant to fill. Only `endpoints/evidence.py` uses it. |

Enums (live): `curation_status` = draft, submitted, in_review, approved, rejected, active, archived;
`workflow_stage` = entry, precuration, curation, review, active; `review_status` = pending, approved,
rejected, needs_revision. **Stages are DB enums**, so a config-defined stage (e.g. `expert_panel`)
needs a schema change.

### 1.2 Seeded rows (4 schemas, 4 pairs)

| Schema | engine | field_definitions keys | workflow_states keys | ui_configuration keys |
| --- | --- | --- | --- | --- |
| ClinGen_SOP_v11 (25 KB) | `clingen_sop_v11` + `verdicts`, `parameters`, `evidence_categories` | evidence_summary, entity_definition, genetic_evidence, experimental_evidence, contradictory_evidence | states, transitions, initial_state | layout, components, quick_actions, keyboard_shortcuts |
| GenCC_Classification | `gencc_based` + `verdicts` | genetic_evidence, experimental_evidence | states, transitions | layout |
| Qualitative_Assessment | `qualitative_assessment` + `verdicts` | literature_review, clinical_assessment | states, transitions | layout |
| Standard_Precuration | (null) | entity_definition, lumping_splitting, initial_assessment | states, transitions | layout |

Pairs: ClinGen/GenCC/Qualitative "Complete_Workflow" all use **the same** Standard_Precuration schema,
plus an inactive `UXR-pair-53760`. `workflow_config` = `{"review_required": true, "require_precuration": true, "auto_populate_fields": true}`. None of these keys is read by code.

**field_definitions shape** (nested objects; leaf evidence lists are `type: array` + `item_schema`).
Scoring is **duplicated** inside the fields:

```json
"other_variant_type": {"type": "array", "ui_component": "EvidenceTable",
  "scoring": {"range": [0, 1.5], "max_per_item": 1.5, "default_points": 0.1},
  "item_schema": {"pmid": {"type": "string", "required": true, "validation": "pmid_format"},
    "score_status": {"type": "enum", "options": [{"label": "Score", "value": "score"}, {"label": "Review", "value": "review"}, {"label": "Contradicts", "value": "contradicts"}], "required": true},
    "proband_counted_points": {"type": "number", "min": 0, "max": 1.5, "step": 0.1, "required": true}, ...}}
```

Distinct `type` values used: string, enum, object, array, boolean, number, integer. Distinct keys used:
type, required, validation, scoring, description, label, options, min, max, step, default,
default_points, max_per_item, max_total_points, range, min_length, help_text, item_schema,
properties, ui_component. Not present: conditional required/visibility, computed fields, or
gene/MONDO/HPO/HGVS/PMID types (PMID is `string` + `validation: "pmid_format"`). The numeric score key
differs by item type: `proband_counted_points` for case-level, `points` for everything else.

**scoring_configuration (ClinGen) excerpt** (overlapping, unordered bands, never evaluated):

```json
"verdicts": {
  "Limited":    {"conditions": [{"score_range": [0.1, 6.99]}]},
  "Moderate":   {"conditions": [{"score_range": [7, 11.99]}]},
  "Strong":     {"conditions": [{"score_range": [12, 18]}, {"replication": true}]},
  "Definitive": {"conditions": [{"score_range": [12, 18]}, {"replication": true}, {"time_requirement": "3_or_more_years"}]},
  "Disputed":   {"conditions": [{"contradictory_evidence": true}]}, ...},
"parameters": {"max_total_score": 18, "max_genetic_score": 12, "max_experimental_score": 6},
"evidence_categories": [{"name": "experimental_evidence", "max_score": 6, "subcategories": [
  {"name": "models", "max_score": 4, ...}, {"name": "rescue", "max_score": 4, ...}]}]
```

GenCC/Qualitative use a different condition grammar: `{"field": "total_score", "operator": ">=", "value": 7}`.

**workflow_states (ClinGen)**: `{"states": [{"name": "draft", "permissions": ["curator","admin"]}, ...], "transitions": {"draft": ["submitted"], "submitted": ["in_review"], "in_review": ["approved","rejected"], ...}, "initial_state": "draft"}`. These are *status* names, while the engine
works on *stages*. Not read anywhere.

**validation_rules (ClinGen)**: `pmid_format` and `mondo_id_format` (`type: regex`, `pattern`) and
`required_evidence` (`type: custom`, `function: "validateRequiredEvidence"`). The backend applies only
rule types `condition|dependency|calculation` (`core/schema_validator.py:570-599`), so **all seeded rules are
silently skipped**. Field-level `"validation": "pmid_format"` references are never resolved.

### 1.3 Real `evidence_data` shapes (dev DB, 8 curations, 7 precurations)

| Shape | Example keys | Count |
| --- | --- | --- |
| A. SOP v11 nested (target) | `genetic_evidence.case_level.autosomal_recessive.predicted_or_proven_null[]` with `proband_counted_points`, `score_status` | 3 |
| B. Legacy root-level | `case_level`, `segregation`, `experimental` at root; items `{id, points, status, proband, variant}` | 2 |
| C. Score-only | `{"genetic_evidence_score": 8, "experimental_evidence_score": 4}` | 2 |
| D. Summary-only | `{"evidence_summary": ""}` | 1 |

Precurations are **flat** (`mondo_id`, `disease_name`, `lumping_splitting_decision`, ...), but the
precuration schema is nested (`entity_definition.mondo_id`). `data_mapping` keys are dotted
(`"entity_definition.mondo_id"`) and `_prefill_curation_data` looks them up as flat keys
(`crud/precuration.py:552-573`), so **prefill never copies anything** (#77).

Active curations' `computed_scores`: `{"engine": "clingen_sop_v11", "raw_scores": {}, "calculated_at": ..., "scope_context": {...}}`, and `computed_verdict` is NULL for all 8 rows.

### 1.4 Triggers (live)

| Table | Trigger | Effect |
| --- | --- | --- |
| curations | `trigger_calculate_schema_scores` BEFORE INSERT/UPDATE (`002_schema_triggers.sql:120-172`) | **Placeholder.** When `is_draft = false`, it replaces `computed_scores` with `{engine, calculated_at, scope_context, raw_scores:{}}` and sets `computed_verdict := NULL`, `computed_summary := NULL`. This wipes the ORM-written engine result (`crud/curation.py:553-556`) on the same UPDATE. **#234.** |
| curations | `trigger_manage_workflow_transitions` BEFORE UPDATE (`002:387-418`) | Hard-coded status→stage side effects: submitted→review (sets submitted_at/by, is_draft=false), approved→**active**, rejected→curation (is_draft=true). This is a second, conflicting state machine to `workflow_engine` (which sets IN_REVIEW, not SUBMITTED). |
| curations | `trigger_increment_lock_version`, `trigger_generate_curation_hash` (INSERT only), `trigger_auto_save_curations`, `trigger_audit_curations`, `trigger_curation_update_mark_stale` | Bookkeeping. `crud/curation.py:516` also bumps `lock_version` by hand, so it is double-incremented. |
| precurations | hash (021), auto-save, audit | No scoring trigger. |
| curation_schemas | `trigger_validate_schema` → `generate_schema_hash()` (`002:455-491`) | Checks only that 3 keys are objects; computes sha256 over the 5 JSON columns. The hash is never stored on curations. |

### 1.5 Views

`003_schema_views.sql`: `scope_statistics` counts `computed_verdict = 'Definitive'|'Strong'|...`
(Title case, `:112-115`), but the engine emits lowercase `definitive` (`scoring/clingen.py:925-956`)
and the trigger nulls it anyway, so every count is 0. `schema_usage_analytics` reads
`scoring_configuration->>'engine'` (`:223`). Other views (`workflow_complete_overview`,
`active_curations_summary`, `review_compliance_dashboard`, ...) project `computed_verdict`.

### 1.6 RLS

RLS (forced) is on curations, precurations, reviews and active_curations (`005_rls_setup.sql`), but not on
`curation_schemas` or `workflow_pairs`. The dev role `dev_user` is **superuser + BYPASSRLS**, so RLS is
never exercised in dev either (#156 covers prod).

### 1.7 Keys read by code vs ignored

| JSON | Read by | Ignored |
| --- | --- | --- |
| `field_definitions` | `SchemaValidator.generate_json_schema` / `_validate_fields` (top level only, wrong types), validator chain, frontend DynamicForm | `scoring.*` inside fields, `validation` refs, `ui_component` (frontend only) |
| `validation_rules` | `_apply_validation_rules`: only condition/dependency/calculation | all seeded rules (regex/custom) |
| `scoring_configuration` | `engine` (views; `SchemaValidator._calculate_scores` compares to `"clingen"`, never matches) | `verdicts`, `parameters`, `evidence_categories`: **no backend reader** |
| `workflow_states` | validator chain (presence of draft/submitted) | states, transitions, permissions, initial_state |
| `ui_configuration` | frontend `useFormTabs` (if #227 fixed) | backend: none |
| `workflow_pairs.workflow_config` | none | all |
| `workflow_pairs.data_mapping` | `_prefill_curation_data` (broken lookup) | |
| `scopes.scope_config` | echoed only | all |

---

## 2. Backend

### 2.1 Models and Pydantic

- `models/models.py:351` `CurationSchema`, `:448` `WorkflowPair`, `:673` `PrecurationNew`, `:778`
  `CurationNew`, `:914` `Review`, `:981` `ActiveCuration`, `:1168` `SchemaSelection`. All JSON is
  `Mapped[dict[str, Any]]`.
- `schemas/schema_repository.py:13-81`: every config block is `dict[str, Any]`. There is **no typed model of
  the config**, so nothing can be validated or round-tripped.

### 2.2 Validation: three parallel validators

| Validator | Where | Type vocabulary | Used by |
| --- | --- | --- | --- |
| `SchemaValidatorChain` | `crud/schema_validators.py:412-485` (`FieldDefinitionsValidator` `:98-207`, `VALID_FIELD_TYPES` `:102` = text, number, boolean, array, object, date, select, multiselect; **requires `label`** on each top-level field) | 8 types | `POST /schemas/curation-schemas` (create, rejects on error) and `POST /schemas/curation-schemas/{id}/validate`. Every seeded schema fails (types `string`/`enum`, no `label`) → **#207**. |
| `SchemaValidator` | `core/schema_validator.py:17-1106`: `field_validators` `:23-38`, `_validate_workflow_states` `:954-971` (expects a **list**; seeds are an object), `_calculate_scores` `:789-856` (engine names `clingen/gencc/qualitative` never match; ClinGen branch sums non-existent keys `case_level_score`...) | 13 types, no `string`/`enum` → "Unknown field type: string" (#227) | `/validation/*` endpoints (`endpoints/schema_validation.py:65-620`) |
| JSON-Schema generator | `core/schema_validator.py:140-167, 995-1102` | 15 types incl. string/enum; handles `item_schema` | `GET /validation/schema/{id}/json-schema` returns `{json_schema, field_count, validation_rules_count}` with only `properties/required`. No `ui_configuration` and no `scoring_configuration`, so DynamicForm renders nothing (#227). |

`services/validation_service.py` + `services/validators/{hgnc,pubmed,hpo}_validator.py` are external
lookups with a cache (`validation_cache`, 011). These are reusable as typed-field validators
(gene/HGNC, PMID, HPO), but they are not wired to field types.

**Evidence is never validated on save or submit**: `crud/curation.py` `create/update_with_lock/save_draft/submit_for_review`
store arbitrary dicts. The only content check is "evidence_data non-empty" (`workflow_engine.py:857-876`).

### 2.3 Workflow: hard-coded Python

`crud/workflow_engine.py`:

- Transition table `:39-60`:
  `entry→precuration`, `precuration→curation|entry`, `curation→review|precuration`,
  `review→active|curation`, `active→review`. **There is no `precuration→review`**, but
  `crud/precuration.py:306-327` submits precuration to REVIEW via this engine, so it always fails (**#229**).
- Role matrix `_get_role_requirements` `:662-709`: every edge requires curator/admin/"scope_admin",
  except `active→review`, which requires admin/scope_admin. `_check_role_authorization` `:711-758` **always
  appends `reviewer`** to scope roles, so a reviewer can do every transition, including submitting. Uses
  `user.role == "admin"` (application role).
- 4-eyes `_requires_peer_review` `:760-774`: only `review→active`, and only `created_by != user`. There is no
  N-reviewers setting, no "not author of any revision", and no expert panel.
- Content requirements `:808-841` are **display strings only**, not enforced.
- Per-stage executors `:880-996` each `db.commit()`. Then audit log, then notification (`:998-1056`) in
  separate commits. `submit_peer_review` `:375-475` commits the review, then calls `execute_transition`
  (another commit), so it is **not atomic (#237)**. `request_changes` only notifies and does **not** move the
  curation back to curation.
- Auto-activate when all reviews approve: `_check_all_reviews_complete` `:1131-1170`. With 0 reviews it
  returns True. There is no minimum reviewer count (#116).
- Precuration has its **own** transitions outside the engine: `submit` / `complete` / `approve` / `reject`
  (`crud/precuration.py:281-527`). `approve_and_create_curation` chooses the pair as "first active pair
  with this precuration schema" (`:542-550`), and all 3 pairs share the schema, so the methodology is
  arbitrary and `scopes.default_workflow_pair_id` is ignored.
- `GET/PUT /workflow/configuration/{scope_id}` (`endpoints/workflow.py:469-523`) returns **hard-coded
  defaults** (`min_reviewers=1`, ...). PUT persists nothing.
- Two state machines fight: the engine sets `status=IN_REVIEW`, while the DB trigger reacts to `submitted`,
  `approved` and `rejected`. Approve via the engine sets `ACTIVE` directly, so the trigger's `approved_at/by` is
  never set.

### 2.4 Scoring

- `scoring/base.py:24-66`: `ScoringEngine` ABC with `calculate_scores(evidence_data, schema_config, scope_context)`. `ScoringResult` has scores, total_score, verdict, verdict_rationale, evidence_breakdown, warnings and metadata (it already has the shape of a "trace").
- `scoring/registry.py:13-125`: registers `clingen_sop_v11`, `gencc_based`, `qualitative_assessment`.
  It is used only by `/schemas/scoring-engines/*` endpoints (`endpoints/schemas.py:372-436`).
- `scoring/clingen.py` (1358 lines; allow-listed). **`schema_config` is explicitly unused** (docstring
  `:103`). Everything is constants:
  - caps `:38-57` (genetic 12, experimental 6, total 18, segregation 3, case-control 6, function 2,
    functional alteration 2, models 4, **rescue 4 separately**, so there is no shared models+rescue cap);
  - thresholds `:60-68` + `_classify` `:925-956`: **definitive ≥12, strong ≥7, moderate ≥2, limited ≥0.1**,
    which contradicts the DB config (Moderate 7–11.99) and SOP v11 (Limited 1–6, Moderate 7–11, Strong 12–18,
    Definitive = Strong + replication/time). Disputed/Refuted come from *negative scores*, which cannot occur.
  - per-item defaults are hard-coded in `.get("points", 0.5)` / `.get("proband_counted_points", 1.5)` calls
    (`:307,314,698-815`). **`score_status` is ignored**: "review" and "contradicts" items are counted. PMID
    presence only produces a warning (`:1026-1031`). Explanation-above-default is not checked.
  - case-control = `max(single, aggregate)` (`:250`), segregation LOD→points `:369-390`.
  - Shape handling: nested (SOP v11) vs "legacy" flat list (`:198-199`, `_calculate_*_legacy`
    `:392-452, 850-923`). Shapes B/C/D from §1.3 score 0 silently.
- `scoring/gencc.py` (`gencc_based`, thresholds `:131-149`) and `scoring/qualitative.py` are hard-coded too.
- **Duplicates**: `crud/curation.py:44-195` (list-view score: **sums** case-control, Moderate ≥2, Title-case
  verdicts), `crud/gene_catalogue.py:26-128` (Moderate ≥9 with genetic gates),
  `core/schema_validator.py:805-836`, and the frontend `components/clingen/scoring.ts` and
  `views/curation/curationScores.ts` (#157).
- Persistence: only `GET /curations/{id}/score` (`endpoints/curations.py:485-507` →
  `crud/curation.py:528-570`) runs the engine (ClinGen hard-wired, `schema_config={}`). This is a GET with a
  write, and the trigger wipes the result if the curation is not a draft. Submit/approve never score.

### 2.5 Endpoints that expose config

| Endpoint | File | Notes |
| --- | --- | --- |
| `GET/POST/PUT/DELETE /schemas/curation-schemas[/{id}]` | `endpoints/schemas.py:36-160` | POST is open to any user (#212). PUT edits in place, with no immutability for in-use schemas (no version bump, #213). |
| `POST /schemas/curation-schemas/{id}/validate` | `:163-190` | chain validator → seeds fail (#207) |
| `GET /schemas/curation-schemas/{id}/compatible-engines` | `:193-218` | always all engines |
| `/schemas/workflow-pairs*` | `:221-370` | |
| `/schemas/scoring-engines[/{name}][/validate|/calculate]` | `:372-436` | the only path that routes by engine name |
| `/validation/validate-evidence`, `validate-schema`, `generate-json-schema`, `schema/{id}/json-schema`, `validate-field`, `supported-field-types`, `business-rules`, `test-validation` | `endpoints/schema_validation.py` | `SchemaValidator` (§2.2) |
| `/workflow/configuration/{scope_id}` | `endpoints/workflow.py:469-523` | stub |

---

## 3. Related open issues

| # | Title (short) | Relation |
| --- | --- | --- |
| 157 | Scoring rules disagree across code | 5 calculators, thresholds; solved by one interpreter + fixtures |
| 234 | Trigger wipes persisted scores | delete `calculate_schema_scores`; prerequisite for anything |
| 207 | Create/duplicate schema always fails | validator vocabulary; replaced by DSL compiler |
| 208 | Schema editor hides save/validate results | editor UX on top of compiler diagnostics |
| 209 | Inactive schemas/pairs disappear | listing of versions |
| 212 | Any user can create schemas | methodology authoring needs admin/scope-admin gate |
| 213 | Duplicate creates same-version active schema | immutable versions + draft/publish |
| 219 | Structured schema editor | visual editor round-trips the DSL/compiled JSON |
| 227 | json_schema shape; DynamicForm empty | forms layer served from compiled config |
| 229 | Precuration submit always fails; any member approves | transition table + roles from config |
| 231 | No screen approves/reopens precuration | workflow layer |
| 237 | Transitions commit before notifications | single-transaction transition executor with effects |
| 116 | Multi-user approval | `review.reviewers: N, not author` |
| 118 | Workflow management detail/edit views | workflow layer editor |
| 120 | Schema read-only detail view | render compiled config/DSL |
| 77 | Prefill from workflow config | `data_mapping` broken; becomes a stage-entry effect |
| 158 | Track applied migrations | needed before a structural migration |
| 156 | Prod connects as superuser, RLS never applies | same in dev; RLS on new tables untested |
| 197 | Scopes without methodology dead-end | scope must pin a methodology |
| 238 / 239 | Reviewers don't see evidence; evidence cells accept invalid PMIDs/points | forms validation from config |
| 251 / 258 | /12 vs /18 bars; "SOP v11" hard-coded in UI | caps/labels from config |
| 87 | Prevent deleting precuration with curation | workflow guard |

---

## 4. Gap analysis vs target

Legend: EXISTS / PARTIAL / MISSING.

### 4.1 Container, versioning, pinning

| Concept | Status | Where / gap | Smallest path |
| --- | --- | --- | --- |
| One "methodology" bundling workflow+forms+scoring | PARTIAL | `workflow_pairs` bundles 2 schemas; workflow lives in code | New `methodology_versions` row holds the whole compiled config |
| Versioned, immutable | PARTIAL | `(name, version)` unique, but PUT mutates in place; `schema_hash` exists | `methodology_versions(id, methodology_id, version int, status draft/published/retired, dsl_source text, compiled jsonb, compiled_hash, compiler_version, created_by, published_at)`; trigger or CRUD rule: compiled immutable once published |
| DSL source stored | MISSING | none | `dsl_source` column; compiled JSON is the runtime truth |
| Curations pinned to version | MISSING | curations → pair → mutable schema | add `methodology_version_id` to precurations + curations (NOT NULL after backfill); scope gets `methodology_id` (follows latest published) |
| Key-rename migrations between versions | MISSING | none | `compiled.migrations: [{from_version, renames: {old_path: new_path}}]` + explicit "upgrade curation to vN" action that rewrites `evidence_data` and re-scores; never automatic |
| Test fixtures (example curation → expected score/class) | MISSING | backend tests only, no config-attached fixtures | `compiled.fixtures[]`; compiler runs them at publish; publish blocked on failure. ClinGen SOP boundary cases become fixtures |

### 4.2 Workflow layer

| Concept | Status | Where | Smallest path |
| --- | --- | --- | --- |
| Stages entry/precuration/curation/review/active | EXISTS (hard-coded) | `workflow_stage` enum, `workflow_engine.py:39-60` | keep enum as **stage kind**; config names stages and maps each to a kind. `expert_panel` = a review-kind stage. Avoids enum churn |
| Transitions table | EXISTS (hard-coded) | `:39-60` + DB trigger `002:387-418` + precuration CRUD | interpreter reads `compiled.workflow.transitions`; delete `valid_transitions`, `_get_role_requirements`, `manage_workflow_transitions` trigger and the precuration-specific submit/approve paths |
| Role guards per transition | PARTIAL (buggy) | `:662-758` (reviewer always allowed) | `who: [curator, scope_admin]` evaluated against `scope_memberships.role` only |
| Conditions ("when valid and every scored_item has pmid") | MISSING | `_get_content_requirements` are strings | expression evaluator over `{evidence, score, reviews, item}`. Share the same evaluator with forms (`required when`) and scoring (`counts when`) |
| N reviewers / not-author | PARTIAL | 1 implicit reviewer, `created_by` check only | `review: {required: N, distinct_from: [author, previous_reviewers]}` consumed by `_check_all_reviews_complete` (fix the 0-reviews case) |
| `back curation when changes_requested` | MISSING | `request_changes` only notifies | transition triggered by review outcome |
| Effects (notify, assign, recurate after 3y) | PARTIAL | notifications hard-coded `:998-1056`; no scheduler | effect list per transition, run **in the same transaction** (fixes #237). "Recurate after 3y" needs a periodic job (Redis is unused, #159, or a cron/startup task); this is the only new runtime piece |
| Atomic transition | MISSING | multiple commits | one `execute_transition` = validate → mutate → audit → effects → single commit |
| Prefill on stage entry | PARTIAL (broken) | `data_mapping` + `_prefill_curation_data` | effect `copy: {from: path, to: path}` with real nested path lookup |

### 4.3 Forms layer

| Concept | Status | Where | Smallest path |
| --- | --- | --- | --- |
| Forms per stage | PARTIAL | one schema per pair side (precuration/curation) | `compiled.forms[stage]` |
| Steps → fields | PARTIAL | `ui_configuration.layout.tabs[].sections[].fields` (paths) + nested `field_definitions` | collapse into one tree: `steps[].fields[]`. Drop the separate layout/fields split (two places to rename) |
| Typed fields (gene/HGNC, MONDO, HPO, PMID, HGVS) | PARTIAL | types string/enum/number/...; PMID via `validation` regex; HGNC/HPO/PubMed validators exist in `services/validators/` | add semantic types; map each to existing validator + regex. HGVS/MONDO = regex first |
| choice/text/bool/number | EXISTS (inconsistent names) | string/enum/boolean/number/integer | normalise names in compiler |
| computed fields | MISSING | `computed_fields` columns unused | `computed: expr` evaluated server-side on save |
| Scored evidence table | EXISTS (implicit) | `type: array` + `item_schema` + `ui_component: EvidenceTable` + `scoring{}` | first-class `evidence_table` field that references a scoring `item_type` |
| required/visibility conditions | MISSING | only boolean `required`; `dependency` rule type (unused) | `required when <expr>`, `visible when <expr>` |
| help text | PARTIAL | `description`, `help_text` on sections | keep |
| Server-side validation of evidence | MISSING in practice | 3 validators, none called on save/submit | one validator generated from compiled forms; call on save (warnings) and as the transition condition `valid` (errors) |
| JSON Schema for frontend | PARTIAL (broken shape) | `generate_json_schema` | serve `compiled.forms` directly. Frontend renders from it; no JSON-Schema translation needed |

### 4.4 Scoring layer

| Concept | Status | Where | Smallest path |
| --- | --- | --- | --- |
| Which items count (status=score, has pmid, in range) | MISSING | engine counts everything | `count_when: score_status = score and pmid and points in range` per item type |
| Per evidence type default/range/step | PARTIAL (data only) | field `scoring{range, default_points}` + `evidence_categories`; engine uses hard-coded `.get(..., default)` | `item_types.<name>: {points_field, default, range, step}` |
| Caps incl. shared caps | PARTIAL | constants `clingen.py:38-57`; config `max_score` unread; no shared cap | `caps: [{sum: [models, rescue], max: 4}]`, evaluated bottom-up |
| Sections (genetic ≤12, experimental ≤6), total | EXISTS (hard-coded) | constants | config |
| Classification bands | PARTIAL / contradictory | engine `:60-68`, config `verdicts` (2 grammars) | ordered `bands` + flags; `Definitive = Strong and replicated` where `replicated` is a form field (bool) |
| Curator-asserted Disputed/Refuted | MISSING | negative-score hack `:66-67` | `asserted_classifications: [Disputed, Refuted]` that override computed when a field is set; requires reason |
| Explanation required above default | MISSING | | `require explanation when points > default` (forms condition, reused) |
| Trace/explain output | PARTIAL | `ScoringResult.evidence_breakdown`, `verdict_rationale` | interpreter emits per-node `{raw, capped, cap_source, counted_items, excluded_items[reason]}` |
| Persisted computed score | BROKEN | trigger wipes (#234); only GET /score writes | compute on every save/transition in Python; store `computed_scores` incl. `methodology_version_id` + `compiled_hash`; delete trigger |
| Pluggable engines | EXISTS | `ScoringEngine`/`scoring_registry` | keep the ABC as the extension point but ship one `ConfigScoringEngine`; delete ClinGen/GenCC/Qualitative classes once fixtures pass |

### 4.5 What becomes an interpreter, what is deleted

New code (all in `backend/app/methodology/`, each file ≤650 lines):
`dsl/` (parser → AST → compiled JSON; Lark or a hand-written recursive-descent parser), `model.py` (Pydantic for the
compiled JSON = the contract the visual editors and the frontend share; export via OpenAPI so `make api-types`
gives TS types), `expr.py` (one safe expression evaluator, no `eval`), `workflow.py`, `forms.py`, `scoring.py`
(each interprets `compiled`), `fixtures.py` (runs `compiled.fixtures`).

Deleted or replaced: `scoring/clingen.py` (1358), `scoring/gencc.py`, `scoring/qualitative*.py`,
`scoring/registry.py` (→ trivial), `core/schema_validator.py` (1106), `crud/schema_validators.py` (485),
`crud/curation.py:44-195`, `crud/gene_catalogue.py:26-128`, the transition/role tables in
`crud/workflow_engine.py` (~400 lines of 1271), precuration-specific transition methods, triggers
`calculate_schema_scores` and `manage_workflow_transitions`, `/validation/*` and `/schemas/scoring-engines/*`
endpoints (replaced by `/methodologies/{id}/versions/{v}` with `compile`, `test` and `explain`). Net change is likely
negative in lines.

Reuse: the five JSONB columns are **not** worth reusing as the store, because their shapes are inconsistent and
partly unread. Keep `curation_schemas`/`workflow_pairs` read-only for history, and generate `methodology_versions` v1 from
them once (ClinGen, GenCC, Qualitative, each paired with Standard_Precuration).

---

## 5. Risks

1. **evidence_data migration.** 4 shapes in dev (§1.3), and production is unknown. Plan: a read-only shape
   census query on prod first; a Python migration script (not SQL) that maps shape B (root-level, `points`/`status`/`proband`) →
   shape A (`proband_counted_points`/`score_status`/`proband_label`), keeps the original under
   `evidence_data._legacy`, and flags C/D as "needs re-entry" instead of inventing items. Re-score after
   migration and diff against any human-recorded verdicts.
2. **Verdict history changes.** Fixing thresholds (#157) changes classifications of existing active
   curations. Pin them to a `clingen-sop11@0` version that reproduces today's (wrong) engine. Re-scoring
   under the corrected version should be an explicit, audited "upgrade" action, so published verdicts never change silently.
3. **Version pinning semantics.** Decide: does a draft follow the scope's latest version? Proposal:
   pinned at creation; explicit upgrade with migration preview. Precuration and curation must share a
   version, so pin both from the same methodology version.
4. **Enum coupling.** `workflow_stage`/`curation_status` are PG enums used by views, RLS helpers and
   triggers. Keep them as *kinds* and store the config stage name in a new `stage_key varchar`. Do not
   create enum values per config.
5. **Two state machines.** The trigger `manage_workflow_transitions` must be dropped in the same release
   in which the interpreter takes over, or the two will fight (approved→active today).
6. **RLS.** New tables need policies: read for scope members of scopes using the methodology (or public if
   published), write for app admins only (#212). This is untestable in dev because `dev_user` is superuser and bypasses RLS. Use
   `make test-postgres` with a non-superuser role (#156). Curation RLS is unaffected if the
   `scope_id`-based policies stay.
7. **Performance.** Compiled JSON for ClinGen is about 30 KB. Cache parsed `compiled` per `(version_id, hash)` in-process
   (immutable, so the cache never needs invalidation). Scoring a curation is O(items) and cheap, so score on save. List
   views must read persisted `computed_scores` instead of recomputing (today `crud/curation.py:315-345`
   recomputes per row). Add a GIN or expression index only if filtering by verdict is needed. A
   `computed_verdict` column already exists.
8. **Migration tooling.** There is no applied-migration tracking (#158), and this change is multi-step (DDL, backfill,
   NOT NULL, drop triggers). Land #158 first or make every file strictly idempotent.
9. **Expression language security.** Conditions are authored by admins. Use a whitelisted AST evaluator
   (paths, comparisons, `and/or/not`, `every/any/count/sum`) with no attribute access and no `eval`.
10. **Frontend contract.** The frontend currently reads `field_definitions`/`ui_configuration` raw. Serve
    the compiled forms through a typed Pydantic model so `src/types/api.ts` covers it. Otherwise the
    editors and the renderer will drift.

## 6. Recommended order (each step shippable)

1. Delete trigger `calculate_schema_scores`. Compute score in Python on save/submit and store it. Make list views
   read `computed_scores` (#234, part of #157).
2. Add `methodologies` / `methodology_versions` + Pydantic compiled model + `expr.py`. Import v0 from the existing
   seeds (fields + layout + hard-coded thresholds as config). Pin all curations/precurations (backfill
   via pair → schema).
3. Scoring interpreter + ClinGen fixtures. Must reproduce v0, then publish v1 with SOP-correct bands, shared
   caps, `count_when` and asserted classifications. Delete engines and duplicate calculators.
4. Workflow interpreter (transitions, roles, conditions, N reviewers, effects, single commit). Drop
   `manage_workflow_transitions` and the precuration-specific paths (#229, #237, #116).
5. Forms interpreter: server validation on save/submit, conditional required/visible, typed fields wired
   to the existing HGNC/HPO/PubMed validators. Serve compiled forms to the frontend (#227).
6. DSL text format + compiler diagnostics + `test`/`explain` endpoints, then the visual editors (#219, #118).
7. Version upgrade/migration action for pinned curations, and a scheduled "recurate after N years" effect.
