# ARCHITECTURE.md - Integration Architecture

**Project:** Gene Curator - Dynamic Form Integration
**Researched:** 2026-01-22
**Confidence:** HIGH (based on direct codebase analysis)

## Current State

### The Problem

The Gene Curator platform has a well-designed schema-agnostic backend with JSONB `field_definitions` and `ui_configuration` in the `curation_schemas` table, but the frontend forms are hardcoded for ClinGen SOP v11. This prevents other scopes (kidney-genetics, cardio-genetics, etc.) from using their own curation methodologies.

### Existing Component Inventory

| Component | Location | Lines | Current State |
|-----------|----------|-------|---------------|
| `DynamicForm.vue` | `frontend/src/components/dynamic/` | 317 | **Functional** - accepts schemaId, renders fields, has v-model, validation, scoring display |
| `DynamicField.vue` | `frontend/src/components/dynamic/` | 402 | **Functional** - handles 14+ field types, recursive for nested objects/arrays |
| `PrecurationFormView.vue` | `frontend/src/views/curation/` | 777 | **Hardcoded** - 100% ClinGen panels, ignores fetched `precurationSchemaId` |
| `ClinGenCurationForm.vue` | `frontend/src/components/clingen/` | 595 | **Hardcoded** - 5 fixed tabs, ClinGen-specific scoring logic |
| `SchemaDrivenCurationForm.vue` | `frontend/src/components/forms/` | 641 | **Partial** - Has ClinGen bypass (`isClinGenSchema` check at line 199-201), falls back to hardcoded form |
| `CurationFormView.vue` | `frontend/src/views/curation/` | 323 | **Router wrapper** - Schema resolution logic, delegates to `SchemaDrivenCurationForm` |
| `PrecurationForm.vue` | `frontend/src/components/forms/` | 663 | **Legacy** - Different hardcoded form, not schema-driven |

### Data Flow (Current)

```
Route params (scopeId, geneId)
        |
        v
CurationFormView.vue
        |
        +--> Resolves schemaId (5-level priority chain)
        |    1. Existing curation's schema
        |    2. User-selected schema
        |    3. Route query param
        |    4. Scope's default workflow pair
        |    5. Single available schema auto-select
        |
        v
SchemaDrivenCurationForm.vue
        |
        +--> Check: isClinGenSchema? (name includes 'clingen')
        |
        |   YES --> ClinGenCurationForm.vue (HARDCODED)
        |                   |
        |                   +--> 5 fixed tabs with hardcoded sections
        |                   +--> Hardcoded scoring logic (calculateGeneticScore/calculateExperimentalScore)
        |
        |   NO --> DynamicForm.vue (SCHEMA-DRIVEN)
                           |
                           +--> validationStore.generateJsonSchema(schemaId)
                           +--> Renders jsonSchema.properties as DynamicField
                           +--> BUT: No tab support, no ui_configuration reading
```

### Key Architecture Insights

**1. DynamicForm Does NOT Read ui_configuration**

Current DynamicForm (line 167):
```javascript
const jsonSchema = computed(() => validationStore.getJsonSchema(props.schemaId))
```

This fetches a JSON Schema from the validation endpoint, not the raw schema with `ui_configuration`. The `ui_configuration` contains tab definitions, but DynamicForm ignores them.

**2. ui_configuration Structure (from database)**

```json
{
  "layout": {
    "type": "tabs",
    "tabs": [
      {
        "id": "summary",
        "name": "Summary",
        "icon": "mdi-file-document-outline",
        "sections": [
          {"name": "Classification Summary", "fields": ["evidence_summary"]},
          {"name": "Score Summary", "component": "ScoreSummary"}
        ]
      },
      {
        "id": "genetic",
        "name": "Genetic Evidence",
        "icon": "mdi-dna",
        "show_score_badge": true,
        "sections": [...]
      }
    ]
  },
  "components": {...},
  "keyboard_shortcuts": {...},
  "quick_actions": [...]
}
```

