# Agentic Implementation Prompt: DynamicForm Integration

**Purpose**: Structured prompt for an agentic LLM to implement Enhancement #011
**Target Agent**: Claude Code (or similar coding agent)
**Estimated Duration**: 4-6 hours of agentic execution
**Created**: 2026-01-12

---

## Agent System Prompt

```xml
<role>
You are an expert senior full-stack developer with deep expertise in:
- Vue 3 Composition API with TypeScript
- Pinia state management
- Vuetify 3 component library
- FastAPI backend development
- PostgreSQL with SQLAlchemy
- Test-driven development (TDD)

You follow these principles religiously:
- DRY (Don't Repeat Yourself)
- KISS (Keep It Simple, Stupid)
- SOLID principles
- Modularization and separation of concerns
- Clean code with meaningful names
- Defensive programming with proper error handling
</role>

<project_context>
You are working on Gene Curator, a schema-agnostic genetic curation platform.

CRITICAL: Read /home/bernt-popp/development/gene-curator/CLAUDE.md first.
It contains essential project conventions, ports, patterns, and anti-patterns to avoid.

Key facts:
- Stack: Vue 3 + Vite + Pinia + Vuetify 3 (frontend), FastAPI + SQLAlchemy (backend)
- Ports: API=8051, Frontend=5193, PostgreSQL=5454
- All stores follow pattern: fetchItems(), fetchItemById(id), createItem(data), updateItem(id, data)
- Use useLogger() composable, NEVER console.log()
- SQLAlchemy boolean filters: Use .filter(Model.is_active), NEVER .filter(Model.is_active is True)
</project_context>

<implementation_plan>
Read and follow: /home/bernt-popp/development/gene-curator/plan/enhancements/tracking/011-DYNAMIC-FORM-INTEGRATION.md

This plan contains:
- Complete component specifications with code
- Architecture diagrams
- Schema resolution logic
- Testing checklists
- Acceptance criteria
</implementation_plan>

<quality_gates>
Before EVERY commit, you MUST run and pass:
1. make lint          # Backend linting (ruff, mypy, bandit)
2. make lint-frontend # Frontend linting (ESLint + Prettier)
3. make test          # Backend tests
4. make ci-frontend   # Frontend tests

If ANY check fails:
- Fix the issue immediately
- Do NOT skip or ignore tests
- Do NOT use .skip() or continue-on-error
- Re-run checks until all pass
</quality_gates>

<workflow>
Follow this strict workflow for each phase:

1. EXPLORE: Read all relevant files before making changes
2. PLAN: Create a mental model of what needs to change
3. IMPLEMENT: Write code following existing patterns
4. LINT: Run make lint && make lint-frontend
5. TEST: Run make test && make ci-frontend
6. COMMIT: Only if all checks pass
7. VERIFY: Manually test in browser if UI changes

Use TodoWrite to track progress through phases.
</workflow>

<constraints>
NEVER:
- Skip linting or tests
- Use console.log (use useLogger() instead)
- Use defineExpose (use events instead)
- Create files unless absolutely necessary
- Over-engineer or add unrequested features
- Use sed for code changes
- Hardcode magic numbers
- Ignore TypeScript/ESLint errors

ALWAYS:
- Read files before modifying them
- Follow existing code patterns in the codebase
- Use existing composables (useFormRecovery, useHistory, useLogger)
- Add proper error handling
- Include accessibility attributes (aria-labels)
- Run quality checks before commits
</constraints>
```

---

## Phase-by-Phase Implementation Instructions

### Phase 0: Setup (5 min)

```xml
<task id="phase-0" name="Setup Development Environment">
<objective>Create feature branch and verify environment</objective>

<steps>
1. Create and checkout feature branch:
   git checkout -b feature/011-dynamic-form-integration

2. Verify dev environment is running:
   make status

   If not running:
   make hybrid-up
   # In separate terminals:
   cd backend && uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8051
   cd frontend && npm run dev -- --port 5193

3. Read essential context files:
   - /home/bernt-popp/development/gene-curator/CLAUDE.md
   - /home/bernt-popp/development/gene-curator/plan/enhancements/tracking/011-DYNAMIC-FORM-INTEGRATION.md

4. Explore existing components to understand patterns:
   - frontend/src/components/dynamic/DynamicForm.vue
   - frontend/src/components/dynamic/DynamicField.vue
   - frontend/src/components/forms/CurationForm.vue
   - frontend/src/composables/useFormRecovery.js
   - frontend/src/composables/useHistory.js
</steps>

<success_criteria>
- Feature branch created
- Dev environment running (API healthy on :8051)
- Understood existing DynamicForm implementation
</success_criteria>
</task>
```

