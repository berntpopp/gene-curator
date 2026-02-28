# Feature Landscape: Form Intelligence (v0.2)

**Domain:** Dynamic form conditional logic for clinical genetics curation
**Researched:** 2026-02-28
**Milestone context:** Subsequent milestone — adding field interaction capabilities to existing schema-driven DynamicForm system
**Scope:** Conditional visibility, cross-field validation, cascading field dependencies

---

## Existing Foundation (What's Already Built)

Understanding what NOT to build again, and what to extend:

| Capability | Location | Notes |
|-----------|----------|-------|
| Schema-driven field rendering | `DynamicForm.vue`, `DynamicField.vue` | Renders from `field_definitions` JSONB |
| Client-side per-field validation | `useValidationRules.js` composable | Required, min/max, pattern, enum |
| Backend validation engine | `schema_validator.py` | 12 field types, business rules |
| Tab/section layout | `TabContent.vue`, `DynamicForm.vue` | From `ui_configuration.layout.tabs` |
| Component registry | `componentRegistry.js` | MONDO, PMID, HPO, OMIM, HPOInheritanceSelect |
| Live scoring | `useSchemaScoring.js` | ClinGen, GenCC, Qualitative engines |
| `show_when` stub in schema | `016_seed_precuration_schema.sql` | `show_when: {field: value}` exists in data but is NOT evaluated at runtime |
| `conditional_required` stub | `016_seed_precuration_schema.sql` | Pattern exists in `validation_rules` JSONB but not enforced |

**Critical observation:** The data model already has two nascent patterns (`show_when` and `conditional_required`) that are stored in the schema but never evaluated. This milestone is about making them real.

---

## Table Stakes

Features that must exist for conditional forms to be useful at all. Without these, users encounter confusing, broken-feeling forms.

### TS-01: Simple Field Visibility (show/hide by equality)

**What:** A field becomes visible or hidden when another field equals a specific value.

**Why expected:** This is the most basic conditional form behavior. REDCap, JotForm, Salesforce, and every form platform support this. The precuration schema already stores `show_when: {"mode_of_inheritance": "Other"}` and `show_when: {"lumping_splitting_applicable": true}` — users who created these schemas expect them to work.

**Example in Gene Curator:**
```json
"moi_notes": {
  "show_when": {"mode_of_inheritance": "Other"}
}
"lumping_splitting_decision": {
  "show_when": {"lumping_splitting_applicable": true}
}
```

**User expectation:** When "Mode of Inheritance" is set to "Other", the "MOI Notes" field appears immediately (no page reload, no save required).

**Complexity:** Low — Vue 3 reactivity makes this straightforward once evaluation logic is centralized.

**Dependencies on existing features:** `DynamicField.vue` (add v-if), `formData` reactive object (already in DynamicForm), dot-notation path resolution (already exists in TabContent).