**3. ClinGen Bypass Mechanism**

In `SchemaDrivenCurationForm.vue` (line 199-201):
```javascript
const isClinGenSchema = computed(() => {
  const schemaName = schema.value?.name?.toLowerCase() || ''
  return schemaName.includes('clingen') || schemaName.includes('sop')
})
```

This check defeats the entire purpose of schema-driven forms. ANY schema named with "clingen" or "sop" falls back to hardcoded rendering.

**4. Schema Store Returns Full Schema**

The `schemasStore.fetchSchemaById(id)` returns the complete schema including `ui_configuration` and `field_definitions`, but neither `SchemaDrivenCurationForm` nor `DynamicForm` use this data for layout.

## Target State

### Goal Architecture

```
Route params (scopeId, geneId)
        |
        v
CurationFormView.vue (unchanged - good schema resolution)
        |
        v
SchemaDrivenCurationForm.vue
        |
        +--> NO ClinGen bypass
        |
        +--> Fetch full schema (field_definitions + ui_configuration)
        |
        v
TabDrivenForm.vue (NEW or enhanced DynamicForm)
        |
        +--> Read ui_configuration.layout.tabs[]
        |
        +--> For each tab:
        |    +--> Render <v-tab> with name, icon, score badge
        |    +--> For each section in tab:
        |         +--> If section has "fields": render DynamicField for each
        |         +--> If section has "component": render registered component
        |
        v
DynamicField.vue (unchanged - already handles 14+ field types)
```

### Component Changes Summary

| Component | Change Type | What Changes |
|-----------|-------------|--------------|
| `DynamicForm.vue` | **MODIFY** | Add tab/section layout support from ui_configuration |
| `SchemaDrivenCurationForm.vue` | **MODIFY** | Remove `isClinGenSchema` bypass, pass ui_configuration to DynamicForm |
| `ClinGenCurationForm.vue` | **KEEP** | Keep as fallback for edge cases, but stop auto-detecting |
| `CurationFormView.vue` | **KEEP** | Schema resolution logic is good |
| `PrecurationFormView.vue` | **MODIFY** | Replace hardcoded panels with DynamicForm |
| `DynamicField.vue` | **KEEP** | Already functional for all field types |
| New: Component registry | **CREATE** | Map component names to Vue components (ScoreSummary, LumpingSplittingSection) |

## Integration Strategy

### Recommended: Incremental Refactor

**Why not Big Bang:**
- Existing ClinGen curations must keep working (constraint from PROJECT.md)
- 777-line `PrecurationFormView.vue` is too risky to rewrite at once
- Need to verify schema data flows correctly before removing bypasses

**Incremental Approach:**

1. **Phase 1: Wire ui_configuration to DynamicForm** (LOW RISK)
   - DynamicForm accepts optional `uiConfiguration` prop
   - If present, renders tabs/sections from ui_configuration
   - If absent, falls back to flat field rendering (current behavior)
   - No existing code breaks

2. **Phase 2: Pass ui_configuration from SchemaDrivenCurationForm** (LOW RISK)
   - Fetch full schema including ui_configuration
   - Pass to DynamicForm
   - ClinGen bypass still in place (safety net)

3. **Phase 3: Test with non-ClinGen schemas** (MEDIUM RISK)
   - Use GenCC or custom schema with a test scope
   - Verify tabs render correctly
   - Fix any field path issues (nested fields like "genetic_evidence.case_level")

4. **Phase 4: Remove ClinGen bypass** (MEDIUM RISK)
   - Remove `isClinGenSchema` check
   - ClinGen schemas render through DynamicForm like any other
   - Keep ClinGenCurationForm.vue as dead code initially (can delete later)

5. **Phase 5: Refactor PrecurationFormView** (MEDIUM-HIGH RISK)
   - Simplest approach: Replace hardcoded panels with single DynamicForm
   - Precuration schema has its own field_definitions
   - May need ui_configuration for precuration schemas too

## Data Flow

### Schema Data Flow (Target)