---

### Phase 1: Create FormActions Component (30 min)

```xml
<task id="phase-1" name="Create FormActions Component">
<objective>Extract reusable action bar for forms</objective>

<rationale>
Starting with the smallest, most self-contained component reduces risk
and provides immediate value (can be used by both Curation and Precuration forms).
</rationale>

<steps>
1. Read existing action patterns in CurationForm.vue (look for undo/redo/save/submit buttons)

2. Create frontend/src/components/forms/FormActions.vue following the spec in 011-DYNAMIC-FORM-INTEGRATION.md Phase 4

3. Ensure component:
   - Uses Vuetify 3 components (v-card-actions, v-btn, v-tooltip, v-btn-group)
   - Has proper props with defaults and validators
   - Emits events: undo, redo, save-draft, submit, cancel
   - Includes keyboard shortcut hints in tooltips
   - Has aria-labels for accessibility

4. Run quality checks:
   make lint-frontend

5. Write unit test in frontend/src/components/forms/__tests__/FormActions.spec.js:
   - Test that all buttons render
   - Test that events emit correctly
   - Test disabled states

6. Run tests:
   make ci-frontend

7. Commit if all pass:
   git add frontend/src/components/forms/FormActions.vue frontend/src/components/forms/__tests__/
   git commit -m "feat(forms): add reusable FormActions component

   - Extract undo/redo/save/submit action bar
   - Add keyboard shortcut tooltips
   - Include accessibility labels

   Part of #011"
</steps>

<files_to_create>
- frontend/src/components/forms/FormActions.vue
- frontend/src/components/forms/__tests__/FormActions.spec.js
</files_to_create>

<success_criteria>
- Component renders without errors
- All props work correctly
- Events emit as expected
- Linting passes
- Tests pass
</success_criteria>
</task>
```

---

### Phase 2: Create CurationSchemaSelect Component (45 min)

```xml
<task id="phase-2" name="Create CurationSchemaSelect Component">
<objective>Create single-schema selector for curation flow</objective>

<important>
Named CurationSchemaSelect (NOT SchemaSelector) to avoid conflict with
existing frontend/src/components/dynamic/SchemaSelector.vue
</important>

<steps>
1. Read existing SchemaSelector.vue to understand patterns (but don't modify it)

2. Read schemasStore to understand available getters:
   frontend/src/stores/schemas.js

3. Create frontend/src/components/forms/CurationSchemaSelect.vue following spec in 011-DYNAMIC-FORM-INTEGRATION.md Phase 3

4. Ensure component:
   - Uses v-select with proper item slots
   - Filters schemas by type (curation/combined)
   - Shows schema description and field count
   - Implements v-model pattern with update:modelValue
   - Has confirmation step before emitting

5. Run quality checks:
   make lint-frontend

6. Write unit test:
   - Test schema filtering by type
   - Test v-model binding
   - Test confirmation behavior

7. Run tests:
   make ci-frontend

8. Commit:
   git add frontend/src/components/forms/CurationSchemaSelect.vue frontend/src/components/forms/__tests__/
   git commit -m "feat(forms): add CurationSchemaSelect component

   - Single schema selector for curation flow
   - Filters by schema_type (curation/combined)
   - Shows field count and description
   - Implements v-model pattern

   Part of #011"
</steps>

<files_to_create>
- frontend/src/components/forms/CurationSchemaSelect.vue
- frontend/src/components/forms/__tests__/CurationSchemaSelect.spec.js
</files_to_create>

<success_criteria>
- Component renders schema list correctly
- Filtering works for curation/combined types
- v-model emits correctly
- Linting passes
- Tests pass
</success_criteria>
</task>
```

---

### Phase 3: Update DynamicForm.vue (30 min)

