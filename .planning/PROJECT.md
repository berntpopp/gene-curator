# Gene Curator - Schema-Driven Forms

## What This Is

A gene-disease validity curation platform that enables clinical genetics teams to curate gene-disease relationships using configurable methodologies (ClinGen SOP v11, GenCC, institutional approaches). The frontend now renders forms dynamically from database schema configuration, enabling any scope to use their own curation methodology without code changes.

## Core Value

**Every scope can use their own curation methodology with dynamically rendered forms that adapt to any schema definition.**

When a curator opens a precuration or curation form, the UI renders from the database schema configuration - not from hardcoded Vue components. Kidney-genetics uses ClinGen while cardio-genetics uses GenCC without code changes.

## Requirements

### Validated

- Schema-agnostic backend foundation with JSONB `field_definitions` - v0.1
- 13+ field types supported (text, number, boolean, date, array, object, select, etc.) - v0.1
- 4 schema types configured (ClinGen_SOP_v11, GenCC_Classification, Qualitative_Assessment, Standard_Precuration) - v0.1
- Multi-stage workflow (Entry -> Precuration -> Curation -> Review -> Active) - v0.1
- Scope-based organization with workflow pairs per scope - v0.1
- DynamicForm renders fields from schema `field_definitions` - v0.1
- DynamicForm renders tabs/sections from schema `ui_configuration` - v0.1
- ClinGen bypass removed from SchemaDrivenCurationForm - v0.1
- Score calculation works for any schema type (ClinGen, GenCC, Qualitative) - v0.1
- Form validation runs against schema rules - v0.1
- Component registry maps 5 specialized evidence components - v0.1
- PrecurationFormView renders from schema field_definitions - v0.1
- Feature flag infrastructure for gradual DynamicForm rollout - v0.1

### Active

- [ ] **COND-01**: Fields show/hide based on other field values (conditional visibility)
- [ ] **COND-02**: Visibility rules defined in field_definition.visibility property
- [ ] **XVAL-01**: Validation rules can reference other field values (cross-field validation)
- [ ] **XVAL-02**: Cross-field rules defined in schema validation_rules
- [ ] **DEPS-01**: Cascading selects (field B options depend on field A value)
- [ ] **DEPS-02**: Auto-population (selecting MONDO ID populates disease_name)

### Out of Scope

- New schema types - Focus on using existing 4 schemas; new types via admin UI later
- Schema editor UI - Existing admin UI works; this initiative focused on form rendering
- Backend changes - Backend schema system is complete; frontend integration was the focus
- Mobile app - Web-first; mobile later
- Real-time collaboration - Out of scope for v1
- Drag-and-drop form builder - Schemas defined by admin via database; separate product
- Custom component registration at runtime - Security risk, debugging nightmare
- Client-side schema editing - Schemas are institutional configurations
- Offline-first / IndexedDB - Curation done online; localStorage recovery sufficient
- AI-assisted field completion - Separate feature, out of scope for form infrastructure

## Context

**Current State (as of 2026-01-23, after v0.1 milestone):**

1. **Backend ready**: JSONB `field_definitions` in `curation_schemas` table with 4 configured schemas
2. **Frontend complete**: DynamicForm renders all forms schema-driven
3. **Scoring working**: ClinGen, GenCC, and Qualitative engines all display live scores
4. **Tests passing**: 428 frontend tests, 101 backend tests all green

**Tech Stack:**
- Frontend: Vue 3 + Vuetify 3 + Pinia (55,478 LOC)
- Backend: FastAPI + SQLAlchemy + PostgreSQL
- Forms: Schema-driven via DynamicForm/DynamicField components

**Architecture:**
- Component registry pattern for specialized evidence fields
- useValidationRules composable for schema-driven client validation
- useSchemaScoring composable for engine-agnostic scoring
- Feature flag (use_dynamic_form) for gradual rollout control

## Constraints

- **Tech stack**: Vue 3 + Vuetify 3 + Pinia (no framework changes)
- **Backward compatibility**: Existing ClinGen curations continue to work
- **Testing**: Must pass existing test suite
- **Performance**: Form render time under 500ms for schemas with 50+ fields

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Wire DynamicForm to existing views | Components existed; avoided rewrite | Good - shipped in 2 days |
| Remove ClinGen bypass | Bypass defeated schema-driven design | Good - all schemas use same code |
| Use ui_configuration for tabs | Already in schema; just needed frontend reading | Good - clean architecture |
| Keep backend unchanged | Backend was complete and tested | Good - avoided scope creep |
| Component registry pattern | Explicit mapping for specialized components | Good - clear, extensible |
| Feature flag at schema level | Per-schema rollout control | Good - safe gradual rollout |
| Auto-migration on load | Non-destructive, immediate, simple | Good - no data coordination needed |
| Schema-agnostic scoring | No hardcoded engine checks | Good - new engines work automatically |
| Sticky sidebar lg+ only | Better mobile UX | Good - follows Vuetify conventions |

---
*Last updated: 2026-01-23 after v0.1 milestone completion*
*Core focus: Foundation complete. Next: conditional visibility, cross-field validation*
