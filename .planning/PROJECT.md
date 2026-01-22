# Gene Curator - Schema-Driven Forms

## What This Is

A gene-disease validity curation platform that enables clinical genetics teams to curate gene-disease relationships using configurable methodologies (ClinGen SOP v11, GenCC, institutional approaches). Currently, the backend has a well-designed schema-agnostic system, but frontend forms are hardcoded for ClinGen SOP v11, preventing other scopes from using their own curation methodologies.

## Core Value

**Every scope can use their own curation methodology with dynamically rendered forms that adapt to any schema definition.**

When a curator opens a precuration or curation form, the UI must render from the database schema configuration - not from hardcoded Vue components. This enables kidney-genetics to use ClinGen while cardio-genetics uses GenCC without code changes.

## Requirements

### Validated

<!-- Shipped and confirmed valuable. -->

- Schema-agnostic backend foundation with JSONB `field_definitions`
- 13+ field types supported (text, number, boolean, date, array, object, select, multiselect, email, url, pmid, hgnc_id, score)
- 4 schema types configured in database (ClinGen_SOP_v11, GenCC_Classification, Qualitative_Assessment, Standard_Precuration)
- Multi-stage workflow (Entry → Precuration → Curation → Review → Active)
- Scope-based organization with workflow pairs (precuration_schema_id + curation_schema_id per scope)
- DynamicForm and DynamicField components exist and partially functional

### Active

<!-- Current scope. Building toward these. -->

- [ ] **FORM-01**: PrecurationFormView renders from schema `field_definitions` instead of hardcoded panels
- [ ] **FORM-02**: CurationFormView renders tabs/sections from schema `ui_configuration`
- [ ] **FORM-03**: Remove ClinGen detection bypass in SchemaDrivenCurationForm (currently falls back to hardcoded form when schema name includes 'clingen')
- [ ] **FORM-04**: DynamicForm receives schemaId prop and fetches/renders field definitions
- [ ] **FORM-05**: Score calculation works for any schema type, not just ClinGen
- [ ] **FORM-06**: Form validation runs against schema rules, not hardcoded patterns
- [ ] **FORM-07**: Tab rendering from ui_configuration.tabs array

### Out of Scope

<!-- Explicit boundaries. Includes reasoning to prevent re-adding. -->

- New schema types — Focus on using existing 4 schemas; new types can be added via admin UI later
- Schema editor UI — Existing admin UI works; this initiative focuses on form rendering
- Backend changes — Backend schema system is complete; this is a frontend integration task
- Mobile app — Web-first; mobile later
- Real-time collaboration — Out of scope for v1

## Context

**Current State (as of 2026-01-22):**

1. **Backend is ready**: JSONB `field_definitions` in `curation_schemas` table with 4 configured schemas
2. **Frontend is blocked**: Forms hardcoded for ClinGen SOP v11
3. **DynamicForm exists but unused**: Components at `frontend/src/components/dynamic/` are 70-80% complete but not wired to actual forms

**Key Files with Hardcoding:**

| File | Lines | Issue |
|------|-------|-------|
| `PrecurationFormView.vue` | 777 | 100% hardcoded ClinGen panels, loads `precurationSchemaId` but ignores it |
| `ClinGenCurationForm.vue` | ~500 | Hardcoded 5 tabs: Summary, Genetic Evidence, Experimental Evidence, Contradictory, Lumping & Splitting |
| `SchemaDrivenCurationForm.vue` | 641 | ClinGen bypass at line with `includes('clingen')` check |

**What Works:**
- DynamicForm.vue supports live scoring, validation, v-model binding
- DynamicField.vue handles 14 field types with recursive rendering
- Backend returns complete field definitions via `/api/v1/schemas/{id}`

**UX Pain Points (from Playwright exploration):**
- NAA10 curation displays ClinGen-specific scoring categories even though schema is configurable
- Schema View button in admin UI doesn't open modal (bug)
- All scopes show same form structure regardless of their workflow pair settings

## Constraints

- **Tech stack**: Vue 3 + Vuetify 3 + Pinia (no framework changes)
- **Backward compatibility**: Existing ClinGen curations must continue to work
- **No new dependencies**: Use existing DynamicForm/DynamicField components
- **Testing**: Must pass existing test suite; add tests for dynamic rendering
- **Performance**: Form render time must stay under 500ms for schemas with 50+ fields

## Current Milestone: v0.1 Dynamic Forms

**Goal:** Wire DynamicForm components to actual form views, eliminating frontend hardcoding so any scope can use their own curation methodology.

**Target features:**
- PrecurationFormView renders from schema field_definitions
- CurationFormView renders tabs/sections from schema ui_configuration
- Remove ClinGen detection bypass in SchemaDrivenCurationForm
- Score calculation works for any schema type
- Form validation runs against schema rules

## Key Decisions

<!-- Decisions that constrain future work. Add throughout project lifecycle. -->

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Wire DynamicForm to existing views | Components exist; avoid rewrite | — Pending |
| Remove ClinGen bypass | Bypass defeats the purpose of schema-driven design | — Pending |
| Use ui_configuration for tabs | Already in schema; just needs frontend reading | — Pending |
| Keep backend unchanged | Backend is complete and tested | — Pending |

---
*Last updated: 2026-01-22 after milestone v0.1 initialization*
*Core focus: Eliminate frontend hardcoding, wire DynamicForm to actual views*
