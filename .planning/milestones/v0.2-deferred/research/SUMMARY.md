# Project Research Summary

**Project:** Gene Curator — Form Intelligence (v0.2)
**Domain:** Schema-driven dynamic form conditional logic for clinical genetics curation
**Researched:** 2026-02-28
**Confidence:** HIGH

## Executive Summary

Gene Curator v0.2 adds conditional field interactions — visibility, cross-field validation, and cascading dependencies — to the existing schema-driven `DynamicForm` system. The research findings are unusually clear because the codebase is mature: the component tree (`DynamicForm` → `TabContent` → `DynamicField`), the composable layer (`useValidationRules`), and the schema storage model (JSONB `field_definitions`) are all well-understood through direct code inspection. Critically, two conditional visibility syntaxes (`show_when` object and `condition` string) already exist in the production database schemas but are not evaluated at runtime. The v0.2 milestone makes those stubs real.

The recommended approach is to build a single `useFieldInteractions` composable that produces three reactive computed maps — `visibilityMap`, `crossFieldRules`, and `dynamicOptions` — which flow downward through the existing prop chain with minimal modifications. No new form library is needed; Vue 3's built-in reactivity is the correct tool, with the optional addition of `json-logic-js` (~3 kB) only if condition operators beyond simple equality are required. The key architectural insight is that computed properties — not watchers — must drive visibility, because computed properties are pull-based and cannot create infinite reactive loops. This is both the performance solution and the correctness solution.

The primary risk is the frontend/backend validation gap: the backend `SchemaValidator` does not evaluate visibility conditions, so a field that is hidden on the frontend may still fail backend required-field checks. The recommended mitigation is to clear hidden field values to `null` in `formData` when fields hide, which causes the backend's existing `if field_value is None: skip` path to handle them gracefully. A second risk is the two-syntax problem in existing schemas — the ClinGen schema uses string expressions (`"evidence_category == 'case_level'"`) while the precuration schema uses object notation (`{"lumping_splitting_applicable": true}`). A normalization layer must be built before activating the visibility engine, and ideally a SQL migration should canonicalize existing schemas to one format.

## Key Findings

### Recommended Stack

The existing stack (Vue 3.4 + Vuetify 3.9 + Pinia 2.1 + VueUse 14.1) covers all three feature areas without introducing a form framework. Every evaluated alternative — VeeValidate v4, Vuelidate 2, FormKit, Yup — was rejected for the same core reason: their rule definitions live in JavaScript closures that cannot be stored in the JSONB `field_definitions`, which breaks the schema-agnostic design.

**Core technologies:**
- **Vue 3 `computed()`**: Visibility maps and dynamic option sets — zero-cost, pull-based, cannot loop
- **Vue 3 `watch()` with `onCleanup`**: Auto-population side effects only — deliberately limited to write-to-other-field cases where computed cannot be used
- **Existing `useValidationRules.js`**: Extended (not replaced) with a `formDataGetter` parameter for cross-field rule context
- **`json-logic-js` v2.0.5 (conditional)**: Serializable JSON rule evaluation from JSONB — add only if operators beyond `eq/neq/in/truthy/falsy` are needed; skip if a 20-line inline evaluator suffices
- **Existing `DynamicForm` component tree**: Modified in three files (`DynamicForm.vue`, `TabContent.vue`, `DynamicField.vue`), not replaced

**Version status:** All existing packages are current stable. VeeValidate v5 is in beta — do not adopt. `json-logic-js` last published ~2 years ago but is intentionally complete, not abandoned.

### Expected Features

**Must have (table stakes):** These make existing precuration schema stubs functional.
- **TS-05: Visibility Evaluator Composable** — foundational; all other features depend on it; normalizes both legacy syntaxes
- **TS-01: Simple Field Visibility** — `show_when: {mode_of_inheritance: "Other"}` already in production schemas; non-negotiable
- **TS-02: Conditional Required Fields** — `conditional_required` stub already in `validation_rules` JSONB; users expect it to work
- **TS-03: Hidden Field Data Handling** — policy: preserve value in `formData`, exclude from submission payload, clear to `null` on hide to satisfy backend validator
- **TS-04: Cross-Field Validation** — date ordering, score component bounds; standard in clinical EDC systems (REDCap, etc.)

