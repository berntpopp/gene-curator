# Requirements: Gene Curator v0.2 Form Intelligence

**Defined:** 2026-02-28
**Core Value:** Every scope can use their own curation methodology with dynamically rendered forms that adapt to any schema definition.

## v0.2 Requirements

Requirements for Form Intelligence milestone. Fields react to each other through conditional visibility, cross-field validation, and cascading dependencies.

### Conditional Visibility

- [ ] **COND-01**: Fields show/hide based on other field values (conditional visibility)
- [ ] **COND-02**: Visibility rules defined in field_definition.visibility property
- [ ] **COND-03**: Condition syntax unified across all schemas (canonical format replacing legacy show_when and condition strings)
- [ ] **COND-04**: Hidden field values cleared to null and excluded from form submission
- [ ] **COND-05**: DAG cycle detection prevents circular field dependencies

### Cross-Field Validation

- [ ] **XVAL-01**: Validation rules can reference other field values (cross-field validation)
- [ ] **XVAL-02**: Cross-field rules defined in schema validation_rules
- [ ] **XVAL-03**: Backend validation skips required checks for fields hidden by visibility rules

### Field Dependencies

- [ ] **DEPS-01**: Cascading selects (field B options depend on field A value)
- [ ] **DEPS-02**: Auto-population (selecting MONDO ID populates disease_name)

## Future Requirements

Deferred to later milestones. Tracked but not in current roadmap.

### Advanced Visibility

- **VIS-01**: Tab/section-level visibility (entire tabs hide when no visible fields)
- **VIS-02**: Visibility-aware completeness indicator (progress bar excludes hidden fields)
- **VIS-03**: Configurable clear-on-hide behavior per field (null vs retain)

### Extended Dependencies

- **EDEP-01**: Multi-field cascading chains (A → B → C)
- **EDEP-02**: Auto-population from additional ontology APIs (HPO, OMIM)

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| json-logic-js dependency | Defer until a schema needs compound operators (and/or/greater-than); simple equality sufficient for current schemas |
| Programmatic JS in schema conditions | XSS risk; conditions must be declarative JSON only |
| Bidirectional field dependencies | Infinite loop risk; dependencies must be unidirectional |
| AI-assisted field completion | Separate feature per PROJECT.md |
| Schema editor for visibility rules | Admin manages via database; UI editor is a separate product |
| Real-time collaboration on forms | Out of scope for v1 |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| COND-01 | Pending | Pending |
| COND-02 | Pending | Pending |
| COND-03 | Pending | Pending |
| COND-04 | Pending | Pending |
| COND-05 | Pending | Pending |
| XVAL-01 | Pending | Pending |
| XVAL-02 | Pending | Pending |
| XVAL-03 | Pending | Pending |
| DEPS-01 | Pending | Pending |
| DEPS-02 | Pending | Pending |

**Coverage:**
- v0.2 requirements: 10 total
- Mapped to phases: 0
- Unmapped: 10 ⚠️

---
*Requirements defined: 2026-02-28*
*Last updated: 2026-02-28 after initial definition*