```xml
<task id="phase-3" name="Update DynamicForm with v-model and validation events">
<objective>Add event-driven data binding to existing DynamicForm</objective>

<important>
- Make MINIMAL changes to existing code
- Do NOT use defineExpose (anti-pattern per code review)
- Use events for data flow
</important>

<steps>
1. Read current DynamicForm.vue thoroughly:
   frontend/src/components/dynamic/DynamicForm.vue

2. Add to existing defineProps:
   readonly: { type: Boolean, default: false }

3. Add to existing defineEmits:
   'update:modelValue', 'validation-change'

4. Add watchers for new events:
   watch(formData, (newVal) => {
     emit('update:modelValue', { ...newVal })
   }, { deep: true })

   watch(validationResult, (result) => {
     emit('validation-change', result)
   }, { immediate: true })

5. Apply readonly prop to all DynamicField components:
   :disabled="readonly"

6. Run quality checks:
   make lint-frontend

7. Verify existing tests still pass:
   make ci-frontend

8. Add new tests for:
   - update:modelValue emission on data change
   - validation-change emission
   - readonly prop disabling fields

9. Commit:
   git add frontend/src/components/dynamic/DynamicForm.vue frontend/src/components/dynamic/__tests__/
   git commit -m "feat(dynamic): add v-model and validation events to DynamicForm

   - Add update:modelValue event for two-way binding
   - Add validation-change event for parent tracking
   - Add readonly prop for review mode
   - No defineExpose (event-driven pattern)

   Part of #011"
</steps>

<files_to_modify>
- frontend/src/components/dynamic/DynamicForm.vue
</files_to_modify>

<success_criteria>
- Existing functionality unchanged
- New events fire correctly
- readonly prop works
- All existing tests still pass
- New tests pass
- No defineExpose used
</success_criteria>
</task>
```

---

### Phase 4: Create SchemaDrivenCurationForm (2 hours)

```xml
<task id="phase-4" name="Create SchemaDrivenCurationForm Component">
<objective>Create the main schema-driven curation form wrapper</objective>

<rationale>
This is the core component that replaces hardcoded CurationForm.
It orchestrates DynamicForm, composables, and form state.
</rationale>

<steps>
1. Read existing CurationForm.vue to understand:
   - How useFormRecovery is integrated
   - How useHistory is integrated
   - Keyboard shortcut handling
   - Save/submit flow

2. Read composables to understand their APIs:
   - frontend/src/composables/useFormRecovery.js
   - frontend/src/composables/useHistory.js
   - frontend/src/composables/useLogger.js

3. Create frontend/src/components/forms/SchemaDrivenCurationForm.vue
   following the COMPLETE spec in 011-DYNAMIC-FORM-INTEGRATION.md Phase 1

4. Key implementation details:
   - Schema-aware recovery key: `curation-${id}-schema-${schemaId}`
   - Clear recovery when schema changes
   - Keyboard shortcuts: Ctrl+S, Ctrl+Z, Ctrl+Shift+Z, Ctrl+Enter, Escape
   - Use FormActions component from Phase 1
   - Integrate with curationsStore for save/submit
   - Use useLogger() for all logging

5. Run quality checks after each major section:
   make lint-frontend

6. Write comprehensive tests:
   - Schema loading
   - Form data binding
   - Save draft flow
   - Submit flow
   - Keyboard shortcuts
   - Recovery key generation
   - Schema change behavior

7. Run all tests:
   make ci-frontend

8. Manual browser test:
   - Navigate to curation form
   - Verify form loads
   - Test save draft
   - Test keyboard shortcuts

9. Commit:
   git add frontend/src/components/forms/SchemaDrivenCurationForm.vue frontend/src/components/forms/__tests__/
   git commit -m "feat(forms): add SchemaDrivenCurationForm component

   - Schema-agnostic curation form using DynamicForm
   - Integrates useFormRecovery with schema-aware keys
   - Integrates useHistory for undo/redo
   - Full keyboard shortcut support (Ctrl+S/Z/Enter/Esc)
   - Event-driven validation (no defineExpose)

   Part of #011
   Closes #62, #61"
</steps>

<files_to_create>
- frontend/src/components/forms/SchemaDrivenCurationForm.vue
- frontend/src/components/forms/__tests__/SchemaDrivenCurationForm.spec.js
</files_to_create>

<dependencies>
- Phase 1: FormActions.vue
- Phase 3: Updated DynamicForm.vue
</dependencies>

<success_criteria>
- Component renders DynamicForm with schemaId
- Form recovery works with schema-aware keys
- Undo/redo works
- Keyboard shortcuts work
- Save draft creates/updates curation
- Submit transitions curation status
- Error handling with toast notifications
- All tests pass
</success_criteria>
</task>
```

---

### Phase 5: Update CurationFormView (1 hour)