**Should have (differentiators):**
- **DIFF-01: Operator-Based Conditions** — `gt/lt/gte/lte/in/not_in/truthy/falsy`; clinical data is quantitative; trivial to add once TS-05 is built
- **DIFF-02: Cascading Select** — evidence_subtype options depend on evidence_type; zygosity options narrow by inheritance pattern
- **DIFF-04: Tab/Section Visibility** — hide entire "Experimental Evidence" tab when not applicable; reduces cognitive load
- **DIFF-03: Auto-Population (Approach A)** — event-based MONDO → disease_name fill; existing components already have lookup logic
- **DIFF-05: Visibility-Aware Completeness** — progress bar that does not penalize curators for empty hidden fields

**Defer (v2+):**
- AI-assisted field suggestions (AF-06) — out of scope per PROJECT.md
- Real-time multi-curator conflict resolution for conditional fields (AF-05) — existing optimistic locking is sufficient
- Full JSON Schema if/then/else keywords (AF-04) — custom DSL is sufficient and a migration would be disruptive
- Schema-defined populate rules / Approach B auto-population (DIFF-03 partial) — start with event-based; schema-level populate rules are Phase 2

**Anti-features to enforce:** No JavaScript expressions in schema conditions (XSS risk), no bidirectional field dependencies (cycle risk), no runtime condition editing by curators (institutional schemas, not user schemas).

### Architecture Approach

The architecture centers on a single new composable, `useFieldInteractions`, that accepts the schema and `formData` as reactive getters and returns three derived maps consumed passively by the component tree. Components are pure consumers of these maps — no field subscribes to another field's events. The dependency graph is Vue's reactive computed graph, which is explicit, traceable, and cannot loop. Modifications are localized to three existing files plus one new composable, preserving the 428 passing tests on the existing `DynamicForm` system.

**Major components:**

1. **`useFieldInteractions.js` (new)** — single source of truth; produces `visibilityMap`, `crossFieldRules`, `dynamicOptions`, and `getAutoPopulateUpdates()`; normalizes both legacy condition syntaxes; runs DAG cycle detection at schema load time
2. **`DynamicForm.vue` (modified)** — instantiates `useFieldInteractions`; passes derived maps to `TabContent`; calls `getAutoPopulateUpdates()` in `handleTabFieldUpdate` before debounced backend validation
3. **`TabContent.vue` (modified)** — receives `visibilityMap`, `crossFieldRules`, `dynamicOptions` as props; uses `v-if` (not `v-show`) on fields; passes props to `DynamicField`
4. **`DynamicField.vue` (modified)** — accepts `crossFieldRules` and `dynamicOptions` props; merges cross-field rules into existing Vuetify rules array; uses `dynamicOptions` over static schema options when provided
5. **`useValidationRules.js` (unchanged)** — cross-field rules generated by `useFieldInteractions` and merged at `DynamicField` level, preserving single-field contract

**Data flow:** User changes field A → `formData` updates → `visibilityMap`/`crossFieldRules`/`dynamicOptions` recompute automatically (Vue reactive, no explicit wiring) → template re-renders → 500ms debounce fires backend validation (unchanged).

**Schema extension:** New canonical keys in `field_definitions` JSONB: `visibility` (object with `field/operator/value`), `required_when`, `auto_populate`, `options_from`. Cross-field rules go in existing `validation_rules.cross_field` array. Both legacy formats normalized at composable init.

### Critical Pitfalls

1. **Circular field dependencies** — Field A visibility depends on B; B's options depend on A. Vue `watch` loops cause tab freezes. Prevention: build a DAG cycle detector in `useFieldInteractions` that runs at schema load time and throws a descriptive error. Use `computed` (pull-based, cannot loop) for visibility, never `watch`.

