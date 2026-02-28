---
phase: M1-security-review-workflow
plan: 05
type: execute
wave: 1
depends_on: []
files_modified:
  - frontend/src/views/curation/CurationDetailView.vue
autonomous: true
gap_closure: true

must_haves:
  truths:
    - "CurationReview displays evidence read-only with score and verdict"
    - "Evidence fields are rendered schema-agnostically via DynamicForm"
  artifacts:
    - path: "frontend/src/views/curation/CurationDetailView.vue"
      provides: "Read-only DynamicForm rendering of curation evidence fields"
      contains: "DynamicForm"
  key_links:
    - from: "CurationDetailView.vue"
      to: "DynamicForm component"
      via: "<DynamicForm :schema-id :initial-data :readonly>"
      pattern: "DynamicForm.*readonly"
    - from: "CurationDetailView.vue"
      to: "schemasAPI.getWorkflowPairById"
      via: "fetch workflow pair to get curation_schema_id"
      pattern: "getWorkflowPairById|curation_schema_id"
---

<objective>
Add schema-agnostic read-only evidence display to CurationDetailView using the existing DynamicForm component in readonly mode.

Purpose: CurationDetailView currently shows hardcoded ClinGen score tables (genetic/experimental evidence breakdown) but does NOT render the actual evidence form fields schema-agnostically. A reviewer needs to see ALL evidence fields — not just scores — to make an informed review decision. DynamicForm already supports a `readonly` prop (built in v0.1), so this is primarily a wiring task.

Output: CurationDetailView renders a read-only DynamicForm showing all evidence fields below the existing score breakdown tables.
</objective>

<execution_context>
@~/.claude/get-shit-done/workflows/execute-plan.md
@~/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/M1-security-review-workflow/M1-VERIFICATION.md
@frontend/src/views/curation/CurationDetailView.vue
@frontend/src/components/dynamic/DynamicForm.vue (props: schemaId, title, initialData, readonly)
@frontend/src/api/schemas.js (getWorkflowPairById method)
</context>

<tasks>