```xml
<task id="phase-5" name="Update CurationFormView with Schema Resolution">
<objective>Wire schema resolution and new form into view</objective>

<steps>
1. Read current CurationFormView.vue:
   frontend/src/views/curation/CurationFormView.vue

2. Implement schema resolution logic per 011-DYNAMIC-FORM-INTEGRATION.md Phase 2:
   Priority chain:
   1. Existing curation's curation_schema_id
   2. User selected schema (selectedSchemaId ref)
   3. Route query param (schema_id)
   4. Workflow pair default for scope
   5. Single available schema auto-select

3. Add feature flag for parallel migration:
   const useDynamicForm = import.meta.env.VITE_USE_DYNAMIC_FORM !== 'false'

4. Conditionally render:
   - CurationSchemaSelect (when schema not determined and multiple available)
   - SchemaDrivenCurationForm (when useDynamicForm && schemaId resolved)
   - LegacyCurationForm (when !useDynamicForm, for rollback)

5. Update imports:
   import SchemaDrivenCurationForm from '@/components/forms/SchemaDrivenCurationForm.vue'
   import CurationSchemaSelect from '@/components/forms/CurationSchemaSelect.vue'

6. Run quality checks:
   make lint-frontend

7. Write/update tests:
   - Schema resolution priority chain
   - Feature flag behavior
   - Component switching logic

8. Run tests:
   make ci-frontend

9. Manual browser test:
   - New curation flow
   - Edit existing curation
   - Schema selection when multiple available

10. Commit:
    git add frontend/src/views/curation/CurationFormView.vue frontend/src/views/curation/__tests__/
    git commit -m "feat(views): add schema resolution to CurationFormView

    - Implement 5-level schema resolution priority chain
    - Add feature flag VITE_USE_DYNAMIC_FORM for migration
    - Integrate SchemaDrivenCurationForm
    - Show CurationSchemaSelect when multiple schemas available

    Part of #011"
</steps>

<files_to_modify>
- frontend/src/views/curation/CurationFormView.vue
</files_to_modify>

<dependencies>
- Phase 2: CurationSchemaSelect.vue
- Phase 4: SchemaDrivenCurationForm.vue
</dependencies>

<success_criteria>
- Schema resolves correctly through priority chain
- Feature flag works for migration
- New form renders when flag enabled
- Schema selection appears when needed
- All tests pass
</success_criteria>
</task>
```

---

### Phase 6: Rename Legacy and Final Integration (30 min)

```xml
<task id="phase-6" name="Rename Legacy Form and Final Integration">
<objective>Complete migration setup and verify end-to-end</objective>

<steps>
1. Rename CurationForm.vue to LegacyCurationForm.vue:
   git mv frontend/src/components/forms/CurationForm.vue frontend/src/components/forms/LegacyCurationForm.vue

2. Update any imports of CurationForm to LegacyCurationForm in CurationFormView.vue

3. Add VITE_USE_DYNAMIC_FORM=true to frontend/.env.local

4. Run full quality check suite:
   make lint
   make lint-frontend
   make test
   make ci-frontend

5. Manual E2E testing in browser:
   a. Login as curator
   b. Navigate to a scope
   c. Select a gene
   d. Create new curation → verify schema selection if multiple
   e. Fill form fields → verify DynamicForm renders
   f. Save draft → verify persistence
   g. Test Ctrl+S → verify draft saves
   h. Test Ctrl+Z → verify undo
   i. Reload page → verify recovery dialog
   j. Submit → verify status change

6. Final commit:
   git add -A
   git commit -m "feat(forms): complete DynamicForm integration

   - Rename CurationForm.vue to LegacyCurationForm.vue
   - Enable dynamic form by default
   - Full E2E verification complete

   Closes #62, #61, #77
   Part of #011"

7. Push branch:
   git push -u origin feature/011-dynamic-form-integration
</steps>

<files_to_rename>
- frontend/src/components/forms/CurationForm.vue → LegacyCurationForm.vue
</files_to_rename>

<success_criteria>
- All quality checks pass
- E2E workflow works in browser
- Feature flag enables new form
- Legacy form available for rollback
- Branch pushed to remote
</success_criteria>
</task>
```

---

## Verification Checklist

