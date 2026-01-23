# Research Summary: Dynamic Form Integration

**Domain:** Vue 3 + Vuetify 3 Dynamic Schema-Driven Forms
**Researched:** 2026-01-22
**Overall Confidence:** HIGH

## Executive Summary

The Gene Curator project has a solid foundation for dynamic schema-driven forms. The backend already provides comprehensive JSON Schema generation, field-level and form-level validation, live score calculation, and business rule enforcement. The frontend has working `DynamicForm` and `DynamicField` components that handle 6+ field types and integrate with the validation store.

**The work is integration, not construction.** No new dependencies are needed. The existing Vue 3 + Vuetify 3 + Pinia + VueUse stack provides all required capabilities.

**Critical insight:** The `ClinGenCurationForm.vue` demonstrates the target UX (tabbed interface, live scoring sidebar, keyboard shortcuts). The task is making this pattern schema-driven rather than hardcoded.

## Key Findings

**Stack:** Keep existing (Vue 3.4, Vuetify 3.9, Pinia 2.1, VueUse 14.1) - all current versions, no upgrades needed.

**Architecture:** Two-layer validation pattern - Vuetify native `:rules` for instant feedback, backend `/validation/validate-evidence` for comprehensive validation including business rules and live scores.

**Critical insight:** Backend `SchemaValidationResult.score_calculations` already provides live scoring data; the UI just needs to display it.

## Implications for Roadmap

Based on research, suggested phase structure:

1. **Phase 1: Wire DynamicForm to PrecurationFormView**
   - Addresses: Precuration forms currently hardcoded
   - Avoids: Regression by keeping existing ClinGen-specific form path
   - Rationale: PrecurationFormView is simpler, lower risk starting point

2. **Phase 2: Add Dynamic Tab Rendering**
   - Addresses: `ui_configuration.sections` not being used
   - Builds: `DynamicTabs.vue` component that reads schema configuration
   - Pattern: Copy v-tabs/v-window pattern from ClinGenCurationForm.vue

3. **Phase 3: Enhance DynamicField for Remaining Types**
   - Addresses: Some field types (pmid, hgnc_id, autocomplete) need specialized components
   - Integration: Connect to existing autocomplete components (MONDOAutocomplete, OMIMAutocomplete, etc.)

4. **Phase 4: Live Scoring Display**
   - Addresses: Score calculations available but not displayed in generic forms
   - Pattern: Copy ScoreSummary sidebar from ClinGenCurationForm

**Phase ordering rationale:**
- Start with precuration (simpler, fewer fields, no scoring)
- Add structure (tabs) before field complexity
- Scoring last because backend already calculates; UI display is straightforward

**Research flags for phases:**
- Phase 1: Standard patterns, unlikely to need research
- Phase 2: Standard patterns, unlikely to need research
- Phase 3: May need research for specialized autocomplete integration
- Phase 4: Standard patterns, backend already implemented

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Verified against package.json, all versions current |
| Existing Components | HIGH | Read and analyzed DynamicForm.vue, DynamicField.vue, SchemaDrivenCurationForm.vue |
| Backend Integration | HIGH | Read validation_service.py, schema_validator.py, API endpoints |
| Vuetify Patterns | HIGH | Already used in codebase (ClinGenCurationForm tabs, validation rules) |

## Field Metadata Handling

### Problem
Dynamic forms need more than type/validation: icons, hints, tooltips, help links. Current `field_definitions` lack this UI metadata.

### Solution: Inline Extension Pattern
Based on industry best practices ([JSON Forms](https://jsonforms.io/docs/uischema/), [react-jsonschema-form](https://rjsf-team.github.io/react-jsonschema-form/docs/api-reference/uiSchema/), [VJSF](https://github.com/koumoul-dev/vuetify-jsonschema-form), [vue3-schema-forms](https://github.com/MaciejDybowski/vue3-schema-forms)):

Extend field definitions with UI metadata properties:

```json
{
  "proband_count": {
    "type": "integer",
    "label": "Proband Count",
    "icon": "mdi-account-multiple",
    "hint": "Count only unrelated probands",
    "tooltip": "Include probands from independent families...",
    "helpUrl": "https://clinicalgenome.org/docs/proband-counting",
    "required": true,
    "min": 0
  }
}
```

### UI Metadata Properties

| Property | Vuetify Binding | Purpose |
|----------|-----------------|---------|
| `icon` | `:prepend-icon` | Field icon (MDI) |
| `hint` | `:hint` + `persistent-hint` | Persistent help text |
| `tooltip` | `v-tooltip` wrapper | Hover information |
| `helpUrl` | Custom icon + click handler | Link to docs |
| `appendIcon` | `:append-icon` | Icon at end of field |

See `.planning/research/METADATA.md` for full implementation details.

## Gaps to Address

1. **UI Configuration Schema:** Backend schemas may not have `ui_configuration.sections` fully populated. Need to verify/update schema seed data.

2. **Field Type Coverage:** DynamicField handles core types but specialized types (pmid, hgnc_id) may need wiring to existing autocomplete components.

3. **Form State Persistence:** Draft auto-save composable exists (`useFormRecovery`) but may need integration with DynamicForm.

4. **Field Metadata:** Current `field_definitions` lack UI metadata (icons, hints, tooltips). Need to extend DynamicField to support these properties.

## Files Created

| File | Purpose |
|------|---------|
| `.planning/research/SUMMARY.md` | This executive summary |
| `.planning/research/STACK.md` | Technology recommendations with rationale |

## Ready for Roadmap

Research complete. The integration path is clear:
1. Existing components cover 70-80% of needs
2. No new dependencies required
3. Patterns already demonstrated in ClinGenCurationForm
4. Backend validation/scoring infrastructure complete

Proceeding to roadmap creation.