<task type="auto">
  <name>Task 1: Wire DynamicForm read-only evidence display into CurationDetailView</name>
  <files>frontend/src/views/curation/CurationDetailView.vue</files>
  <action>
  Modify `frontend/src/views/curation/CurationDetailView.vue` to add a read-only DynamicForm rendering the evidence fields. The existing hardcoded ClinGen score tables should remain (they provide a useful score summary). The DynamicForm supplements them by showing all evidence form fields.

  **Step 1: Add imports**

  In the `<script setup>` section (around line 506), add:
  ```javascript
  import DynamicForm from '@/components/dynamic/DynamicForm.vue'
  import { schemasAPI } from '@/api'
  ```

  **Step 2: Add state for schema ID**

  After the existing state declarations (around line 531), add:
  ```javascript
  const curationSchemaId = ref(null)
  const loadingSchema = ref(false)
  ```

  **Step 3: Create function to fetch curation schema ID**

  Add a function that fetches the workflow pair to get the curation_schema_id. Place it after the `loadCuration` function (around line 735):
  ```javascript
  async function loadCurationSchema() {
    if (!curation.value?.workflow_pair_id) return
    loadingSchema.value = true
    try {
      const workflowPair = await schemasAPI.getWorkflowPairById(curation.value.workflow_pair_id)
      curationSchemaId.value = workflowPair.curation_schema_id || null
      logger.debug('Curation schema loaded', {
        workflow_pair_id: curation.value.workflow_pair_id,
        curation_schema_id: curationSchemaId.value
      })
    } catch (err) {
      logger.warn('Failed to load curation schema for evidence display', {
        error: err.message,
        workflow_pair_id: curation.value.workflow_pair_id
      })
      // Non-fatal: evidence display is supplementary, score tables still show
    } finally {
      loadingSchema.value = false
    }
  }
  ```

  **Step 4: Call loadCurationSchema after loadCuration**

  Modify the existing `loadCuration` function so that after `curation.value = data` (line 724), it calls `loadCurationSchema()`:
  ```javascript
  async function loadCuration() {
    loading.value = true
    error.value = null

    try {
      const data = await curationsAPI.getCuration(curationId.value)
      curation.value = data
      logger.debug('Curation loaded', { curation_id: curationId.value })
      // Load schema for read-only evidence display
      await loadCurationSchema()
    } catch (err) {
      error.value = 'Failed to load curation details'
      logger.error('Failed to load curation', {
        error: err.message,
        curation_id: curationId.value
      })
    } finally {
      loading.value = false
    }
  }
  ```

  **Step 5: Add DynamicForm to template**

  In the template, AFTER the Score Breakdown `</v-row>` (around line 323, after the closing `</v-row>` of the "Evidence Score Breakdown" card) and BEFORE the Metadata `<v-row>` (around line 326), add a new row:

  ```html
          <!-- Evidence Details (Schema-Agnostic) -->
          <v-row v-if="curationSchemaId" class="mb-6">
            <v-col cols="12">
              <v-card>
                <v-card-title>
                  <v-icon start>mdi-file-document-outline</v-icon>
                  Evidence Details
                </v-card-title>
                <v-card-text>
                  <DynamicForm
                    :schema-id="curationSchemaId"
                    :initial-data="curation.evidence_data || {}"
                    :readonly="true"
                    title=""
                  />
                </v-card-text>
              </v-card>
            </v-col>
          </v-row>
  ```

  **Important considerations:**
  - Use `v-if="curationSchemaId"` so the section only renders when the schema is successfully loaded. If schema fetch fails, the hardcoded ClinGen tables still display.
  - Pass `title=""` to DynamicForm to avoid a redundant "Dynamic Form" title inside the card (the card already has "Evidence Details" as title).
  - The DynamicForm `readonly` prop is already supported (v0.1). It passes `disabled` to DynamicField components, preventing edits. The Save Draft and Submit buttons in DynamicForm's card-actions are hidden when `readonly` is true because `hasChanges` will always be false and `canSubmit` will be false.
  - Do NOT remove the existing hardcoded ClinGen score breakdown tables. They provide a useful summary view alongside the full evidence form.
  - The `schemasAPI` import uses the named export from `@/api` — check that `schemasAPI` is exported from `frontend/src/api/index.js`. If not, import directly: `import schemasAPI from '@/api/schemas'`.
  </action>
  <verify>
  1. Run `cd /home/bernt-popp/development/gene-curator && make lint-frontend` — no lint errors.
  2. Run `cd /home/bernt-popp/development/gene-curator && make test-frontend` — all 428 frontend tests pass.
  3. Grep confirms DynamicForm usage: `grep -n "DynamicForm" frontend/src/views/curation/CurationDetailView.vue` shows import and template usage.
  4. Grep confirms readonly prop: `grep -n "readonly" frontend/src/views/curation/CurationDetailView.vue` shows `:readonly="true"`.
  5. Grep confirms schema fetch: `grep -n "getWorkflowPairById\|curationSchemaId" frontend/src/views/curation/CurationDetailView.vue` shows the wiring.
  </verify>
  <done>CurationDetailView renders a read-only DynamicForm below the score breakdown tables, showing all evidence fields schema-agnostically. The DynamicForm only appears when the curation schema is successfully loaded. Hardcoded ClinGen score tables remain as a summary view. All 428 frontend tests pass and linting is clean.</done>
</task>

</tasks>

<verification>
1. `make lint-frontend` — passes
2. `make test-frontend` — all 428 tests pass
3. DynamicForm component is imported and rendered with `:readonly="true"` and `:schema-id="curationSchemaId"`
4. Schema is fetched via `schemasAPI.getWorkflowPairById(curation.workflow_pair_id)` to get `curation_schema_id`
5. Graceful degradation: if schema fetch fails, only the existing hardcoded score tables show (no error)
</verification>

<success_criteria>
- CurationDetailView imports and renders DynamicForm with readonly=true
- Evidence fields are rendered schema-agnostically (not hardcoded to ClinGen fields)
- Schema ID is obtained by fetching the workflow pair's curation_schema_id
- Existing ClinGen score breakdown tables are preserved
- All 428 frontend tests pass
- Lint passes
</success_criteria>

<output>
After completion, create `.planning/phases/M1-security-review-workflow/M1-05-SUMMARY.md`
</output>