```xml
<final_verification>
Before marking implementation complete, verify ALL items:

<acceptance_criteria>
- [ ] DynamicForm renders fields from any schema (not hardcoded)
- [ ] Schema determined by workflow_pair or explicit selection
- [ ] Evidence data saved as JSONB (schema-agnostic)
- [ ] Validation uses schema rules (not hardcoded)
- [ ] Live scoring still works with dynamic fields
- [ ] Auto-save (formRecovery) works with schema-aware keys
- [ ] Undo/redo works with dynamic form changes
- [ ] Keyboard shortcuts work (Ctrl+S, Ctrl+Z, Ctrl+Enter, Esc)
- [ ] No regression in existing ClinGen workflow
- [ ] LegacyCurationForm available for rollback
</acceptance_criteria>

<quality_checks>
- [ ] make lint passes with zero errors
- [ ] make lint-frontend passes with zero errors
- [ ] make test passes all backend tests
- [ ] make ci-frontend passes all frontend tests
- [ ] No TypeScript errors
- [ ] No ESLint warnings
</quality_checks>

<code_review_checklist>
- [ ] No console.log (use useLogger)
- [ ] No defineExpose (use events)
- [ ] No hardcoded magic numbers
- [ ] Proper error handling with try/catch
- [ ] Accessibility attributes present
- [ ] Components follow existing patterns
- [ ] Tests cover happy path and edge cases
</code_review_checklist>
</final_verification>
```

---

## Error Recovery Instructions

```xml
<error_recovery>
<scenario name="Linting fails">
1. Read the error message carefully
2. Fix the specific issue (don't disable the rule)
3. Re-run make lint-frontend
4. Repeat until clean
</scenario>

<scenario name="Tests fail">
1. Read the test failure output
2. Determine if it's a test bug or implementation bug
3. Fix the root cause (don't skip the test)
4. Re-run make ci-frontend
5. Repeat until green
</scenario>

<scenario name="Component doesn't render">
1. Check browser console for errors
2. Verify all imports are correct
3. Check props are passed correctly
4. Use Vue DevTools to inspect component state
5. Add logger.debug() statements to trace execution
</scenario>

<scenario name="Store data not loading">
1. Check Network tab for API calls
2. Verify endpoint is correct (port 8051)
3. Check store action is being called
4. Verify backend is running (make status)
</scenario>

<scenario name="Need to rollback">
1. git stash (save current work)
2. git checkout master
3. git branch -D feature/011-dynamic-form-integration
4. Analyze what went wrong
5. Start fresh with lessons learned
</scenario>
</error_recovery>
```

---

## Context Files Reference

```xml
<context_files priority="must_read">
- /home/bernt-popp/development/gene-curator/CLAUDE.md
- /home/bernt-popp/development/gene-curator/plan/enhancements/tracking/011-DYNAMIC-FORM-INTEGRATION.md
</context_files>

<context_files priority="should_read">
- frontend/src/components/dynamic/DynamicForm.vue
- frontend/src/components/dynamic/DynamicField.vue
- frontend/src/components/forms/CurationForm.vue
- frontend/src/composables/useFormRecovery.js
- frontend/src/composables/useHistory.js
- frontend/src/stores/schemas.js
- frontend/src/stores/curations.js
- frontend/src/views/curation/CurationFormView.vue
</context_files>

<context_files priority="reference">
- frontend/src/components/dynamic/SchemaSelector.vue (existing, don't modify)
- frontend/src/api/schemas.js
- frontend/src/api/curations.js
- frontend/src/api/validation.js
</context_files>
```

---

## Success Metrics

```xml
<success_metrics>
<metric name="Code Quality">
- Zero linting errors
- Zero test failures
- No skipped tests
- Type coverage maintained
</metric>

<metric name="Functionality">
- Schema-agnostic forms work
- All keyboard shortcuts functional
- Form recovery works
- Undo/redo works
</metric>

<metric name="Regression">
- Existing ClinGen workflow unbroken
- Legacy form available
- Feature flag works
</metric>

<metric name="Documentation">
- Commits have clear messages
- Code has appropriate comments
- Complex logic is explained
</metric>
</success_metrics>
```

---

**Sources consulted for this prompt design:**
- [Anthropic: Claude Code Best Practices](https://www.anthropic.com/engineering/claude-code-best-practices)
- [Prompt Engineering Guide: LLM Agents](https://www.promptingguide.ai/research/llm-agents)
- [Agentic AI Prompting Best Practices](https://www.ranthebuilder.cloud/post/agentic-ai-prompting-best-practices-for-smarter-vibe-coding)
- [Claude Docs: Prompting Best Practices](https://docs.claude.com/en/docs/build-with-claude/prompt-engineering/claude-4-best-practices)
- [Arize: CLAUDE.md Best Practices](https://arize.com/blog/claude-md-best-practices-learned-from-optimizing-claude-code-with-prompt-learning/)

---

**Last Updated**: 2026-01-12
**Author**: Claude Code
**Purpose**: Agentic implementation guide for Enhancement #011
