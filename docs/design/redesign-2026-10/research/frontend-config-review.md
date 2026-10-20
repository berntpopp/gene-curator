# Frontend config-driven rendering: review and migration path

Date: 2026-10-21. Scope: `frontend/src` (read-only review), with backend touch points where the
frontend depends on them. Paths are relative to `frontend/src` unless prefixed. Target: one
versioned methodology config (workflow, stage forms, scoring) authored as DSL plus visual
builders (mockups `FormBuilder`, `Scoring`, `Studio`, `Methodologies`, `Workflows`, `Curation`
in `../source/`).

## TL;DR

- The generic renderer exists (`components/dynamic/*`) but **renders nothing today** (#227). Fixing
  the store alone is not enough: the backend `json-schema` endpoint strips almost every key the
  renderer reads (title, component, hint, options labels, per-field `required`, `ui_configuration`,
  `scoring_configuration`).
- The ClinGen form is about 3,100 hand-written lines (`components/clingen/**`) that **duplicate data
  already in the seed config**: `database/sql/020_complete_sop11_schema.sql` already has
  `ui_component: "EvidenceTable"`, `item_schema` (columns), `scoring.default_points/range`, and
  category `max_score` caps. The frontend ignores all of it and hard-codes its own copies, which have
  drifted from the seed.
- There are **5 frontend score calculators and 4 backend ones**, with 3 different classification rules.
  The design (Scoring mockup) is a sixth rule set (models+rescue share a cap of 4; Disputed/Refuted
  are asserted, not computed).
- No conditional logic (`when`), no computed fields, no steps, no HGVS or gene field type, and no
  config-level validation that the frontend can show (no diagnostics).
- Recommendation: **backend owns the DSL** (parse, compile, format, validate, score) and serves one
  immutable **compiled methodology version** (IR JSON). The frontend gets rid of all ClinGen code
  and renders forms from the IR through a type registry, with a generic `scored-table` field type.
  The DSL editor is CodeMirror 6 with diagnostics from `/compile`. Visual builders edit the IR, and
  the backend prints it back to canonical DSL.

---

## 1. Generic renderer (`components/dynamic/*`)

### Data flow

| Step | Where | What |
| --- | --- | --- |
| Load | `DynamicForm.vue:481-493` (watch, immediate) **and** `:524-535` (onMounted) | `validationStore.generateJsonSchema(schemaId)` is called twice per mount (#177) |
| Store | `stores/validation.ts:92-106` | stores the whole `JSONSchemaResponse` wrapper `{json_schema, field_count, ...}` at `jsonSchemas[id]` (**#227**) |
| Read | `DynamicForm.vue:248-250` | `getJsonSchema(id)` is used as if it were the document, so `.properties` (`:63,66`) is always `undefined` and the form is empty |
| Backend | `backend/app/core/schema_validator.py:140-167`, `:995-1102` | `generate_json_schema` outputs only `type`, `minimum/maximum`, `minLength/maxLength`, `pattern`, `enum` (values only, **labels dropped**), `items`, `description`, plus a top-level `required[]`. It drops `title/label`, `component`/`ui_component`, `hint/help_text`, `placeholder`, `multiline`, `enumOptions`, `icon`, `helpUrl` and per-field `required`. `step` becomes `multipleOf` (the renderer reads `step`). |
| Layout | `composables/useFormTabs.ts:47-93` | reads `jsonSchema.ui_configuration.layout.tabs`. The endpoint never returns it, so the flat fallback is always used. |
| Scoring | `DynamicForm.vue:267-269,171-179` | reads `jsonSchema.scoring_configuration.engine`. It is never returned, so the sidebar never shows. |

So even with the #227 one-line store fix, fields render with snake_case labels, no custom components,
no option labels and no required markers. The useful source is the raw schema
(`schemasStore.fetchSchemaById`, already loaded by `SchemaDrivenCurationForm.vue:472`), but it uses the seed
vocabulary (`help_text`, `min_length`, `options[{value,label}]`, `item_schema`, `ui_component`,
`type: enum|string|integer`), not `FieldSchema` (`components/dynamic/types.ts:66-97`). A normaliser
is needed either way, and that normaliser is exactly the "compiled config" (section 5).

### Components

| File | Lines | Role | Notes |
| --- | --- | --- | --- |
| `DynamicForm.vue` | 553 | loads schema, tabs or flat, backend validation, Save/Submit, score sidebar | Validates on **every change**: the deep watch `:496-504` bypasses the 500 ms debounce of `:303-311`/`:331-349`. Actions are shown even when `readonly` (`:144-166`, #227). Its own Save/Submit plus the parent's `FormActions` give two button rows (`components/forms/SchemaDrivenCurationForm.vue:40-83`). |
| `DynamicField.vue` | 616 (limit 650) | type switch `v-if` chain: registry component, string, textarea, enum select, number, boolean, date, nested, unknown | The same prepend/append/hint-truncation slot block is pasted 5 times (`:36-78`, `:98-140`, `:160-202`, `:225-267`, `:323-365`). The registry component (`:4-13`) gets **no** `rules`/`error-messages`, so custom fields never show validation. Number fields emit strings. An enum on a `number` type falls to a text field. |
| `DynamicNestedField.vue` | 207 | object/array recursion (array = card per item, "Add Item") | Arrays of objects render as stacked cards, not a table, which is unusable for evidence rows. Depth cap 10 (`DynamicField.vue:428`). |
| `TabContent.vue` | 183 | tab → expansion panels (sections) → fields by dot path | `getFieldSchema` walks `properties`/`items.properties` (`:328-366`). Section-level `component` (seed: `ScoreSummary`, `LumpingSplittingSection`, `020_...sql:931,1015`) is **not supported**, so those sections render empty. Column width rule is hard-coded (`:239`). |
| `composables/useFormTabs.ts` | 213 | tab validation, score badge, error dot, swipe | Needs at least 2 valid tabs, otherwise flat (`:87`). Tab→score key mapping is hard-coded for ClinGen (`:111-115`), and badge colours are hard-coded thresholds 7/2 (`:164-168`). |
| `composables/useValidationRules.ts` | 146 | Vuetify rules from `required/minLength/maxLength/minimum/maximum/pattern/enum` | Good, reusable as is. No conditional required. |
| `componentRegistry.ts` | 54 | `Record<string, Component>`: MONDOAutocomplete, PMIDInput, HPOInheritanceSelect, OMIMAutocomplete, HPOInput | Keyed by component name, not by field type. No value-shape contract. Becomes the field-type registry (section 5). |
| `validationResult.ts` | 35 | narrows backend `ValidationResponse` | Reusable. |
| `ScoreDisplay.vue` + `composables/useSchemaScoring.ts` | 339 + 215 | generic score sidebar | `totalScore` sums **every** `score_calculations` value (`useSchemaScoring.ts:48-56`), so genetic + experimental + total are counted twice. It is also never reached (see above). |
| `SchemaSelector.vue`, `ScopeSelector.vue` | 200, 107 | pick precuration/curation schemas and create a workflow pair | Used by `views/ScopeSelection.vue:40`. |

**Conditional logic:** none. A grep for `visible_if|show_if|when|depends_on|condition` in `src` finds nothing
form-related. The seed has `classification_rules.conditions` (scoring only).

**Validation:** client rules (above), plus backend `/validation/validate-evidence` on every change
(`stores/validation.ts:51-73`), plus `/validate-field` on blur (`DynamicForm.vue:351-361`). The backend
ClinGen score path `schema_validator.py:805-836` reads legacy flat keys (`case_level_score`, ...) and only
runs for `engine == "clingen"`. The seed engine is `"clingen_sop_v11"` (`020_...sql:785`), so the
seeded methodology returns **no** `score_calculations`.

### Composables around the form

| File | Notes |
| --- | --- |
| `composables/useHistory.ts` (144) | undo/redo. `JSON.stringify` compare on every record (`:63`). Fed by a deep watch in `SchemaDrivenCurationForm.vue:253-261`. Part of the #232 lag. |
| `composables/useFormRecovery.ts` (253) | localStorage autosave. Deep watch (`:186`) serialises the whole tree. Key `curation-{id}-schema-{schemaId}-v2` (`SchemaDrivenCurationForm.vue:216-218`): **should become methodology version hash**. The timestamp is never passed to the dialog (#246). |
| `components/forms/useCurationSubmission.ts` (218) | save/submit for both paths. `lockVersion + 1` bug (#240). |
| `composables/useScoring.ts` (134) | yet another ClinGen calculator on `evidence_items[]` (`:49-112`) with different caps (segregation 7, rescue 2), /12 progress (#251). Used by `components/evidence/ScorePreview.vue:239` in the **generic** path sidebar. |

## 2. Hand-written ClinGen path

### Switch

`components/forms/SchemaDrivenCurationForm.vue:195-203`: `schema.use_dynamic_form` if defined, else
`!name.includes('clingen') && !name.includes('sop')`. The DB column defaults to `false` and is
set to true for non-ClinGen names (`database/sql/027_...sql:55-69`). While the schema is loading, `''`
counts as "not ClinGen", so the generic form paints first (#241). The flag goes away once ClinGen is a
generated instance.

### What is hard-coded that config should provide

| Hard-coded thing | Where | Seed config already has it? |
| --- | --- | --- |
| Tab layout (Summary, Genetic, Experimental, Contradictory, Lumping) + icons + score chips | `ClinGenCurationForm.vue:23-62` | yes: `ui_configuration.layout.tabs` (`020_...sql:921-1020`) |
| Section/sub-table layout, panel titles, "Default: x pts"/"Range: a-b" chips | `GeneticEvidenceSection.vue:10-216` (501 lines), `ExperimentalEvidenceSection.vue:11-291` (646 lines), `ContradictoryEvidenceSection.vue` (201) | partly (`description`, `help_text`) |
| **Column definitions** (17 arrays: `nullVariantColumns`, `otherVariantColumns`, `arNullVariantColumns`, `arOtherVariantColumns`, `segregationColumns`, `caseControlColumns`, `aggregateColumns`, `functionColumns`, `proteinColumns`, `expressionColumns`, `patientCellsColumns`, `nonPatientCellsColumns`, `organismColumns`, ...) | `sections/evidenceTableColumns.ts:5-446` | yes: `item_schema` per table (`020_...sql:72-118` etc.), and **richer**: `proband_not_counted_points`, `sex`, `age`, `zygosity`, `de_novo` ... are in the seed but not in the UI. Labels differ (`Splice (+/-1,2)` vs `Canonical +/- 1,2 splice`). |
| Per-column min/max/step | `evidenceTableColumns.ts:35-43,78-86,...` | yes: `item_schema.*.min/max/step` |
| Default points for a new row (1.5, 0.1, 0.5, 1, 2, ...) | `GeneticEvidenceSection.vue:316,345,375,402`, `ExperimentalEvidenceSection.vue:401-539` | yes: `scoring.default_points` per table, and `scoring_configuration.evidence_categories[].default_points` |
| Empty data shape | `evidenceDefaults.ts:3-46` | derivable from field tree |
| Caps (case-level 12, segregation 3, case-control 6, genetic 12, function 2, alteration 2, models 4, rescue 4, experimental 6, total 18) | `scoring.ts:64-111`, `ClinGenCurationForm.vue:298-310`, `GeneticEvidenceSection.vue:280-288`, `ExperimentalEvidenceSection.vue:352-375` | yes: `scoring_configuration.evidence_categories[].max_score` (`020_...sql:784-870`) |
| Case-control rule | `scoring.ts:55-62` **sums** single+aggregate; `GeneticEvidenceSection.vue:282-288` takes **max** (#157) | `max_score` only, no rule. The design says "max of single, aggregate". |
| Classification bands | `scoring.ts:115-122` (12/7/2/0.1, Disputed if any contradictory row); `views/curation/curationScores.ts:128-134` (total + genetic gates, 12/9/1); `useScoring.ts:91-96` (12/7/2/0.1) | seed `classification_rules` uses Moderate 7-11.99, Limited 0.1-6.99 (`020_...sql:876-915`). The design uses Limited 1-6, Moderate 7-11, Strong 12-18, Definitive by assertion. |
| Submit gate "needs case-level or segregation evidence" | `ClinGenCurationForm.vue:317-332` | no. This should be a stage gate in the workflow layer ("every scored_item has pmid" in the Workflows mockup). |
| Header: disease/MOI/expert panel from precuration, `'SOP v11'` literal | `ClinGenCurationForm.vue:277-291` (#258) | no. This should be "fields from previous stage" plus methodology metadata. |
| Lumping & splitting read-only tab | `ClinGenCurationForm.vue:107-109`, `sections/LumpingSplittingSection.vue` (403) | seed refers to it as a section `component` |
| Detail-view scores | `views/curation/curationScores.ts:66-125`, used by `CurationDetailView.vue:585-588` | should read persisted `computed_scores` (#157) |

`EvidenceDataTable.vue` (159 lines) is already a generic column-driven table (`EvidenceColumn`:
`types.ts:54-63`, with `pmid|select|number|text`). Its known defects: it emits on every keystroke (`:25,42,58,70` → #232),
has no aria-labels or focus, `parseFloat(x)||0` coercion (`:58`, #239), and no use of `PMIDInput` validation. It is the
seed of the generic `scored-table` field type.

## 3. Evidence entry components: reuse as field types

All of them take `modelValue/label/hint/required/disabled` and emit `update:modelValue`, so they fit the
registry contract with small changes. All call `ontologyAPI`/`publicationsAPI` directly from the
component (AGENTS.md says to go through stores; acceptable for lookup widgets, but note it).

| Component | Value | Fits type | Gap |
| --- | --- | --- | --- |
| `MONDOAutocomplete.vue` (305) | `string` id; label is emitted separately (`update:diseaseName`, `:252-253`) | `mondo` | Through the registry only the id is stored, so the label is lost (`DynamicField.vue:4-13` binds only `modelValue`). Value should be `{id,label}`, or the IR declares a companion key. |
| `OMIMAutocomplete.vue` (459) | `string \| string[]` (`multiple`) | `omim` | fine |
| `HPOInput.vue` (350) | `string[]` | `hpo` (multi) | no `under` (root term) filter as used by the mockup `moi_hpo : hpo under HP:0000005` |
| `HPOInheritanceSelect.vue` (327) | `string` shortcode + `update:hpoId` | `hpo` with root HP:0000005, or `choice` | special case of the above. Keep it as the widget for `hpo under HP:0000005`. |
| `PMIDInput.vue` (485) | `string[]` with Europe PMC batch validation | `pmid` (multi) | needs a single-value/cell mode for table columns (#239, and the Curation mockup "paste a PMID to fetch the citation") |
| `ScorePreview.vue` (274) | display | none | delete (the score panel comes from the IR) |
| gene/HGNC | none. `composables/useHgncSearch.ts` (331) is only used by `components/gene/AddGeneModal.vue` | `gene` | need a thin autocomplete over `useHgncSearch` |
| HGVS | none | `hgvs` | text plus syntax check. The VEP/variant validation lookup is optional later. |
| computed | none | `computed` | evaluate an IR expression; read-only display |

## 4. Admin editors today

| View | Lines | Edits | Reuse |
| --- | --- | --- | --- |
| `views/SchemaEditor.vue` | 433 | raw JSON textareas for `field_definitions` and `scoring_configuration` only (`:91-149`), read mode = `JSON.stringify` `<pre>` dumps (`:112,139`), `saveSchema` sends basics + 2 blocks (`:309-330`), validate result only logged (`:335-347`, #208). `ui_configuration`, `validation_rules`, `workflow_states` not editable (#219). | Little. Export/duplicate/delete wiring only. |
| `views/SchemaManagement.vue` | 415 | list + "New Schema" posts empty blocks that the validator rejects (`:344-365`, #207). `viewSchema` is a TODO (#120). | List/table shell becomes the Methodologies list. |
| `views/WorkflowManagement.vue` | 535 | workflow **pairs** only (precuration schema + curation schema, `:238-289`). The stage grid is the static `WORKFLOW_STAGES` constant (`stores/workflow.ts:22-63`) and configures nothing (#216). Version is hard-coded `'1.0.0'` (`:473`). Edit is a stub (#118). | Pair CRUD only. The workflow layer is MISSING. |
| `components/dynamic/SchemaSelector.vue`, `views/ScopeSelection.vue` | 200, — | choose schemas, create pair while setting up a scope | becomes "pick methodology version" (one select) |
| `components/forms/CurationSchemaSelect.vue` | 145 | schema dropdown | same |

There is no code editor dependency (no Monaco or CodeMirror in `frontend/package.json`), no drag/drop lib,
and no graph lib (needed for the Workflows canvas).

## 5. Gap analysis and smallest path

| Concept (target) | Status | Evidence | Smallest path |
| --- | --- | --- | --- |
| Versioned methodology (3 layers, one version) | PARTIAL | `curation_schemas` versioned rows + `workflow_pairs`. Workflow stages are hard-coded in backend `crud/workflow_engine.py` and `stores/workflow.ts:22`. | New `methodology_versions` row (immutable once published) that holds DSL source + compiled IR + hash. Curations pin `methodology_version_id`. Existing schemas get wrapped, not rewritten. |
| Compiled config delivered to the frontend | MISSING | lossy `/validation/schema/{id}/json-schema` | `GET /methodologies/{id}/versions/{ver}/compiled` returns IR, with `ETag` = content hash. Pinia `methodologies` store caches it by hash forever (immutable). Delete `generateJsonSchema` + `jsonSchemas` from `stores/validation.ts`. |
| Steps / tabs / sections | PARTIAL | `ui_configuration.layout.tabs[].sections[].fields` + `useFormTabs`/`TabContent` | IR `stage.form.steps[]` → reuse `useFormTabs` (rename tab→step) and `TabContent`. Drop the "at least 2 tabs" rule and the hard-coded score keys (score badge from IR `step.score_ref`). |
| Typed fields: text, number, bool, choice, date | EXISTS (broken by #227) | `DynamicField.vue` | Move each `v-if` branch into a registry entry. One shared `FieldShell` (label/hint/help/icon) replaces the 5 pasted slot blocks, which also brings `DynamicField` well under the 650 limit. |
| gene/HGNC | MISSING | `useHgncSearch` only | `GeneField.vue` over `useHgncSearch` |
| MONDO, HPO, PMID, OMIM | PARTIAL | `components/evidence/*` | register by type; fix value shape (MONDO `{id,label}`), add `under` for HPO, single mode for PMID |
| HGVS | MISSING | — | text + regex check in IR `pattern`; lookup later |
| computed | MISSING | — | IR expression evaluated by a small TS evaluator (shared op set with backend) |
| **scored evidence table** | PARTIAL | `EvidenceDataTable.vue` (generic columns), seed `ui_component: "EvidenceTable"` + `item_schema` + `scoring` | **Yes, ClinGen tables fit one generic type.** See below. |
| required / visibility conditions | MISSING | no `when` anywhere | IR `when` as a JSON-Logic-style AST (`{"==":[{"var":"moi"},"other"]}`). Evaluate in TS for visibility and in Python for required-on-submit, with shared fixtures. Hidden fields are not validated and not submitted. |
| help text | PARTIAL | `hint`/`tooltip`/`helpUrl` in `FieldSchema`, seed `help_text`/`description` | normalise in the compiler to `help` (+ `help_url`) |
| Client validation | EXISTS | `useValidationRules.ts` | keep; feed it from IR; also pass `rules`/`error-messages` to registry components |
| Server validation | PARTIAL | `schema_validator.py` (rejects its own seeds, #207) | the validator validates against the IR, not against `field_definitions` |
| Scoring rules (filter, points/default/range, caps, shared caps, sections, total) | PARTIAL / duplicated | 5 FE + 4 BE calculators (section 2). Backend `scoring/clingen.py` is a hard-coded engine; seed `scoring_configuration` is descriptive only. | Compile the DSL scoring block to a declarative IR (row filter, per-class points, caps incl. shared, sections, total, bands). One **backend** evaluator returns totals + **trace**. The frontend shows it and deletes `scoring.ts`, `curationScores.ts`, `useScoring.ts`, `useSchemaScoring` summing, and `ScorePreview`. |
| Classification bands | PARTIAL / conflicting | 3 different rules (section 2) | IR `bands[]` + asserted classes (Definitive/Disputed/Refuted) with required reason (Scoring mockup), and one `config/classification.ts` for colours (#251) |
| Scoring tests and trace | MISSING | — | IR `tests[]` run by backend on compile/publish. "Run on 212 saved curations" = batch re-score endpoint. Trace = evaluator output. |
| Workflow layer (stages, gates, effects) | MISSING (static) | `WORKFLOW_STAGES` constant, `workflow_engine.py` | IR `workflow.stages[]` with `form`, `by` (scope role), `then/when/back`. Engine reads it. Table view first; canvas later. |
| DSL editor with diagnostics | MISSING | — | CodeMirror 6 + Lezer grammar (highlight only) + diagnostics from `/compile` (debounced) |
| Visual builders round-trip | MISSING | raw JSON textareas | builders edit IR → `POST /format` returns canonical DSL; `POST /compile` returns IR + diagnostics |
| Preview as curator | MISSING | — | the builder preview **is** the curator renderer fed with the draft IR (the #219 idea: no second renderer) |
| Version diff / upgrade impact | MISSING | — | backend: diff two IRs; re-score pinned curations with new IR (dry run) |

### Can ClinGen evidence tables be one generic "scored evidence table" type? Yes.

Every ClinGen table is: rows of typed columns, plus one points column with default/range per row
class, a row status that decides whether the row counts, and a category the points roll up into.
That matches `EvidenceDataTable` + seed `item_schema` + `scoring` and the Studio/Curation
mockups (columns: Proband/text, Variant/hgvs, PMID/pubmed, Points/number. Scoring: per variant
class default/max). Proposed IR (compiled; the DSL is the source):

```jsonc
{
  "key": "genetic_evidence.case_level.autosomal_dominant_or_x_linked.predicted_or_proven_null",
  "type": "scored-table",
  "label": "Variant in proband, predicted null (AD/XL)",
  "help": "…",
  "columns": [
    { "key": "proband_label", "type": "text", "label": "Proband", "required": true },
    { "key": "variant_type", "type": "choice", "label": "Type", "options": [{ "value": "nonsense", "label": "Nonsense" }] },
    { "key": "variant", "type": "hgvs", "label": "Variant", "required": true },
    { "key": "pmid", "type": "pmid", "label": "Publication", "required": true },
    { "key": "score_status", "type": "choice", "options": ["score", "review", "contradicts"], "default": "score" },
    { "key": "explanation", "type": "text", "required_when": { ">": [{ "var": "points" }, { "var": "$default" }] } }
  ],
  "points": { "key": "proband_counted_points", "default": 1.5, "min": 0, "max": 3, "step": 0.1,
              "by_class": { "column": "variant_type", "classes": {} } },
  "counts_when": { "and": [{ "==": [{ "var": "score_status" }, "score"] }, { "var": "pmid" }] },
  "category": "proband",
  "detail_columns": ["sex", "age", "zygosity", "de_novo"]
}
```

- `key` keeps today's `evidence_data` path, so **no data migration** for v1. The merge of AD/XL null and other into
  one table with per-row class (Curation mockup) is a later version with a migration rule.
- `detail_columns` covers the seed fields not shown inline (expandable row).
- The segregation "points from summed LOD and method" (mockup) is a `computed` field over a table, not a
  special widget.
- `EvidenceDataTable` becomes `ScoredTableField.vue`: columns from IR, cell editors from the same type
  registry (`cell` variant), commit on blur (#232), aria-label per cell (#239), inline range error, and
  "above default needs explanation" from `required_when`.

### Field-type registry API (extend `componentRegistry.ts`)

```ts
// components/dynamic/fieldTypes.ts (replaces componentRegistry.ts)
export interface FieldTypeDef {
  component: Component          // full field: props { modelValue, field: IRField, disabled, errorMessages, rules }
  cell?: Component              // compact editor for table cells (same props)
  empty: (field: IRField) => unknown   // initial value; replaces evidenceDefaults.ts
}
export const fieldTypes: Record<IRFieldType, FieldTypeDef> = {
  text, number, bool, choice, date, gene, mondo, hpo, pmid, omim, hgvs, computed,
  group,          // object (today DynamicNestedField)
  'scored-table'  // ScoredTableField
}
```

- `DynamicField.vue` becomes about 40 lines: `FieldShell` + `<component :is="fieldTypes[field.type].component">`.
  An unknown type is a compile error on the backend, so there is no runtime fallback to text.
- `IRField`/`IRFieldType` come from OpenAPI (`make api-types`), never hand-written (AGENTS.md).
- The builder palette (FormBuilder mockup "Field types") lists the same keys, labelled from the IR type catalogue
  served by the backend (`/validation/field-types` already exists: `stores/validation.ts:108-121`).

### Where the DSL parser lives: backend only (recommendation)

| Option | For | Against |
| --- | --- | --- |
| **A. Backend (Python) parser/compiler/printer; frontend calls `/compile`, `/format`** | One source of truth: the same code validates at publish, scores at save, and serves diagnostics. Backend must score and validate anyway (persisted `computed_scores`, RLS, 4-eyes gates), and it cannot run a TS parser without adding Node. Round-trip (IR → DSL → IR identity) is tested in one place (pytest). The frontend bundle stays small (#172/#173). | Diagnostics need a round-trip (debounce of about 300 ms is fine for an admin editor). Offline editing is not needed. |
| B. Shared TS package, backend calls it via Node or WASM | instant diagnostics | adds a Node runtime to the backend image, two languages for one grammar, and scoring must still exist in Python |
| C. Parser in both | — | guaranteed drift (we already have 9 calculators) |

Concretely:

- `backend/app/methodology/` contains `grammar` (Lark), `compile(src) -> (IR, diagnostics[{range, severity, message, fix?}])`,
  `format(IR) -> src` (canonical, so visual edits produce stable diffs), `evaluate(IR, evidence) -> scores + trace`,
  `run_tests(IR)`.
- The frontend editor is **CodeMirror 6** (about 150 KB vs Monaco's multi-MB, and it works with Vuetify). It uses a small Lezer grammar for
  highlighting/folding only (not validation), plus `@codemirror/lint` fed by `/compile`. A "fix" in a diagnostic → apply edit
  (Workflows mockup "Apply fix").
- Visual builders never touch DSL text: they mutate IR, call `/format` to refresh the code tab, and `/compile` to
  validate. The Code tab edits text and calls `/compile`, and the builder re-reads the IR. One canonical direction per edit.
- Live scoring in the curation form: call the backend evaluator on cell commit (it already validates on change). Add a TS IR
  evaluator **only** if latency is a measured problem. If you add it, run the methodology's own `tests[]` in Vitest and pytest as the
  conformance suite.

## 6. Migration path (smallest steps, each shippable)

1. **Fix the generic renderer on today's data** (#227): store `response.json_schema`; better, render from the raw
   schema via a frontend `normalizeSchema()` (seed vocabulary → `FieldSchema`) so labels/options/required/components
   survive; hide actions when `readonly`; drop the deep-watch validation; pass `rules`/`error-messages` to registry
   components. This unblocks precuration (#229, #231).
2. **Single score source** (#157): backend evaluator persisted in `computed_scores`; frontend reads it; delete
   `curationScores.ts`, `useScoring.ts`, `ScorePreview.vue`; fix `useSchemaScoring` summing; one
   `config/classification.ts` (#251).
3. **`scored-table` field type**: promote `EvidenceDataTable` with commit-on-blur, a11y and range errors (#232, #239). Render
   the ClinGen tables through `DynamicForm` from the seed `item_schema`/`scoring`. Support section-level components
   (score summary, read-only previous-stage data) as registry entries. When the generated ClinGen form matches the
   hand-written one (snapshot of the same `evidence_data` paths), delete `components/clingen/sections/*`,
   `evidenceTableColumns.ts`, `evidenceDefaults.ts`, `scoring.ts`, `ClinGenCurationForm.vue` and the `use_dynamic_form`
   switch (#240, #241, #245 go away with them).
4. **IR + compiled endpoint**: introduce `methodology_versions` and the compiled IR (JSON, typed via OpenAPI); the
   normaliser from step 1 moves to the backend compiler; curations pin a version; the recovery/history key uses the IR hash.
5. **DSL + editors**: Lark grammar, `/compile` + `/format`; CodeMirror code tab; Studio/FormBuilder field list + preview
   (reusing the renderer, #219, #120); Scoring rules table + tests + trace; Methodologies versions/diff/upgrade impact.
6. **Workflow layer**: IR stages/gates read by `workflow_engine.py`; table view first (Workflows-table mockup),
   canvas later (needs a graph lib; owner decision). Replaces `WORKFLOW_STAGES` and workflow pairs (#216, #118).
7. Conditions (`when`, `required_when`) and `computed` arrive with step 4/5, because they need the IR. Precuration MOI branch
   (FormBuilder mockup) is the first consumer.

## 7. Related open issues

| # | Title (short) | Relation |
| --- | --- | --- |
| 227 | Schema-driven forms render no fields (store wrapper) | step 1; also lossy backend endpoint (above) |
| 219 | Edit schema fields without hand-writing JSON | Studio/FormBuilder; preview = renderer |
| 232 | ClinGen cell typing lags 0.5 s | scored-table commit-on-blur; history/recovery deep watches |
| 239 | Evidence cells unlabelled, accept invalid PMIDs/points | scored-table a11y + range + PMID cell |
| 240 | ClinGen undo/quick actions do nothing, no save feedback | removed with ClinGen form; `lockVersion+1` in `useCurationSubmission` |
| 241 | Generic layout flashes before ClinGen form | removed with the `use_dynamic_form` switch |
| 245 | ClinGen form polish (score thrice, tabs overflow, `moi` unused) | generated form + config-driven default open panel (`when`) |
| 157 | SOP v11 case-control rule and thresholds disagree | single evaluator + IR bands + tests |
| 251 | One classification in five colours; /12 vs /18 | `classification.ts`; max from IR |
| 207 | Creating/duplicating a schema fails (validator vs seeds) | compiler replaces `schema_validators.py` checks |
| 208 | Schema editor hides save/validate results | diagnostics panel |
| 120 | Schema read-only detail view | Methodologies detail = read-only builder |
| 118, 216 | Workflow management stubs, static stage grid, fixed version | workflow layer |
| 213 | Duplicating creates a second active schema, same version | immutable published versions |
| 229, 231 | Precuration submit fails / no approve screen | blocked by step 1; gates from workflow IR |
| 238 | Reviewers approve without seeing evidence rows | review view renders the same IR read-only |
| 246 | Recovery dialog timestamp | recovery keyed by IR hash |
| 258 | `SOP v11` hard-coded in UI | methodology metadata from IR |
| 77 | Prefill based on workflow config | IR "fields from previous stage" |
| 164 | Migrate to Vuetify 4 | do the field registry before or with it; it shrinks the Vuetify surface in forms |

## Side findings (not in an issue yet)

- `backend/app/core/schema_validator.py:798` scores only `engine == "clingen"`, while the seed uses `"clingen_sop_v11"`, so the
  seeded methodology gets no `score_calculations` from validation. `_calculate_clingen_scores` (`:805-836`) reads legacy
  flat keys anyway.
- `useSchemaScoring.ts:48-56` double-counts (sums section scores and total).
- Seed `item_schema` columns (`sex`, `age`, `zygosity`, `de_novo`, `proband_not_counted_points`, ...) are not editable anywhere in the UI.
- `DynamicField.vue` is at 616/650 lines; any new type added inline will hit the size gate.