**Data behavior:** Hidden fields should be excluded from submission payload (matches Vueform's `requestData` exclusion pattern). Existing schema already has `show_when` keys — just need the evaluator.

**Confidence:** HIGH — Pattern already stubbed in production schema data, evaluation logic is standard.

---

### TS-02: Conditional Required Fields

**What:** A field is required only when it is visible (conditional on another field's value).

**Why expected:** Directly follows from conditional visibility. If `moi_notes` appears when "Other" is selected, it must be required when visible, and not required when hidden. The schema already has `conditional_required` in `validation_rules` but it is not enforced.

**Example in Gene Curator:**
```json
"validation_rules": {
  "conditional_required": {
    "lumping_splitting_decision": {
      "when": {"lumping_splitting_applicable": true}
    }
  }
}
```

**User expectation:** Submit button is blocked when a visible conditional field is empty. No "Required" error appears for a field that is currently hidden.

**Complexity:** Low-Medium — Requires coordination between visibility evaluator and `useValidationRules`. The pattern is defined; the evaluator and rule generator need to read it.

**Dependencies:** TS-01 (conditional visibility evaluator), `useValidationRules.js` (add `isRequired(formData)` function), backend `schema_validator.py` (must also skip hidden fields during validation).

**Backend enforcement required:** Yes. Hidden fields must not fail required checks on the backend either. OWASP input validation principles apply: client-side only is insufficient.

**Confidence:** HIGH — Pattern exists in schema data; implementation is standard.

---

### TS-03: Hidden Field Data Handling (clear vs. preserve)

**What:** A clear policy for what happens to a field's data when it becomes hidden.

**Why expected:** Without a clear policy, users hit confusing bugs: stale data submits silently, or carefully-entered data vanishes unexpectedly.

**Clinical curation context:** This matters acutely. A curator enters detailed notes for "Lumping/Splitting Rationale", then toggles the applicable checkbox off and back on. Should those notes still be there?

**Recommendation: Preserve value, exclude from payload.**

- Keep the value in `formData` while the field is hidden (prevents data loss if user accidentally toggles)
- Exclude hidden field values from the submission payload sent to the backend
- Backend must NOT require hidden fields to pass validation
- This matches how Vueform handles `requestData` (HIGH confidence from official docs)

**Two-tier behavior:**
```
On hide:   Keep formData value intact (no clear)
On submit: Exclude hidden field paths from payload
```

**Exception — cascading dependency:** When field A controls which options exist in field B, and field A changes to a value that makes field B's current selection invalid, field B SHOULD be cleared. This is a dependency reset, not a visibility hide.

**Complexity:** Low — Exclusion is handled at payload construction time; the reactive `formData` retains values naturally.

**Dependencies:** TS-01, submission handler in `DynamicForm.vue` (add field exclusion based on visibility state).

**Confidence:** MEDIUM-HIGH — Clear policy emerging from ecosystem patterns; exact behavior is a product decision.

---

### TS-04: Cross-Field Date/Numeric Validation

**What:** Validation rules that compare two fields against each other (e.g., date B must be after date A, score components must sum within bounds).

**Why expected:** Clinical curation inherently has temporal relationships (submission before review, onset before diagnosis) and scoring integrity (component scores cannot exceed category maximum). These are table stakes for data integrity.

**Examples in Gene Curator:**
- `review_date` must be >= `submission_date`
- `proband_counted_points` + `proband_not_counted_points` cannot exceed `max_per_item: 3`
- Total score calculated from components must match `total_score` field when user overrides it

**User expectation:** Error appears next to the field that violates the constraint (not just a generic form-level error). The error message names both fields: "Review date must be after submission date."

**Complexity:** Medium — Requires a cross-field rule DSL in schema `validation_rules`, an evaluator that reads multiple field values, and error attribution to specific fields.

**Schema structure (recommended):**
```json
"validation_rules": {
  "cross_field": [
    {
      "type": "date_order",
      "fields": ["submission_date", "review_date"],
      "operator": "<=",
      "message": "Review date must be after submission date"
    }
  ]
}
```

**Dependencies:** Backend `schema_validator.py` (add cross-field rule types), `useValidationRules.js` (extend for cross-field rules), `DynamicForm.vue` (pass full `formData` context to field validation).

**Confidence:** HIGH — These patterns are standard in clinical data systems (REDCap plausibility checks, VeeValidate cross-field validators).

---

### TS-05: Visibility Evaluator Composable

**What:** A single, centralized `useFieldVisibility(schema, formData)` composable that computes which fields are currently visible.

**Why expected (as infrastructure):** All other conditional features depend on a correct, performant, reactive visibility computation. Without centralizing this, every component re-implements visibility logic inconsistently.

**Design:**
```javascript
// Returns reactive computed map: { fieldPath: boolean }
const { isVisible, visibleFields } = useFieldVisibility(schema, formData)
```

**Must handle:**
- Simple equality: `show_when: {field: value}`
- Multiple conditions (AND logic): `show_when: {field1: val1, field2: val2}`
- Nested field paths via dot notation (already supported by TabContent)
- Fields inside sections inside tabs
- Operator beyond equality: needed for scientific contexts (e.g., `show_when: {score: {gte: 5}}`)

**Complexity:** Medium — Reactive computed over formData is well-understood in Vue 3; the complexity is in the condition DSL design.

**Dependencies:** Vue 3 `computed()` (already in use throughout), formData reactive ref (in DynamicForm).

**Confidence:** HIGH — Standard composable pattern; Vueform's condition system confirms approach.

---

## Differentiators

Features that go beyond what users expect, providing competitive advantage for a clinical curation platform. These should be built after table stakes are solid.

### DIFF-01: Operator-Based Conditions (beyond simple equality)

**What:** Conditions that use comparison operators, not just equality.

**Value proposition:** Clinical data is inherently quantitative. "Show 'Contradictory Evidence Notes' when `total_score` is less than 2" or "Show 'High Confidence Justification' when `classification` equals 'Definitive'" requires operator support.

**Proposed operator set (prioritized for clinical context):**
| Operator | Example use |
|----------|-------------|
| `eq` / `==` | enum selection (already table stakes) |
| `neq` / `!=` | show unless something is selected |
| `gt` / `gte` | score threshold fields |
| `lt` / `lte` | score threshold fields |
| `in` | show when one of several values |
| `not_in` | hide for specific values |
| `truthy` | boolean fields |
| `falsy` | boolean fields |

**Not needed yet:**
- `between` (two conditions `gte + lte` already covers this)
- `regex` on form values (security risk, use pattern validation instead)
- Date comparison in conditions (use cross-field validation instead)

**Complexity:** Low — Extending the evaluator with an operator lookup table is straightforward once TS-05 is in place.

**Dependencies:** TS-05 (visibility evaluator composable).

**Confidence:** HIGH — Standard in form engines (Vueform, REDCap, JotForm all support operators).

---

### DIFF-02: Cascading Select (Options Filtered by Parent Field)

**What:** The options available in field B depend on the current value of field A.

**Examples in Gene Curator:**
- "Evidence sub-type" options depend on "Evidence type" selection
- "Score range" displayed differs by "Mode of Inheritance" selected in precuration
- "Zygosity" options narrow based on "Inheritance pattern" (hemizygous only for X-linked)

**User expectation:** When field A changes, field B's dropdown instantly updates to show only valid options. If field B's current value is no longer in the new option set, field B is cleared.

**Schema structure (recommended):**
```json
"evidence_subtype": {
  "type": "select",
  "options_source": "conditional",
  "options_map": {
    "genetic": [
      {"value": "case_level", "label": "Case-Level Data"},
      {"value": "segregation", "label": "Segregation Data"}
    ],
    "experimental": [
      {"value": "functional", "label": "Functional Studies"},
      {"value": "model", "label": "Animal Models"}
    ]
  },
  "options_controlled_by": "evidence_type"
}
```

**Data behavior on parent change:** If selected value in child is no longer valid in new option set, CLEAR the child field. This is the one case where clearing on change is correct (different from hiding).

**Complexity:** Medium — Requires schema support for options maps, a computed `getOptionsForField(fieldPath, formData)` function, and DynamicField integration.

**Dependencies:** TS-01, TS-05, `DynamicField.vue` (pass dynamic options alongside static schema options).

**Confidence:** HIGH — Standard in all form platforms; the schema JSONB structure makes this straightforward to model.

---

### DIFF-03: Auto-Population (Lookup Field Triggers Data Fill)

**What:** Selecting or entering a value in field A automatically populates field B with data fetched or derived from field A's value.

**Examples in Gene Curator:**
- Selecting a MONDO ID auto-fills the disease name text field
- Selecting a PMID auto-fills title and year fields
- Selecting a gene symbol auto-populates known inheritance patterns

**Current state:** The `MONDOAutocomplete` and `PMIDInput` components emit the looked-up data, but there is no generic mechanism for the form to listen and populate related fields. This is component-specific today.

**Implementation approach:** Auto-population is not a generic form feature — it requires domain knowledge about what to fill. Two viable approaches:

**Approach A: Event-based (recommended for this milestone)**
Component emits a structured event: `{trigger: "mondo_id", data: {disease_name: "SCN1A-epilepsy", ...}}`. DynamicForm listens and applies the data map to formData.

**Approach B: Schema-defined populate rules (more powerful, more complex)**
```json
"mondo_id": {
  "on_change": {
    "populate_fields": {
      "disease_name": "$.label",
      "omim_ids": "$.xrefs.omim"
    }
  }
}
```

**Recommendation:** Start with Approach A (event-based). Existing components already have the lookup logic — connecting it to form-level population is the missing piece. Approach B is a Phase 2 item.

**Complexity:** Medium (Approach A) — Requires a `useFieldPopulation` composable and DynamicForm event handling. The actual data fetching already exists in the component registry.

**Dependencies:** Component registry components (already emit data), DynamicForm (add event handler), Pinia stores (already hold lookup results).

**Confidence:** HIGH — The pattern is clear; implementation complexity is in the event contract design.

---

### DIFF-04: Conditional Section/Tab Visibility

**What:** Entire sections or tabs can be hidden/shown based on form state, not just individual fields.

**Examples in Gene Curator:**
- "Experimental Evidence" tab only shown when genetic basis is confirmed
- "Contradictory Evidence" section appears when any evidence item is marked as "contradicts"
- "Rescue Evidence" sub-section shown only when model organism data is present

**Value proposition:** Prevents curators from seeing and accidentally filling sections that don't apply to their curation context. Reduces cognitive load significantly on complex ClinGen forms.

**Schema structure (recommended):**
```json
"ui_configuration": {
  "layout": {
    "tabs": [
      {
        "id": "experimental",
        "name": "Experimental Evidence",
        "show_when": {"genetic_basis_confirmed": true}
      }
    ]
  }
}
```

**Complexity:** Medium — Requires extending TS-05 evaluator to handle tab-level conditions, and DynamicForm to filter `validTabs` based on visibility state.

**Dependencies:** TS-05, DynamicForm.vue `validTabs` computed (already exists, just needs condition filtering added).

**Confidence:** HIGH — The data structure already has tabs array; adding `show_when` at tab level is a natural extension.

---

### DIFF-05: Completeness Progress Indicator (Visibility-Aware)

**What:** Progress bar or section completion badges that correctly account for conditional fields — hidden fields don't count as "missing."

**Value proposition:** Curators often want to know "how complete is this curation?" before submitting. The existing `completeness_score` in `SchemaValidationResult` does not account for conditional fields, causing misleading "X% complete" values.

**Example:** A curation with MOI = "AD" (not "Other") should show 100% complete even though `moi_notes` is empty — because that field is hidden and doesn't apply.

**Complexity:** Medium — Requires visibility-aware completeness calculation in both `schema_validator.py` (backend) and optionally in a new frontend composable.

**Dependencies:** TS-01, TS-02, `schema_validator.py` (completeness calculation), ScoreDisplay component.

**Confidence:** MEDIUM — Pattern is clear; exact UX for displaying completeness needs design decision.

---

## Anti-Features

Things to deliberately NOT build. These are either too complex for this milestone, architecturally risky, or actively harmful to the curation workflow.

### AF-01: Programmatic/Expression Conditions in Schema (JavaScript in JSON)

**What:** Allowing arbitrary JavaScript expressions or functions as visibility/validation conditions stored in the schema JSON.

**Why avoid:** This is an XSS and code injection vector. An admin storing malicious JavaScript in a schema definition would execute in all curators' browsers. Even "safe" approaches (sandboxed eval) are complex and error-prone.

**Instead:** Use a structured DSL (operator + value pairs, as shown in TS-05 and DIFF-01). Cover 95% of use cases safely. Flag for "custom rule plugins" only if genuinely needed later with proper security review.

**Reference:** Clinical data systems like REDCap use a structured expression language (not arbitrary JS) for exactly this reason.

---

### AF-02: Bidirectional Field Dependencies (Circular Conditions)

**What:** Field A's visibility depends on Field B, and Field B's visibility depends on Field A.

**Why avoid:** Creates infinite evaluation loops. Dependency graphs require DAG (directed acyclic graph) structure — cycles break topological evaluation order. Detecting and gracefully handling cycles requires significant complexity (cycle detection, error reporting to schema authors).

**Instead:** Schema authors must define one-directional dependencies. Add cycle detection to schema validation with a clear error: "Field B cannot depend on Field A when A already depends on B." Detect at schema load time, not at runtime.

---

### AF-03: Runtime Condition Editing by Curators

**What:** Allowing curators to modify the visibility rules or validation conditions of a form while filling it out.

**Why avoid:** Schema configuration is institutional. ClinGen SOP conditions are defined by expert panels, not individual curators. Allowing per-session overrides undermines data integrity and reproducibility. This is the same reason the project scope excludes "Client-side schema editing."

**Instead:** Admin-only schema editing (existing SchemaEditor.vue and SchemaManagement.vue already handle this appropriately).

---

### AF-04: Full JSON Schema If/Then/Else (Draft-07 Conditional Keywords)

**What:** Implementing the full JSON Schema `if`/`then`/`else` conditional keywords for validation.

**Why avoid:** The Gene Curator schema validation system uses a custom JSONB schema format (not JSON Schema Draft-07 directly). The existing `schema_validator.py` would need significant rework to support full JSON Schema conditionals. The custom DSL approach is already working and sufficient for Gene Curator's needs.

**Instead:** Use the custom condition DSL already emerging in the schema data (`show_when`, `conditional_required`). Extend this consistently rather than migrating to JSON Schema Draft-07 semantics.

**Note:** The backend already generates JSON Schema from field definitions via `generate_json_schema()`, but this is for downstream consumption (not internal validation). These are separate concerns.

---

### AF-05: Real-Time Multi-Curator Conflict Resolution for Conditional Fields

**What:** Detecting and resolving conflicts when two curators simultaneously edit a form and their conditional field states diverge.

**Why avoid:** Real-time collaboration is explicitly out of scope for v0.1 and v0.2. The existing optimistic locking (`useOptimisticLocking.js`) handles concurrent edit conflicts at the record level. Extending this to field-level conditional state is a significant architectural effort.

**Instead:** Rely on existing optimistic locking. If two curators conflict, one gets a version conflict error and must refresh. This is acceptable for curation workflows where curators own their work.

---

### AF-06: AI-Assisted Field Suggestions Based on Conditional State

**What:** When a field becomes visible due to a condition, automatically suggest values based on other form data or external knowledge bases.

**Why avoid:** Explicitly out of scope per PROJECT.md: "AI-assisted field completion — Separate feature, out of scope for form infrastructure." This milestone is about infrastructure (the plumbing), not intelligence layered on top of it.

**Instead:** Mark as a future differentiator. Once conditional visibility is stable, AI suggestions can be added as a separate, opt-in overlay.

---

## Feature Dependencies

```
TS-05 (Visibility Evaluator)
  └─► TS-01 (Simple Visibility)
        └─► TS-02 (Conditional Required)
              └─► TS-03 (Hidden Field Data Handling)

TS-05 + TS-01 ──► DIFF-01 (Operator Conditions)
TS-01 + TS-05 ──► DIFF-02 (Cascading Select)
TS-01         ──► DIFF-04 (Tab/Section Visibility)
DIFF-02       ──► DIFF-03 (Auto-Population, Approach A)
TS-01 + TS-02 ──► DIFF-05 (Visibility-Aware Completeness)

TS-04 (Cross-Field Date Validation) — independent, can start in parallel
```

**Minimum viable set:** TS-05 → TS-01 → TS-02 → TS-03. These four make the existing precuration schema work correctly.

---

## Clinical/Scientific Form-Specific Considerations

These are not generic form platform concerns — they are specific to clinical genetics curation systems.

### Readonly Inherited Fields

Fields marked `"readonly": true` in the schema (like entity_definition fields inherited from precuration) must be visible but non-interactive. They can appear in conditional visibility evaluation as source values, but not as targets of auto-population rules. The existing `disabled` prop in `DynamicField.vue` handles this for the UI; the condition evaluator should still read their values.

### Scoring Integrity with Conditional Fields

When a conditional field becomes hidden, its scoring contribution should be zeroed out, not just visually hidden. The ClinGen scoring engine in `backend/app/scoring/` calculates scores from `evidence_data`. If a field's value is excluded from the submitted payload (TS-03), the scoring engine naturally re-calculates correctly. No special handling needed IF payload exclusion is implemented correctly.

### Validation Context: Backend Must Mirror Frontend Conditions

The most common pitfall in conditional validation: frontend hides a field, user submits, backend fails with "required field missing." This is the OWASP input validation principle: backend is the authoritative validator.

**Implementation requirement:** Backend `schema_validator.py` must receive the same condition context and evaluate visibility before checking required fields. The condition evaluator logic must be duplicated (or extracted to a shared format) between Python backend and JavaScript frontend.

**Practical approach:** The Python backend already has a conditions evaluator for scoring (`conditions` arrays in classification rules). The same condition evaluation pattern can be applied to field visibility.

### Form State Persistence During Workflow Transitions

Gene Curator curations move through workflow states (Draft → Submitted → In Review → Active). Conditional field values that exist in the JSONB `evidence_data` must not be silently dropped during state transitions. Backend `schema_validator.py` should validate with the same visibility rules regardless of workflow state.

### Audit Trail for Conditional Fields

When a field value is present in `evidence_data` but the field is currently hidden (because the triggering condition is no longer true), auditors reviewing historical curations must still see that value with context. Design recommendation: store all values in JSONB (never auto-delete), but display historically with a "(now hidden)" indicator in read-only views.

---

## MVP Recommendation

For this milestone, implement in this order:

**Phase 1 — Make Existing Schema Work:**
1. TS-05: `useFieldVisibility` composable (2-3 days)
2. TS-01: Wire visibility into DynamicField/TabContent (1 day)
3. TS-02: Conditional required in useValidationRules + backend (1-2 days)
4. TS-03: Payload exclusion for hidden fields (0.5 days)

**Phase 2 — Cross-Field Validation:**
5. TS-04: Cross-field validation DSL + evaluator (2-3 days)

**Phase 3 — Dependencies and Differentiators:**
6. DIFF-01: Operator conditions in evaluator (1 day, extends TS-05)
7. DIFF-02: Cascading select options (2 days)
8. DIFF-04: Tab/section visibility (1 day, extends TS-05)
9. DIFF-03: Auto-population via events (2-3 days)
10. DIFF-05: Visibility-aware completeness (1 day)

**Defer beyond this milestone:**
- AI-assisted suggestions (AF-06 rationale)
- Real-time collaboration (AF-05 rationale)
- Full JSON Schema if/then/else (AF-04 rationale)

---

## Confidence Assessment

| Feature | Confidence | Basis |
|---------|-----------|-------|
| TS-01 Simple visibility | HIGH | Pattern already in schema data; Vue 3 reactivity is ideal for this |
| TS-02 Conditional required | HIGH | Pattern already in validation_rules; standard in all form frameworks |
| TS-03 Data handling policy | MEDIUM-HIGH | Policy is a product decision; implementation is clear |
| TS-04 Cross-field validation | HIGH | Standard in REDCap, VeeValidate, form frameworks; DSL design is the work |
| TS-05 Visibility evaluator | HIGH | Standard composable pattern; confirmed by Vueform docs |
| DIFF-01 Operators | HIGH | Trivial extension of TS-05; ecosystem consensus on operator set |
| DIFF-02 Cascading select | HIGH | Standard in all form platforms; schema model is clear |
| DIFF-03 Auto-population | MEDIUM | Approach A is clear; Approach B complexity warrants deferring |
| DIFF-04 Tab visibility | HIGH | Natural extension of TS-05 to tab-level |
| DIFF-05 Completeness | MEDIUM | Backend integration complexity; depends on TS-02 correctness |

---

## Sources

- [Vueform Conditional Rendering Documentation](https://vueform.com/docs/conditional-rendering) — Operator set, data handling for hidden fields, schema-driven conditions
- [REDCap Branching Logic Guide](https://www.ctsi.ufl.edu/wordpress/files/2017/06/Branching-Logic-in-REDCap-%E2%80%93-How.pdf) — Clinical EDC skip logic patterns
- [Hidden vs. Disabled in UX — Smashing Magazine](https://www.smashingmagazine.com/2024/05/hidden-vs-disabled-ux/) — UX principles for field hiding
- [VeeValidate Cross-Field Validation](https://vee-validate.logaretm.com/v3/advanced/cross-field-validation.html) — Cross-field validation patterns
- [JSON Schema Conditionals](https://json-schema.org/understanding-json-schema/reference/conditionals) — if/then/else semantics (used to inform what NOT to implement)
- [OWASP Input Validation Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Input_Validation_Cheat_Sheet.html) — Backend enforcement requirement
- [Hike Medical: Schema-Driven Dynamic Forms](https://medium.com/hike-medical/scaling-clinical-workflows-with-schema-driven-dynamic-forms-091f89cc730f) — Clinical workflow form patterns
- Gene Curator codebase: `016_seed_precuration_schema.sql`, `DynamicForm.vue`, `DynamicField.vue`, `schema_validator.py`, `useValidationRules.js`