```
1. CurationFormView.vue mounts
        |
        v
2. schemasStore.fetchSchemaById(resolvedSchemaId)
        |
        +--> API: GET /api/v1/schemas/curation-schemas/{id}
        |
        +--> Returns:
             {
               id: "...",
               name: "ClinGen_SOP_v11",
               field_definitions: { ... },     <-- Field types and validation
               ui_configuration: { ... },      <-- Tab layout
               validation_rules: { ... },      <-- Business rules
               scoring_configuration: { ... }  <-- Score calculation
             }
        |
        v
3. SchemaDrivenCurationForm.vue receives schema
        |
        +--> Extract: schema.field_definitions
        +--> Extract: schema.ui_configuration
        |
        v
4. DynamicForm.vue (enhanced)
        |
        +--> Props: { schemaId, uiConfiguration, fieldDefinitions, initialData }
        |
        +--> If uiConfiguration?.layout?.type === 'tabs':
        |         Render <v-tabs> from uiConfiguration.layout.tabs
        |    Else:
        |         Render flat field list (backward compatible)
        |
        v
5. For each tab.section.fields[]:
        |
        +--> Resolve field path (e.g., "genetic_evidence.case_level.autosomal_dominant_or_x_linked")
        +--> Get field definition from fieldDefinitions
        +--> Render DynamicField with field schema
        |
        v
6. For each tab.section.component:
        |
        +--> Look up in component registry
        +--> Render registered Vue component (ScoreSummary, LumpingSplittingSection, etc.)
```

### Component Registry Pattern

```javascript
// componentRegistry.js
import ScoreSummary from '@/components/evidence/ScorePreview.vue'
import LumpingSplittingSection from '@/components/clingen/sections/LumpingSplittingSection.vue'

export const componentRegistry = {
  'ScoreSummary': ScoreSummary,
  'LumpingSplittingSection': LumpingSplittingSection,
  // Add more as needed
}

// In DynamicForm.vue
import { componentRegistry } from '@/utils/componentRegistry'

// When section has "component" key:
const DynamicComponent = componentRegistry[section.component]
// Render: <component :is="DynamicComponent" v-bind="sectionProps" />
```

## Build Order

### Phase 1: Foundation (1-2 days)

**Order matters - each step enables the next:**

1. **Create component registry** (`frontend/src/utils/componentRegistry.js`)
   - Map: component name string -> Vue component
   - Start with existing: ScoreSummary, ScorePreview

2. **Modify DynamicForm.vue to accept uiConfiguration prop**
   - Add prop: `uiConfiguration: { type: Object, default: null }`
   - Conditional rendering: tabs if ui_configuration, flat otherwise
   - Keep existing flat rendering as default (backward compatible)

3. **Add tab rendering logic to DynamicForm**
   - Parse `uiConfiguration.layout.tabs`
   - Render `<v-tabs>` with `<v-tab>` for each tab
   - Render `<v-window>` with `<v-window-item>` for tab content

4. **Add section rendering within tabs**
   - For each section in tab.sections:
     - If `fields`: render DynamicField for each field path
     - If `component`: render from registry

### Phase 2: Integration (1-2 days)

5. **Modify SchemaDrivenCurationForm to pass ui_configuration**
   - After fetching schema, extract ui_configuration
   - Pass to DynamicForm: `<DynamicForm :ui-configuration="schema.ui_configuration" />`
   - Keep ClinGen bypass active for safety

6. **Add field path resolution**
   - Support nested paths like "genetic_evidence.case_level"
   - Resolve from field_definitions object
   - Handle missing paths gracefully

7. **Test with GenCC schema**
   - Create test scope with GenCC workflow pair
   - Open curation form
   - Verify tabs render from GenCC's ui_configuration

### Phase 3: Bypass Removal (1 day)

8. **Remove ClinGen bypass in SchemaDrivenCurationForm**
   - Delete `isClinGenSchema` computed property
   - Delete conditional rendering of ClinGenCurationForm
   - All schemas now flow through DynamicForm