2. **Hidden field values submitted causing invisible backend errors** — Backend `SchemaValidator` validates all fields regardless of frontend visibility. The form shows no red fields but cannot submit. Prevention: clear hidden field values to `null` in `formData` atomically with the visibility change. Backend's existing `if field_value is None: skip` path handles this correctly without requiring backend changes.

3. **Async auto-population race condition** — MONDO ID selected, async lookup fires, user changes selection before first lookup returns, stale disease name overwrites correct one. Prevention: `onCleanup` callback pattern in `watch()` with `AbortController`. Note: `onWatcherCleanup` must be called before first `await`; use the third callback parameter form instead.

4. **`v-show` vs `v-if` for conditional fields** — `v-show` keeps components in the DOM; Vuetify validates all registered inputs including hidden ones, blocking form submission. Prevention: use `v-if` exclusively. Hidden fields are excluded from Vuetify's validation tree; their values persist in `formData` (no auto-clear needed for validation purposes).

5. **Two-syntax expression language in existing schemas** — ClinGen schema uses string `"evidence_category == 'case_level'"` (migration 014); precuration uses object `{"lumping_splitting_applicable": true}` (migration 016). Activating the visibility engine without normalizing these will immediately hide or show wrong fields. Prevention: audit all 4 schemas before activation; write SQL migration to canonicalize to the object format; implement a normalization function in `useFieldInteractions` as a safety net.

## Implications for Roadmap

Based on combined research, this is an incremental feature addition to a mature codebase, not a new system. The phase structure follows a strict dependency graph: the evaluator composable must exist before any consumer feature can be built. Three phases are sufficient.

### Phase 1: Conditional Visibility Engine (Build First)

**Rationale:** Self-contained, delivers immediate value, validates the architectural approach before adding complexity. The precuration schema already has `show_when` annotations — activating them requires zero schema changes. This phase also proves the `computed` map approach works with the existing prop chain.

**Delivers:**
- `useFieldInteractions.js` with `visibilityMap` only (defer cross-field rules and options to later phases)
- `DynamicForm.vue` → `TabContent.vue` → `DynamicField.vue` modifications for `v-if` visibility
- Legacy syntax normalization (`show_when` object → canonical; `condition` string → canonical)
- DAG cycle detector (must exist before any schema with circular deps is loaded)
- `useFieldInteractions.spec.js` covering all operators and legacy format normalization

**Addresses:** TS-05, TS-01, TS-03 (hidden field data policy and payload exclusion)

**Avoids:** Pitfalls 1 (cycle detection), 4 (`v-if` not `v-show`), 5 (syntax normalization), 7 (KeepAlive stale state — solved automatically by computed approach), 9 (watcher proliferation — solved by single computed map)

**Research flag:** Standard patterns — skip `/gsd:research-phase`. Vue 3 computed reactivity is thoroughly documented.

**Estimated effort:** 3–4 days

### Phase 2: Cross-Field Validation and Conditional Required

**Rationale:** Builds on Phase 1's composable with minimal additional complexity. The `crossFieldRules` export is an extension of the same evaluation engine already established. Conditional required rules (`TS-02`) are the most user-visible gap in the current system — the schema already defines them, users already expect them to work.

**Delivers:**
- `useFieldInteractions.js` extended with `crossFieldRules` computed map
- `DynamicField.vue` merging cross-field rules into Vuetify validation rules array
- Backend alignment: clear-on-hide (null values) ensures backend `SchemaValidator` does not require hidden fields (no backend code change needed)
- `validation_rules.cross_field` array support in schema (date ordering, numeric bounds, conditional required)

**Addresses:** TS-02, TS-04, DIFF-01 (operator set extension — trivial at this point)

**Avoids:** Pitfalls 2 (backend errors on hidden fields), 4 (required-but-hidden paradox), 6 (tab error badge ghosting — atomically clear `backendErrors` with field hide), 10 (cross-field error attribution convention)

**Research flag:** Standard patterns. Vuetify rule function signature is well-understood. One decision needed: establish cross-field error attribution convention (error goes on the dependent field, not the trigger) and document it in code.

**Estimated effort:** 3–4 days

### Phase 3: Field Dependencies (Cascading Selects and Auto-Population)