9. **Verify ClinGen curations still work**
   - Test existing ClinGen curation edit
   - Test new ClinGen curation create
   - Verify scoring displays correctly

### Phase 4: Precuration (1-2 days)

10. **Add ui_configuration to precuration schema (if missing)**
    - Check database for precuration schema's ui_configuration
    - Add expansion panel structure if not present

11. **Refactor PrecurationFormView**
    - Replace 777-line hardcoded form with DynamicForm
    - Pass precuration schema's field_definitions and ui_configuration
    - Keep header with gene info, external links

## Backward Compatibility

### Strategy: Feature Detection, Not Schema Detection

**Old approach (bad):**
```javascript
// Hardcoded schema name check
if (schema.name.includes('clingen')) {
  renderClinGenForm()
}
```

**New approach (good):**
```javascript
// Feature detection
if (uiConfiguration?.layout?.type === 'tabs') {
  renderWithTabs()
} else {
  renderFlat()
}
```

### Existing Curation Protection

| Scenario | What Happens |
|----------|--------------|
| Open existing ClinGen curation | Schema fetched, ui_configuration has tabs, renders with tabs |
| Create new ClinGen curation | Same as above |
| Open existing GenCC curation | Schema fetched, ui_configuration defines layout, renders accordingly |
| Schema missing ui_configuration | Falls back to flat rendering (current DynamicForm behavior) |
| Tab references missing field | Field not rendered (graceful degradation with console warning) |

### Data Migration: None Required

Existing curations store `evidence_data` as JSONB. The field paths in `evidence_data` match the field names in `field_definitions`. No data migration needed - only frontend rendering changes.

## Risk Assessment

| Change | Risk | Mitigation |
|--------|------|------------|
| Add tab support to DynamicForm | LOW | Additive change, default to flat rendering |
| Pass ui_configuration to DynamicForm | LOW | Optional prop, no change if not passed |
| Remove ClinGen bypass | MEDIUM | Test thoroughly with ClinGen curations before deploying |
| Refactor PrecurationFormView | MEDIUM-HIGH | Do last, after curation forms proven stable |
| Component registry | LOW | Simple mapping, can add components incrementally |

## Files to Modify

| File | Changes |
|------|---------|
| `frontend/src/components/dynamic/DynamicForm.vue` | Add uiConfiguration prop, tab rendering, section rendering |
| `frontend/src/components/forms/SchemaDrivenCurationForm.vue` | Pass ui_configuration to DynamicForm, eventually remove ClinGen bypass |
| `frontend/src/utils/componentRegistry.js` | New file - component name -> component mapping |
| `frontend/src/views/curation/PrecurationFormView.vue` | Later - replace hardcoded panels with DynamicForm |

## Files to Keep Unchanged

| File | Reason |
|------|--------|
| `frontend/src/components/dynamic/DynamicField.vue` | Already handles all field types |
| `frontend/src/views/curation/CurationFormView.vue` | Schema resolution logic is correct |
| `frontend/src/stores/schemas.js` | Already fetches full schema |
| `frontend/src/api/schemas.js` | API layer is correct |
| Backend (all files) | Backend is complete (per PROJECT.md constraints) |

## Open Questions for Phase-Specific Research

1. **Scoring in DynamicForm**: DynamicForm displays `validationResult.score_calculations` but ClinGen needs specific breakdown (genetic vs experimental). Does ui_configuration's `show_score_badge: true` on tabs sufficient, or need more?

2. **Nested field path performance**: Fields like `genetic_evidence.case_level.autosomal_dominant_or_x_linked.predicted_or_proven_null[]` are deeply nested arrays. Need to verify DynamicField handles this correctly.

3. **Precuration schema ui_configuration**: Need to verify what's in the database. If missing tabs definition, may need database seed update.

4. **Component prop interface**: What props does LumpingSplittingSection expect? Need to match when rendering dynamically.

---

*Research based on direct codebase analysis. All file paths and line numbers verified against current source.*