**Rationale:** Most complex phase because auto-population involves writing to `formData` (a side effect), not just reading it. Cascading selects require the `dynamicOptions` map. Both are deferred to after Phases 1 and 2 are stable because they involve mutations to `formData` that interact with the existing debounced backend validation.

**Delivers:**
- `useFieldInteractions.js` extended with `dynamicOptions` computed and `getAutoPopulateUpdates()` function
- `DynamicForm.vue` calling `getAutoPopulateUpdates` in `handleTabFieldUpdate` before debounce
- `DynamicField.vue` using `dynamicOptions` over static schema options
- MONDO auto-population via event-based Approach A (component emits structured event; form applies data map)
- Tab/section visibility (DIFF-04 — trivial extension of Phase 1's `visibilityMap` to tab-level conditions)
- Visibility-aware completeness progress (DIFF-05 — visibility-filtered completeness score)

**Addresses:** DIFF-02, DIFF-03, DIFF-04, DIFF-05

**Avoids:** Pitfalls 3 (MONDO race condition — `AbortController` via `onCleanup`), 8 (cascading select stale value — clear child field when parent changes and current value no longer in options), 12 (form recovery restoring stale hidden values — re-evaluate visibility after `restoreRecovery()` call)

**Research flag:** Phase 3 may need a brief research pass on the MONDO REST API endpoint availability and response schema. The `ontologyAPI` module already handles HGNC/PubMed/HPO lookups; confirm MONDO follows the same pattern.

**Estimated effort:** 4–5 days

### Phase Ordering Rationale

- Phase 1 before everything: the `useFieldInteractions` composable is a prerequisite for all consumer features. Building it first and testing it in isolation prevents debugging composable bugs through the component chain.
- Phase 2 before Phase 3: cross-field rules reuse the same condition evaluator as visibility, building confidence that the evaluator is correct before adding write-to-formData side effects.
- Phase 3 last: auto-population is the only phase that mutates `formData` (not just reads it), which requires careful sequencing with the existing debounced backend validation. Establishing that the reactive graph is correct in Phases 1 and 2 reduces risk when adding mutations.
- Flat rendering path (non-tabbed) must be updated in parallel with tabbed path in all phases — the `DynamicForm` has two rendering paths and both must receive `visibilityMap`.

### Research Flags

**Needs research during planning:**
- **Phase 3 (MONDO auto-population):** Confirm MONDO REST endpoint URL, response shape, and whether the existing `ontologyAPI.js` already supports MONDO or needs a new method. The `useFormRecovery.js` integration also needs a careful review before Phase 3 ships.

**Standard patterns (skip research-phase):**
- **Phase 1:** Vue 3 computed reactivity, `v-if` conditional rendering — thoroughly documented, no unknowns
- **Phase 2:** Vuetify validation rule functions — existing `useValidationRules.js` already demonstrates the pattern; extending it is mechanical
- **All phases — backend:** No backend changes needed for Phases 1 and 2. Phase 3 backend work (visibility-aware completeness) is a clean extension of `schema_validator.py`

## Critical Decisions to Make

These must be resolved before implementation begins, not during it.

| Decision | Options | Recommendation | Impact if Deferred |
|----------|---------|---------------|-------------------|
| Canonical condition syntax | Keep both formats with normalization vs. SQL migration to one format | SQL migration to canonical object format + normalization fallback | Normalization layer doubles in complexity every time a third syntax appears |
| Clear-on-hide vs. retain-on-hide | Clear field value when hidden vs. preserve in `formData` | Clear to `null` (backend compat) with UX retention handled by re-display when re-shown | Backend validation fails silently for stale hidden values if not cleared |
| Cross-field error attribution | Error on trigger field vs. dependent field | Always attribute to dependent field (the one needing action) | Inconsistent error placement confuses users; document convention before first PR |
| `json-logic-js` dependency | Add it now vs. inline 20-line evaluator | Inline evaluator first; add `json-logic-js` only when a schema actually needs `and/or` compound conditions | Adding it proactively adds a dependency for unused capability |
| Backend visibility enforcement | Option 1: send `hidden_fields` list in API call; Option 2: backend evaluates same conditions; Option 3: clear-on-hide makes nulls pass existing backend skip | Option 3 for v0.2 (no backend changes); plan Option 2 for v0.3 | Option 3 is fragile if hidden field had a non-null value before being cleared; implement `clearHiddenFieldValue()` atomically |

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All existing packages verified via `package.json`; alternatives evaluated against official docs and npm; no unknowns |
| Features | HIGH | Table stakes confirmed by existing schema stubs (`show_when`, `conditional_required`); differentiators confirmed by clinical form platform patterns (REDCap, Vueform) |
| Architecture | HIGH | Based on direct codebase inspection; component boundaries, data flow, and integration points are concrete, not theoretical |
| Pitfalls | HIGH (Vue patterns) / MEDIUM (UX policies) | Vue 3 pitfalls verified against official docs; UX policies (clear vs. retain) are product decisions with clear tradeoffs documented |

**Overall confidence:** HIGH

### Gaps to Address

- **MONDO API endpoint:** The `ontologyAPI.js` module handles HGNC, PubMed, HPO lookups. Whether MONDO lookup is already implemented or needs a new API method is unconfirmed. Must verify before Phase 3 begins.
- **ClinGen schema string conditions inventory:** Migration 014 uses string expressions. A full audit of which fields have `condition` strings and what they parse to has not been done. Must be done before activating the visibility engine on the ClinGen schema.
- **Form recovery integration testing:** `useFormRecovery.js` saves every 5 seconds. The interaction between recovery restoration and the visibility engine (re-evaluate visibility after restore) needs integration test coverage — this gap is not addressed by unit tests on the composable alone.
- **Backend `_validate_fields` hidden-field behavior:** The current behavior when a field with `required: true` receives `null` was inferred from code reading (`if field_value is None: skip`). This inference must be validated with a specific test case before relying on it.

## Files Created

| File | Purpose | Status |
|------|---------|--------|
| `.planning/research/STACK.md` | Technology evaluation — Vue reactivity vs. form libraries | Complete |
| `.planning/research/FEATURES.md` | Feature landscape — table stakes, differentiators, anti-features | Complete |
| `.planning/research/ARCHITECTURE.md` | Integration architecture — component modifications, composable design, data flow | Complete |
| `.planning/research/PITFALLS.md` | 13 domain pitfalls with prevention strategies | Complete |
| `.planning/research/SUMMARY.md` | This file — synthesis and roadmap implications | Complete |

## Sources

### Primary — HIGH confidence (direct codebase inspection)
- `frontend/src/components/dynamic/DynamicForm.vue` — component tree, data flow, debounce pattern
- `frontend/src/components/dynamic/DynamicField.vue` — field rendering, validation rule integration
- `frontend/src/components/dynamic/TabContent.vue` — tab/section rendering, field path resolution
- `frontend/src/components/dynamic/composables/useValidationRules.js` — existing validation composable pattern
- `database/sql/016_seed_precuration_schema.sql` — `show_when` and `conditional_required` in production
- `database/sql/014_seed_clingen_schema.sql` — string `condition` syntax in production
- `backend/app/core/schema_validator.py` — backend validation architecture and null-value handling
- `frontend/src/components/dynamic/composables/` — existing composable design patterns

### Secondary — MEDIUM confidence (official docs + community)
- Vue 3 official docs (computed, watchers, conditional rendering) — reactivity patterns
- Vuetify 3 official docs — form validation rule function signature
- Vueform conditional rendering docs — operator sets, data handling for hidden fields
- REDCap branching logic guide — clinical EDC skip logic patterns
- json-logic-js npm page — bundle size, stability, isomorphic evaluation
- OWASP Input Validation Cheat Sheet — backend enforcement requirement
- Vue 3.5 `onWatcherCleanup` — async watcher cancellation pattern

### Tertiary — LOW confidence (inference / single source)
- MONDO REST API availability — assumed to follow same pattern as HPO/HGNC in existing `ontologyAPI.js`; not directly verified

---
*Research completed: 2026-02-28*
*Ready for roadmap: yes*
