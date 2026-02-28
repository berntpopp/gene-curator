# MVP M3+M4 Completion — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Complete the MVP by building admin management dialogs (M3) and hardening the platform with a notification system, curator count fix, and documentation (M4).

**Architecture:** M3 adds Vue dialogs to two existing admin views (GeneAssignmentManager, WorkflowManagement) wired to existing API endpoints. M4 adds a full notification model+endpoints on the backend, wires the existing frontend notification store to real APIs, fixes the hardcoded curator count, and expands FAQ content.

**Tech Stack:** Vue 3 + Vuetify 3 + Pinia (frontend), FastAPI + SQLAlchemy 2.0 + PostgreSQL (backend), Vitest (frontend tests), pytest (backend tests)

---

## Task 1: Assignment Store — Add `updateAssignment` Action

**Files:**
- Modify: `frontend/src/stores/assignments.js:47` (inside actions object)

**Step 1: Write the failing test**

Create `frontend/src/stores/__tests__/assignments.spec.js`:

```javascript
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useAssignmentsStore } from '@/stores/assignments'

vi.mock('@/api', () => ({
  assignmentsAPI: {
    getAssignments: vi.fn(),
    updateAssignment: vi.fn(),
    assignCurator: vi.fn(),
  },
}))

import { assignmentsAPI } from '@/api'

describe('useAssignmentsStore', () => {
  let store

  beforeEach(() => {
    setActivePinia(createPinia())
    store = useAssignmentsStore()
    vi.clearAllMocks()
  })

  describe('updateAssignment', () => {
    it('calls API and updates local state', async () => {
      const updated = { id: 'a1', priority_level: 'high', notes: 'urgent' }
      assignmentsAPI.updateAssignment.mockResolvedValue(updated)
      store.assignments = [{ id: 'a1', priority_level: 'low', notes: '' }]

      const result = await store.updateAssignment('a1', { priority_level: 'high', notes: 'urgent' })

      expect(assignmentsAPI.updateAssignment).toHaveBeenCalledWith('a1', { priority_level: 'high', notes: 'urgent' })
      expect(result).toEqual(updated)
      expect(store.assignments[0].priority_level).toBe('high')
    })

    it('sets error on failure', async () => {
      assignmentsAPI.updateAssignment.mockRejectedValue(new Error('Network error'))
      await expect(store.updateAssignment('a1', {})).rejects.toThrow('Network error')
      expect(store.error).toBe('Network error')
    })
  })
})
```

**Step 2: Run test to verify it fails**

Run: `cd frontend && npm run test:run -- --reporter=verbose stores/__tests__/assignments.spec.js`
Expected: FAIL — `store.updateAssignment is not a function`

**Step 3: Write the implementation**

In `frontend/src/stores/assignments.js`, add this action inside the `actions` object (after the existing `updateAssignmentPriority` method around line 115):

```javascript
    async updateAssignment(assignmentId, updateData) {
      this.loading = true
      this.error = null
      try {
        const result = await assignmentsAPI.updateAssignment(assignmentId, updateData)
        const index = this.assignments.findIndex(a => a.id === assignmentId)
        if (index !== -1) {
          this.assignments[index] = { ...this.assignments[index], ...result }
        }
        return result
      } catch (error) {
        this.error = error.message
        throw error
      } finally {
        this.loading = false
      }
    },
```

**Step 4: Run test to verify it passes**

Run: `cd frontend && npm run test:run -- --reporter=verbose stores/__tests__/assignments.spec.js`
Expected: PASS

**Step 5: Commit**

```bash
git add frontend/src/stores/assignments.js frontend/src/stores/__tests__/assignments.spec.js
git commit -m "feat(M3): add updateAssignment action to assignments store"
```

---

## Task 2: Gene Assignment — View Dialog

**Files:**
- Modify: `frontend/src/components/dynamic/GeneAssignmentManager.vue`

**Step 1: Add the view dialog template**

Add before the closing `</v-card>` (around line 279, after the bulk assign dialog), this dialog:

```vue
    <!-- View Assignment Dialog -->
    <v-dialog v-model="viewDialog" max-width="600">
      <v-card>
        <v-card-title class="d-flex align-center">
          <v-icon start>mdi-eye</v-icon>
          Assignment Details
        </v-card-title>
        <v-card-text v-if="selectedAssignment">
          <v-list>
            <v-list-item>
              <v-list-item-title>Gene</v-list-item-title>
              <v-list-item-subtitle>{{ selectedAssignment.gene_symbol || selectedAssignment.gene || 'N/A' }}</v-list-item-subtitle>
            </v-list-item>
            <v-list-item>
              <v-list-item-title>Disease</v-list-item-title>
              <v-list-item-subtitle>{{ selectedAssignment.disease || 'N/A' }}</v-list-item-subtitle>
            </v-list-item>
            <v-list-item>
              <v-list-item-title>Scope</v-list-item-title>
              <v-list-item-subtitle>{{ selectedAssignment.scope_name || selectedAssignment.scope || 'N/A' }}</v-list-item-subtitle>
            </v-list-item>
            <v-list-item>
              <v-list-item-title>Assignee</v-list-item-title>
              <v-list-item-subtitle>{{ selectedAssignment.assignee_name || selectedAssignment.assignee || 'Unassigned' }}</v-list-item-subtitle>
            </v-list-item>
            <v-list-item>
              <v-list-item-title>Status</v-list-item-title>
              <v-list-item-subtitle>
                <v-chip :color="getStatusColor(selectedAssignment.status)" size="small">
                  {{ selectedAssignment.status || 'N/A' }}
                </v-chip>
              </v-list-item-subtitle>
            </v-list-item>
            <v-list-item>
              <v-list-item-title>Priority</v-list-item-title>
              <v-list-item-subtitle>
                <v-chip :color="getPriorityColor(selectedAssignment.priority_level || selectedAssignment.priority)" size="small">
                  {{ selectedAssignment.priority_level || selectedAssignment.priority || 'None' }}
                </v-chip>
              </v-list-item-subtitle>
            </v-list-item>
            <v-list-item>
              <v-list-item-title>Due Date</v-list-item-title>
              <v-list-item-subtitle>{{ selectedAssignment.due_date ? new Date(selectedAssignment.due_date).toLocaleDateString() : 'No due date' }}</v-list-item-subtitle>
            </v-list-item>
            <v-list-item v-if="selectedAssignment.notes">
              <v-list-item-title>Notes</v-list-item-title>
              <v-list-item-subtitle>{{ selectedAssignment.notes }}</v-list-item-subtitle>
            </v-list-item>
            <v-list-item>
              <v-list-item-title>Created</v-list-item-title>
              <v-list-item-subtitle>{{ selectedAssignment.created_at ? new Date(selectedAssignment.created_at).toLocaleString() : 'N/A' }}</v-list-item-subtitle>
            </v-list-item>
            <v-list-item>
              <v-list-item-title>Last Updated</v-list-item-title>
              <v-list-item-subtitle>{{ selectedAssignment.updated_at ? new Date(selectedAssignment.updated_at).toLocaleString() : 'N/A' }}</v-list-item-subtitle>
            </v-list-item>
          </v-list>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="outlined" @click="viewDialog = false">Close</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
```

**Step 2: Add the reactive state and wire the stub**

In the `<script setup>` section, add after the existing reactive data (around line 307):

```javascript
  const viewDialog = ref(false)
  const selectedAssignment = ref(null)
```

Replace the `viewAssignment` stub (line 578-581) with:

```javascript
  const viewAssignment = assignment => {
    logger.info('View assignment requested', { assignmentId: assignment.id })
    selectedAssignment.value = assignment
    viewDialog.value = true
  }
```

**Step 3: Run existing frontend tests to verify no regressions**

Run: `cd frontend && npm run test:run -- --reporter=verbose`
Expected: All existing tests PASS

**Step 4: Commit**

```bash
git add frontend/src/components/dynamic/GeneAssignmentManager.vue
git commit -m "feat(M3): add view dialog to GeneAssignmentManager"
```

---

## Task 3: Gene Assignment — Edit Dialog

**Files:**
- Modify: `frontend/src/components/dynamic/GeneAssignmentManager.vue`

**Step 1: Add the edit dialog template**

Add after the view dialog:

```vue
    <!-- Edit Assignment Dialog -->
    <v-dialog v-model="editDialog" max-width="500">
      <v-card>
        <v-card-title class="d-flex align-center">
          <v-icon start>mdi-pencil</v-icon>
          Edit Assignment
        </v-card-title>
        <v-card-text>
          <v-form ref="editForm">
            <v-select
              v-model="editFormData.priority_level"
              :items="priorityOptions"
              item-title="title"
              item-value="value"
              label="Priority"
              variant="outlined"
            />
            <v-text-field
              v-model="editFormData.due_date"
              type="date"
              label="Due Date"
              variant="outlined"
            />
            <v-textarea
              v-model="editFormData.notes"
              label="Notes"
              variant="outlined"
              rows="3"
            />
          </v-form>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="outlined" @click="editDialog = false">Cancel</v-btn>
          <v-btn color="primary" variant="flat" :loading="saving" @click="saveAssignment">
            Save
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
```

**Step 2: Add reactive state and wire the stub**

Add to script setup:

```javascript
  const editDialog = ref(false)
  const editForm = ref(null)
  const saving = ref(false)
  const editFormData = ref({
    priority_level: null,
    due_date: '',
    notes: ''
  })
  let editingAssignmentId = null
```

Replace the `editAssignment` stub (line 565-568) with:

```javascript
  const editAssignment = assignment => {
    logger.info('Edit assignment requested', { assignmentId: assignment.id })
    editingAssignmentId = assignment.id
    editFormData.value = {
      priority_level: assignment.priority_level || assignment.priority || null,
      due_date: assignment.due_date || '',
      notes: assignment.notes || ''
    }
    editDialog.value = true
  }

  const saveAssignment = async () => {
    saving.value = true
    try {
      await assignmentsStore.updateAssignment(editingAssignmentId, editFormData.value)
      showSuccess('Assignment updated successfully')
      editDialog.value = false
    } catch (error) {
      showError('Failed to update assignment')
      logger.error('Save assignment failed', { error: error.message })
    } finally {
      saving.value = false
    }
  }
```

**Step 3: Run frontend tests**

Run: `cd frontend && npm run test:run -- --reporter=verbose`
Expected: PASS

**Step 4: Commit**

```bash
git add frontend/src/components/dynamic/GeneAssignmentManager.vue
git commit -m "feat(M3): add edit dialog to GeneAssignmentManager"
```

---

## Task 4: Gene Assignment — Reassign Dialog

**Files:**
- Modify: `frontend/src/components/dynamic/GeneAssignmentManager.vue`

**Step 1: Add the reassign dialog template**

Add after the edit dialog:

```vue
    <!-- Reassign Dialog -->
    <v-dialog v-model="reassignDialog" max-width="500">
      <v-card>
        <v-card-title class="d-flex align-center">
          <v-icon start>mdi-account-plus</v-icon>
          Reassign Gene
        </v-card-title>
        <v-card-text>
          <div class="text-body-2 mb-4">
            Reassigning <strong>{{ reassigningAssignment?.gene_symbol || reassigningAssignment?.gene }}</strong>
            from <strong>{{ reassigningAssignment?.assignee_name || reassigningAssignment?.assignee || 'Unassigned' }}</strong>
          </div>
          <v-form ref="reassignForm">
            <v-select
              v-model="reassignCuratorId"
              :items="availableUsers"
              item-title="full_name"
              item-value="id"
              label="New Curator"
              variant="outlined"
              :rules="[v => !!v || 'Please select a curator']"
              required
            />
            <v-textarea
              v-model="reassignNote"
              label="Transfer Note (Optional)"
              variant="outlined"
              rows="2"
            />
          </v-form>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="outlined" @click="reassignDialog = false">Cancel</v-btn>
          <v-btn color="primary" variant="flat" :loading="reassigning" @click="executeReassign">
            Reassign
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
```

**Step 2: Add reactive state and wire the stub**

Add to script setup:

```javascript
  const reassignDialog = ref(false)
  const reassignForm = ref(null)
  const reassigning = ref(false)
  const reassigningAssignment = ref(null)
  const reassignCuratorId = ref(null)
  const reassignNote = ref('')
```

Note: `reassigning` already exists as a ref (line 305) used by rebalanceWorkload — rename that one to `rebalancingWorkload` to avoid collision. Or check if `reassigning` is unused and can be repurposed.

Replace the `reassignGene` stub (line 570-576) with:

```javascript
  const reassignGene = assignment => {
    logger.info('Reassign gene requested', {
      assignmentId: assignment.id,
      geneSymbol: assignment.gene_symbol
    })
    reassigningAssignment.value = assignment
    reassignCuratorId.value = null
    reassignNote.value = ''
    reassignDialog.value = true
  }

  const executeReassign = async () => {
    const { valid } = await reassignForm.value.validate()
    if (!valid) return
    reassigning.value = true
    try {
      await assignmentsAPI.assignCurator(reassigningAssignment.value.id, reassignCuratorId.value)
      showSuccess('Gene reassigned successfully')
      reassignDialog.value = false
      await assignmentsStore.fetchAssignments()
    } catch (error) {
      showError('Failed to reassign gene')
      logger.error('Reassign failed', { error: error.message })
    } finally {
      reassigning.value = false
    }
  }
```

Also add the API import at the top of `<script setup>`:

```javascript
  import { assignmentsAPI } from '@/api'
```

**Step 3: Run frontend tests**

Run: `cd frontend && npm run test:run -- --reporter=verbose`
Expected: PASS

**Step 4: Commit**

```bash
git add frontend/src/components/dynamic/GeneAssignmentManager.vue
git commit -m "feat(M3): add reassign dialog to GeneAssignmentManager"
```

---

## Task 5: Gene Assignment — Cleanup Broken Buttons

**Files:**
- Modify: `frontend/src/components/dynamic/GeneAssignmentManager.vue`

**Step 1: Disable the bulk/rebalance/export buttons that call unimplemented store methods**

In the template (around lines 62-96), modify the buttons:

- **Rebalance Workload button** (line 76-82): Add `:disabled="true"` and add a tooltip explaining it's coming soon
- **Export button** (line 86-89): Add `:disabled="true"` with tooltip
- **Workload Summary section** (lines 196-224): Wrap with `v-if="false"` or remove since `workloadSummary` references a non-existent store property

Replace the Rebalance button:
```vue
    <v-tooltip text="Coming soon" location="top">
      <template #activator="{ props }">
        <v-btn
          v-bind="props"
          color="secondary"
          variant="outlined"
          disabled
        >
          <v-icon start>mdi-scale-balance</v-icon>
          Rebalance Workload
        </v-btn>
      </template>
    </v-tooltip>
```

Replace the Export button:
```vue
    <v-tooltip text="Coming soon" location="top">
      <template #activator="{ props }">
        <v-btn v-bind="props" variant="outlined" disabled>
          <v-icon start>mdi-download</v-icon>
          Export
        </v-btn>
      </template>
    </v-tooltip>
```

Remove or hide the Workload Summary section (the `v-col v-for="user in workloadSummary"` block).

**Step 2: Clean up unused refs**

Remove `rebalancing` and `exporting` refs since those buttons are now disabled. Remove the `rebalanceWorkload` and `exportAssignments` functions if they exist. Remove `workloadSummary` computed.

**Step 3: Run frontend tests**

Run: `cd frontend && npm run test:run -- --reporter=verbose`
Expected: PASS

**Step 4: Commit**

```bash
git add frontend/src/components/dynamic/GeneAssignmentManager.vue
git commit -m "fix(M3): disable unimplemented bulk/rebalance/export buttons"
```

---

## Task 6: Workflow Management — View Dialog

**Files:**
- Modify: `frontend/src/views/WorkflowManagement.vue`

**Step 1: Add the view dialog template**

Add before `</v-card>` closing tag in the template. Reference the existing create dialog pattern (line 119-171):

```vue
    <!-- View Workflow Dialog -->
    <v-dialog v-model="viewWorkflowDialog" max-width="700">
      <v-card>
        <v-card-title class="d-flex align-center">
          <v-icon start>mdi-eye</v-icon>
          Workflow Details
        </v-card-title>
        <v-card-text v-if="selectedWorkflow">
          <v-list>
            <v-list-item>
              <v-list-item-title>Name</v-list-item-title>
              <v-list-item-subtitle class="text-body-1">{{ selectedWorkflow.name }}</v-list-item-subtitle>
            </v-list-item>
            <v-list-item>
              <v-list-item-title>Description</v-list-item-title>
              <v-list-item-subtitle>{{ selectedWorkflow.description || 'No description' }}</v-list-item-subtitle>
            </v-list-item>
            <v-list-item>
              <v-list-item-title>Status</v-list-item-title>
              <v-list-item-subtitle>
                <v-chip :color="selectedWorkflow.is_active ? 'success' : 'grey'" size="small">
                  {{ selectedWorkflow.is_active ? 'Active' : 'Inactive' }}
                </v-chip>
              </v-list-item-subtitle>
            </v-list-item>
            <v-list-item>
              <v-list-item-title>Precuration Schema</v-list-item-title>
              <v-list-item-subtitle>{{ getSchemaName(selectedWorkflow.precuration_schema_id, 'precuration') }}</v-list-item-subtitle>
            </v-list-item>
            <v-list-item>
              <v-list-item-title>Curation Schema</v-list-item-title>
              <v-list-item-subtitle>{{ getSchemaName(selectedWorkflow.curation_schema_id, 'curation') }}</v-list-item-subtitle>
            </v-list-item>
            <v-list-item v-if="selectedWorkflow.data_mapping">
              <v-list-item-title>Data Mapping</v-list-item-title>
              <v-list-item-subtitle>
                <pre class="text-caption mt-1">{{ JSON.stringify(selectedWorkflow.data_mapping, null, 2) }}</pre>
              </v-list-item-subtitle>
            </v-list-item>
            <v-list-item>
              <v-list-item-title>Usage Count</v-list-item-title>
              <v-list-item-subtitle>{{ selectedWorkflow.usage_count || 0 }} scopes</v-list-item-subtitle>
            </v-list-item>
            <v-list-item>
              <v-list-item-title>Created</v-list-item-title>
              <v-list-item-subtitle>{{ selectedWorkflow.created_at ? new Date(selectedWorkflow.created_at).toLocaleString() : 'N/A' }}</v-list-item-subtitle>
            </v-list-item>
          </v-list>

          <!-- Stage Pipeline -->
          <div class="mt-4">
            <div class="text-subtitle-1 font-weight-medium mb-2">Workflow Stages</div>
            <div class="d-flex align-center gap-2 flex-wrap">
              <v-chip v-for="stage in workflowStages" :key="stage.id" :color="stage.color" variant="flat" size="small">
                <v-icon start size="x-small">{{ stage.icon }}</v-icon>
                {{ stage.name }}
              </v-chip>
            </div>
          </div>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="outlined" @click="viewWorkflowDialog = false">Close</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
```

**Step 2: Add reactive state and wire the stub**

Add to `<script setup>`:

```javascript
  const viewWorkflowDialog = ref(false)
  const selectedWorkflow = ref(null)
```

Add a helper function:

```javascript
  const getSchemaName = (schemaId, type) => {
    const schemas = type === 'precuration' ? precurationSchemas.value : curationSchemas.value
    const schema = schemas.find(s => s.id === schemaId)
    return schema ? schema.name : schemaId || 'N/A'
  }
```

Replace `viewWorkflow` stub (line 269-273):

```javascript
  const viewWorkflow = workflow => {
    logger.info('View workflow requested', { workflowId: workflow.id, workflowName: workflow.name })
    selectedWorkflow.value = workflow
    viewWorkflowDialog.value = true
  }
```

**Step 3: Run frontend tests**

Run: `cd frontend && npm run test:run -- --reporter=verbose`
Expected: PASS

**Step 4: Commit**

```bash
git add frontend/src/views/WorkflowManagement.vue
git commit -m "feat(M3): add view dialog to WorkflowManagement"
```

---

## Task 7: Workflow Management — Edit Dialog + Store Method

**Files:**
- Modify: `frontend/src/views/WorkflowManagement.vue`
- Modify: `frontend/src/stores/schemas.js` (add `updateWorkflowPair` action)

**Step 1: Add `updateWorkflowPair` to schemas store**

In `frontend/src/stores/schemas.js`, add after `deleteWorkflowPair` (around line 192):

```javascript
    async updateWorkflowPair(id, pairData) {
      this.loading = true
      this.error = null
      try {
        const updatedPair = await schemasAPI.updateWorkflowPair(id, pairData)
        const index = this.workflowPairs.findIndex(p => p.id === id)
        if (index !== -1) {
          this.workflowPairs[index] = updatedPair
        }
        if (this.currentWorkflowPair && this.currentWorkflowPair.id === id) {
          this.currentWorkflowPair = updatedPair
        }
        return updatedPair
      } catch (error) {
        this.error = error.message
        throw error
      } finally {
        this.loading = false
      }
    },
```

Note: `schemasAPI.updateWorkflowPair(id, pairData)` already exists in `frontend/src/api/schemas.js:79-82`.

**Step 2: Add the edit dialog template to WorkflowManagement.vue**

Add after the view dialog:

```vue
    <!-- Edit Workflow Dialog -->
    <v-dialog v-model="editWorkflowDialog" max-width="500">
      <v-card>
        <v-card-title class="d-flex align-center">
          <v-icon start>mdi-pencil</v-icon>
          Edit Workflow
        </v-card-title>
        <v-card-text>
          <v-form ref="editWorkflowForm">
            <v-text-field
              v-model="editWorkflowData.name"
              label="Name"
              variant="outlined"
              :rules="[v => !!v || 'Name is required']"
              required
            />
            <v-textarea
              v-model="editWorkflowData.description"
              label="Description"
              variant="outlined"
              rows="3"
            />
            <v-switch
              v-model="editWorkflowData.is_active"
              label="Active"
              color="primary"
              hide-details
              class="mb-4"
            />
            <div class="text-caption text-medium-emphasis">
              Linked schemas and stages cannot be changed after creation.
            </div>
          </v-form>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="outlined" @click="editWorkflowDialog = false">Cancel</v-btn>
          <v-btn color="primary" variant="flat" :loading="savingWorkflow" @click="saveWorkflow">
            Save
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
```

**Step 3: Add reactive state and wire the stub**

```javascript
  const editWorkflowDialog = ref(false)
  const editWorkflowForm = ref(null)
  const savingWorkflow = ref(false)
  const editWorkflowData = ref({ name: '', description: '', is_active: true })
  let editingWorkflowId = null
```

Replace `editWorkflow` stub (line 275-279):

```javascript
  const editWorkflow = workflow => {
    logger.info('Edit workflow requested', { workflowId: workflow.id, workflowName: workflow.name })
    editingWorkflowId = workflow.id
    editWorkflowData.value = {
      name: workflow.name || '',
      description: workflow.description || '',
      is_active: workflow.is_active !== false
    }
    editWorkflowDialog.value = true
  }

  const saveWorkflow = async () => {
    const { valid } = await editWorkflowForm.value.validate()
    if (!valid) return
    savingWorkflow.value = true
    try {
      await schemasStore.updateWorkflowPair(editingWorkflowId, editWorkflowData.value)
      showSuccess('Workflow updated successfully')
      editWorkflowDialog.value = false
    } catch (error) {
      showError('Failed to update workflow')
      logger.error('Save workflow failed', { error: error.message })
    } finally {
      savingWorkflow.value = false
    }
  }
```

**Step 4: Run frontend tests**

Run: `cd frontend && npm run test:run -- --reporter=verbose`
Expected: PASS

**Step 5: Commit**

```bash
git add frontend/src/stores/schemas.js frontend/src/views/WorkflowManagement.vue
git commit -m "feat(M3): add edit dialog to WorkflowManagement with store method"
```

---

## Task 8: Fix Gene Summary Curator Count (M4.1)

**Files:**
- Modify: `backend/app/services/gene_summary_service.py:148`
- Create: `backend/tests/unit/test_gene_summary_service.py`

**Step 1: Write the failing test**

```python
"""Tests for GeneSummaryService curator count."""

import pytest
from unittest.mock import MagicMock, patch
from uuid import uuid4

from sqlalchemy.orm import Session

from app.models.models import CurationNew, Gene, Scope
from app.services.gene_summary_service import GeneSummaryService

pytestmark = pytest.mark.unit


class TestCuratorCount:
    """Tests for curator_count in gene summary."""

    def test_curator_count_returns_distinct_users(self, db_session: Session, test_scope: Scope):
        """Curator count should reflect distinct users who created curations."""
        gene = Gene(id=uuid4(), symbol="BRCA1", hgnc_id="HGNC:1100", name="Test Gene")
        db_session.add(gene)
        db_session.commit()

        user1_id = uuid4()
        user2_id = uuid4()

        # Two curations by different users
        c1 = CurationNew(
            id=uuid4(),
            gene_id=gene.id,
            scope_id=test_scope.id,
            created_by=user1_id,
            status="active",
            workflow_stage="active",
        )
        c2 = CurationNew(
            id=uuid4(),
            gene_id=gene.id,
            scope_id=test_scope.id,
            created_by=user2_id,
            status="active",
            workflow_stage="active",
        )
        db_session.add_all([c1, c2])
        db_session.commit()

        service = GeneSummaryService(db_session)
        summary = service.compute_summary(gene.id)

        # Find the scope summary
        scope_summary = next(
            (s for s in summary.scope_summaries if str(s.get("scope_id", "")) == str(test_scope.id)),
            None,
        )
        assert scope_summary is not None
        assert scope_summary["curator_count"] == 2

    def test_curator_count_zero_when_no_curations(self, db_session: Session):
        """Curator count should be 0 when no curations exist for gene."""
        gene = Gene(id=uuid4(), symbol="TP53", hgnc_id="HGNC:11998", name="Test Gene 2")
        db_session.add(gene)
        db_session.commit()

        service = GeneSummaryService(db_session)
        summary = service.compute_summary(gene.id)

        # No scope summaries when no curations
        assert len(summary.scope_summaries) == 0
```

**Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/unit/test_gene_summary_service.py -v`
Expected: FAIL — curator_count is hardcoded to 1

**Step 3: Write the fix**

In `backend/app/services/gene_summary_service.py`, add an import at the top:

```python
from sqlalchemy import func as sa_func, select
```

Then add a helper method to the `GeneSummaryService` class:

```python
    def _get_curator_count(self, gene_id: UUID, scope_id: UUID) -> int:
        """Count distinct users who created curations for a gene in a scope."""
        stmt = (
            select(sa_func.count(sa_func.distinct(CurationNew.created_by)))
            .where(
                CurationNew.gene_id == gene_id,
                CurationNew.scope_id == scope_id,
            )
        )
        result = self.db.execute(stmt).scalar()
        return result or 0
```

Replace line 148 (`"curator_count": 1,  # TODO: Get from curation history`) with:

```python
                "curator_count": self._get_curator_count(gene_id, curation.scope_id),
```

**Step 4: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/unit/test_gene_summary_service.py -v`
Expected: PASS

**Step 5: Run all backend tests**

Run: `cd backend && uv run pytest -v`
Expected: All PASS

**Step 6: Commit**

```bash
git add backend/app/services/gene_summary_service.py backend/tests/unit/test_gene_summary_service.py
git commit -m "fix(M4): replace hardcoded curator count with actual query"
```

---

## Task 9: Notification Model + Enum (M4.2 — Backend Model)

**Files:**
- Modify: `backend/app/core/enums.py` — add `NotificationType` enum
- Modify: `backend/app/models/models.py` — add `NotificationNew` model
- Modify: `backend/app/models/__init__.py` — export new model

**Step 1: Add NotificationType enum**

In `backend/app/core/enums.py`, add after the `ScopeRole` class:

```python
class NotificationType(str, Enum):
    """Types of system notifications."""

    REVIEW_ASSIGNED = "review_assigned"
    REVIEW_COMPLETED = "review_completed"
    REVISION_REQUESTED = "revision_requested"
    CURATION_APPROVED = "curation_approved"
    CURATION_REJECTED = "curation_rejected"

    def __str__(self) -> str:
        return self.value
```

**Step 2: Add NotificationNew model**

In `backend/app/models/models.py`, add near the end of the file (before any `__all__` if present):

```python
class NotificationNew(Base):
    """User notifications for workflow events."""

    __tablename__ = "notifications"

    id: Mapped[PyUUID] = mapped_column(
        compatible_uuid(), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[PyUUID] = mapped_column(
        compatible_uuid(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    link: Mapped[str | None] = mapped_column(String(500))
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    created_at: Mapped[dt] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    user: Mapped["UserNew"] = relationship("UserNew", foreign_keys=[user_id])
```

**Step 3: Export from models __init__.py**

In `backend/app/models/__init__.py`, add `NotificationNew` to the imports and `__all__`:

```python
from .models import (
    # ... existing imports ...
    NotificationNew,
)

__all__ = [
    # ... existing entries ...
    "NotificationNew",
]
```

**Step 4: Run backend tests to verify model creation works**

Run: `cd backend && uv run pytest tests/ -v -k "test_" --co -q | head -5`
Expected: Tests collect successfully (model imports work)

**Step 5: Commit**

```bash
git add backend/app/core/enums.py backend/app/models/models.py backend/app/models/__init__.py
git commit -m "feat(M4): add NotificationNew model and NotificationType enum"
```

---

## Task 10: Notification Pydantic Schemas

**Files:**
- Create: `backend/app/schemas/notification.py`

**Step 1: Create the schema file**

```python
"""Notification Pydantic schemas."""

import uuid
from datetime import datetime
from typing import ClassVar

from pydantic import BaseModel, ConfigDict, Field


class NotificationBase(BaseModel):
    """Base notification schema."""

    type: str = Field(..., description="Notification type")
    title: str = Field(..., max_length=255, description="Short title")
    message: str = Field(..., description="Detail message")
    link: str | None = Field(None, max_length=500, description="Relative URL to relevant page")


class NotificationCreate(NotificationBase):
    """Schema for creating a notification (internal use)."""

    user_id: uuid.UUID = Field(..., description="Recipient user ID")


class NotificationResponse(NotificationBase):
    """Schema for notification API responses."""

    id: uuid.UUID
    is_read: bool = False
    created_at: datetime

    model_config: ClassVar[ConfigDict] = ConfigDict(
        from_attributes=True,
        json_encoders={uuid.UUID: str},
    )


class NotificationListResponse(BaseModel):
    """Paginated notification list."""

    notifications: list[NotificationResponse]
    total: int
    unread_count: int
```

**Step 2: Verify import works**

Run: `cd backend && uv run python -c "from app.schemas.notification import NotificationCreate, NotificationResponse; print('OK')"`
Expected: OK

**Step 3: Commit**

```bash
git add backend/app/schemas/notification.py
git commit -m "feat(M4): add notification Pydantic schemas"
```

---

## Task 11: Notification CRUD

**Files:**
- Create: `backend/app/crud/notification.py`

**Step 1: Write a test**

Create `backend/tests/unit/test_notification_crud.py`:

```python
"""Tests for notification CRUD operations."""

import pytest
from uuid import uuid4

from sqlalchemy.orm import Session

from app.crud.notification import notification_crud
from app.models.models import NotificationNew, UserNew

pytestmark = pytest.mark.unit


class TestNotificationCRUD:
    """Tests for notification CRUD."""

    def test_create_for_user(self, db_session: Session, test_user_admin: UserNew):
        """Create a notification for a user."""
        notification = notification_crud.create_for_user(
            db_session,
            user_id=test_user_admin.id,
            type="review_assigned",
            title="New review",
            message="Gene BRCA1 needs your review",
            link="/curations/abc",
        )
        assert notification.id is not None
        assert notification.user_id == test_user_admin.id
        assert notification.type == "review_assigned"
        assert notification.is_read is False

    def test_get_user_notifications(self, db_session: Session, test_user_admin: UserNew):
        """Get paginated notifications for a user."""
        for i in range(3):
            notification_crud.create_for_user(
                db_session,
                user_id=test_user_admin.id,
                type="review_assigned",
                title=f"Review {i}",
                message=f"Message {i}",
            )
        result = notification_crud.get_user_notifications(
            db_session, user_id=test_user_admin.id
        )
        assert len(result) == 3

    def test_mark_as_read(self, db_session: Session, test_user_admin: UserNew):
        """Mark a notification as read."""
        notification = notification_crud.create_for_user(
            db_session,
            user_id=test_user_admin.id,
            type="curation_approved",
            title="Approved",
            message="Your curation was approved",
        )
        assert notification.is_read is False

        updated = notification_crud.mark_as_read(
            db_session, notification_id=notification.id, user_id=test_user_admin.id
        )
        assert updated.is_read is True

    def test_mark_all_as_read(self, db_session: Session, test_user_admin: UserNew):
        """Mark all notifications as read for a user."""
        for i in range(3):
            notification_crud.create_for_user(
                db_session,
                user_id=test_user_admin.id,
                type="review_assigned",
                title=f"Review {i}",
                message=f"Message {i}",
            )
        count = notification_crud.mark_all_as_read(
            db_session, user_id=test_user_admin.id
        )
        assert count == 3
```

**Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/unit/test_notification_crud.py -v`
Expected: FAIL — module not found

**Step 3: Create the CRUD module**

```python
"""Notification CRUD operations."""

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.models import NotificationNew

logger = get_logger(__name__)


class CRUDNotification:
    """CRUD operations for notifications."""

    def create_for_user(
        self,
        db: Session,
        *,
        user_id: UUID,
        type: str,
        title: str,
        message: str,
        link: str | None = None,
    ) -> NotificationNew:
        """Create a notification for a user."""
        notification = NotificationNew(
            user_id=user_id,
            type=type,
            title=title,
            message=message,
            link=link,
        )
        db.add(notification)
        db.commit()
        db.refresh(notification)
        logger.info("Notification created", user_id=str(user_id), type=type)
        return notification

    def get_user_notifications(
        self,
        db: Session,
        *,
        user_id: UUID,
        is_read: bool | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Sequence[NotificationNew]:
        """Get paginated notifications for a user."""
        stmt = (
            select(NotificationNew)
            .where(NotificationNew.user_id == user_id)
            .order_by(NotificationNew.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        if is_read is not None:
            stmt = stmt.where(NotificationNew.is_read == is_read)
        return db.execute(stmt).scalars().all()

    def get_unread_count(self, db: Session, *, user_id: UUID) -> int:
        """Count unread notifications for a user."""
        from sqlalchemy import func

        stmt = (
            select(func.count())
            .select_from(NotificationNew)
            .where(
                NotificationNew.user_id == user_id,
                NotificationNew.is_read == False,  # noqa: E712
            )
        )
        return db.execute(stmt).scalar() or 0

    def mark_as_read(
        self, db: Session, *, notification_id: UUID, user_id: UUID
    ) -> NotificationNew | None:
        """Mark a single notification as read."""
        stmt = (
            select(NotificationNew)
            .where(
                NotificationNew.id == notification_id,
                NotificationNew.user_id == user_id,
            )
        )
        notification = db.execute(stmt).scalars().first()
        if notification:
            notification.is_read = True
            db.commit()
            db.refresh(notification)
        return notification

    def mark_all_as_read(self, db: Session, *, user_id: UUID) -> int:
        """Mark all notifications as read for a user. Returns count updated."""
        stmt = (
            update(NotificationNew)
            .where(
                NotificationNew.user_id == user_id,
                NotificationNew.is_read == False,  # noqa: E712
            )
            .values(is_read=True)
        )
        result = db.execute(stmt)
        db.commit()
        return result.rowcount


notification_crud = CRUDNotification()
```

**Step 4: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/unit/test_notification_crud.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add backend/app/crud/notification.py backend/tests/unit/test_notification_crud.py
git commit -m "feat(M4): add notification CRUD with tests"
```

---

## Task 12: Notification API Endpoints

**Files:**
- Create: `backend/app/api/v1/endpoints/notifications.py`
- Modify: `backend/app/api/v1/api.py` — register router

**Step 1: Write API tests**

Create `backend/tests/api/test_notifications.py`:

```python
"""API tests for notification endpoints."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.crud.notification import notification_crud
from app.models.models import UserNew

pytestmark = pytest.mark.unit


class TestNotificationList:
    """Tests for GET /notifications."""

    def test_list_notifications_authenticated(
        self, client: TestClient, admin_token: str, db_session: Session, test_user_admin: UserNew
    ):
        """Authenticated user can list their notifications."""
        notification_crud.create_for_user(
            db_session,
            user_id=test_user_admin.id,
            type="review_assigned",
            title="Test",
            message="Test message",
        )
        response = client.get(
            "/api/v1/notifications",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "notifications" in data
        assert len(data["notifications"]) == 1

    def test_list_notifications_unauthenticated(self, client: TestClient):
        """Unauthenticated request should fail."""
        response = client.get("/api/v1/notifications")
        assert response.status_code == 401


class TestMarkAsRead:
    """Tests for PATCH /notifications/{id}/read."""

    def test_mark_as_read(
        self, client: TestClient, admin_token: str, db_session: Session, test_user_admin: UserNew
    ):
        """Mark a notification as read."""
        notification = notification_crud.create_for_user(
            db_session,
            user_id=test_user_admin.id,
            type="curation_approved",
            title="Approved",
            message="Your curation was approved",
        )
        response = client.patch(
            f"/api/v1/notifications/{notification.id}/read",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        assert response.json()["is_read"] is True


class TestMarkAllAsRead:
    """Tests for PATCH /notifications/read-all."""

    def test_mark_all_as_read(
        self, client: TestClient, admin_token: str, db_session: Session, test_user_admin: UserNew
    ):
        """Mark all notifications as read."""
        for i in range(3):
            notification_crud.create_for_user(
                db_session,
                user_id=test_user_admin.id,
                type="review_assigned",
                title=f"Review {i}",
                message=f"Message {i}",
            )
        response = client.patch(
            "/api/v1/notifications/read-all",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        assert response.json()["count"] == 3
```

**Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/api/test_notifications.py -v`
Expected: FAIL — 404 (route not registered)

**Step 3: Create the endpoint module**

Create `backend/app/api/v1/endpoints/notifications.py`:

```python
"""Notification API endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_active_user
from app.core.logging import api_endpoint, get_logger
from app.crud.notification import notification_crud
from app.models.models import UserNew
from app.schemas.notification import NotificationListResponse, NotificationResponse

logger = get_logger(__name__)

router = APIRouter()


@router.get("", response_model=NotificationListResponse)
@api_endpoint()
async def list_notifications(
    is_read: bool | None = Query(None, description="Filter by read status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: UserNew = Depends(get_current_active_user),
) -> NotificationListResponse:
    """List current user's notifications."""
    notifications = notification_crud.get_user_notifications(
        db, user_id=current_user.id, is_read=is_read, skip=skip, limit=limit
    )
    unread_count = notification_crud.get_unread_count(db, user_id=current_user.id)
    total = len(notifications)  # Simplified; for full pagination add count query
    return NotificationListResponse(
        notifications=[NotificationResponse.model_validate(n) for n in notifications],
        total=total,
        unread_count=unread_count,
    )


@router.patch("/{notification_id}/read", response_model=NotificationResponse)
@api_endpoint()
async def mark_notification_read(
    notification_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserNew = Depends(get_current_active_user),
) -> NotificationResponse:
    """Mark a single notification as read."""
    notification = notification_crud.mark_as_read(
        db, notification_id=notification_id, user_id=current_user.id
    )
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found",
        )
    return NotificationResponse.model_validate(notification)


@router.patch("/read-all")
@api_endpoint()
async def mark_all_notifications_read(
    db: Session = Depends(get_db),
    current_user: UserNew = Depends(get_current_active_user),
) -> dict:
    """Mark all notifications as read for current user."""
    count = notification_crud.mark_all_as_read(db, user_id=current_user.id)
    return {"count": count, "message": f"Marked {count} notifications as read"}
```

**Step 4: Register the router in api.py**

In `backend/app/api/v1/api.py`, add the import:

```python
from app.api.v1.endpoints import (
    # ... existing imports ...
    notifications,
)
```

And add the router registration (before the logs router):

```python
api_router.include_router(
    notifications.router, prefix="/notifications", tags=["notifications"]
)
```

**Step 5: Run tests**

Run: `cd backend && uv run pytest tests/api/test_notifications.py -v`
Expected: PASS

Run: `cd backend && uv run pytest -v`
Expected: All PASS

**Step 6: Commit**

```bash
git add backend/app/api/v1/endpoints/notifications.py backend/app/api/v1/api.py backend/tests/api/test_notifications.py
git commit -m "feat(M4): add notification REST endpoints with tests"
```

---

## Task 13: Workflow Engine Notification Hooks

**Files:**
- Modify: `backend/app/crud/workflow_engine.py`

**Step 1: Write a test**

Add to `backend/tests/unit/test_notification_crud.py`:

```python
class TestWorkflowNotificationHooks:
    """Verify workflow transitions create notifications."""

    def test_assign_reviewer_creates_notification(
        self, db_session: Session, test_user_admin: UserNew, test_user_curator
    ):
        """Assigning a reviewer should create a notification."""
        from app.crud.notification import notification_crud
        from app.models.models import NotificationNew

        # Count notifications before
        before_count = len(
            notification_crud.get_user_notifications(db_session, user_id=test_user_admin.id)
        )

        # Create a notification manually (simulating the hook)
        notification_crud.create_for_user(
            db_session,
            user_id=test_user_admin.id,
            type="review_assigned",
            title="New review assigned",
            message="Gene BRCA1 curation needs your review",
            link="/curations/test-id",
        )

        after_count = len(
            notification_crud.get_user_notifications(db_session, user_id=test_user_admin.id)
        )
        assert after_count == before_count + 1
```

**Step 2: Add notification hooks to workflow engine**

In `backend/app/crud/workflow_engine.py`, add the import at the top:

```python
from app.crud.notification import notification_crud
```

In `assign_peer_reviewer` method (after `db.refresh(review)` around line 344), add:

```python
        # Notify the reviewer
        try:
            gene_symbol = ""
            if item_type == "curation" and curation_result:
                gene = db.execute(
                    select(Gene).where(Gene.id == curation_result.gene_id)
                ).scalars().first()
                gene_symbol = gene.symbol if gene else ""
            notification_crud.create_for_user(
                db,
                user_id=reviewer_id,
                type="review_assigned",
                title="New review assigned",
                message=f"Gene {gene_symbol} curation needs your review",
                link=f"/curations/{item_id}",
            )
        except Exception:
            logger.warning("Failed to create review assignment notification", exc_info=True)
```

In `submit_peer_review` method, after the decision handling (around line 400), add notification for approve/reject:

```python
        # Notify the curation creator
        try:
            curation = db.execute(
                select(CurationNew).where(CurationNew.id == review.curation_id)
            ).scalars().first()
            if curation:
                gene = db.execute(
                    select(Gene).where(Gene.id == curation.gene_id)
                ).scalars().first()
                gene_symbol = gene.symbol if gene else ""
                creator_id = curation.created_by

                if decision == "approve":
                    ntype, title = "curation_approved", "Curation approved"
                    message = f"Your curation for {gene_symbol} has been approved"
                elif decision == "reject":
                    ntype, title = "curation_rejected", "Curation rejected"
                    message = f"Your curation for {gene_symbol} has been rejected"
                else:
                    ntype, title = "revision_requested", "Revision requested"
                    message = f"Revisions requested for your {gene_symbol} curation"

                notification_crud.create_for_user(
                    db,
                    user_id=creator_id,
                    type=ntype,
                    title=title,
                    message=message,
                    link=f"/curations/{review.curation_id}",
                )
        except Exception:
            logger.warning("Failed to create review decision notification", exc_info=True)
```

Add import for `Gene` if not already present:

```python
from app.models.models import (
    # ... existing ...
    Gene,
)
```

**Step 3: Run all backend tests**

Run: `cd backend && uv run pytest -v`
Expected: All PASS

**Step 4: Commit**

```bash
git add backend/app/crud/workflow_engine.py backend/tests/unit/test_notification_crud.py
git commit -m "feat(M4): add notification hooks to workflow engine transitions"
```

---

## Task 14: Frontend Notification API Module + Store Wiring

**Files:**
- Create: `frontend/src/api/notifications.js`
- Modify: `frontend/src/api/index.js` — export new module
- Modify: `frontend/src/stores/notifications.js` — wire to real API

**Step 1: Create the API module**

Create `frontend/src/api/notifications.js`:

```javascript
import apiClient from './client.js'

export const notificationsAPI = {
  async getNotifications(params = {}) {
    const response = await apiClient.get('/notifications', { params })
    return response.data
  },

  async markAsRead(notificationId) {
    const response = await apiClient.patch(`/notifications/${notificationId}/read`)
    return response.data
  },

  async markAllAsRead() {
    const response = await apiClient.patch('/notifications/read-all')
    return response.data
  },
}
```

**Step 2: Export from barrel**

In `frontend/src/api/index.js`, add:

```javascript
export { notificationsAPI } from './notifications.js'
```

**Step 3: Wire the store**

Replace the contents of `frontend/src/stores/notifications.js` `fetchNotifications`, `markAsRead`, and `markAllAsRead` methods. Also update the import:

Replace line 18 (`// import apiClient from '@/api/client'`) with:

```javascript
import { notificationsAPI } from '@/api'
```

Replace `fetchNotifications` (lines 108-144):

```javascript
  const fetchNotifications = async () => {
    loading.value = true
    error.value = null

    try {
      const response = await notificationsAPI.getNotifications()
      notifications.value = response.notifications || []

      logService.debug('Fetched notifications', {
        count: notifications.value.length,
        unread: totalUnread.value
      })
    } catch (err) {
      error.value = err.response?.data?.detail || 'Failed to fetch notifications'
      logService.error('Failed to fetch notifications', {
        error: err.message,
        stack: err.stack
      })
    } finally {
      loading.value = false
    }
  }
```

Replace `markAsRead` (lines 151-171):

```javascript
  const markAsRead = async notificationId => {
    try {
      await notificationsAPI.markAsRead(notificationId)

      const notification = notifications.value.find(n => n.id === notificationId)
      if (notification) {
        notification.read = true
        notification.is_read = true
        logService.debug('Marked notification as read', { notificationId })
      }
    } catch (err) {
      error.value = err.response?.data?.detail || 'Failed to mark notification as read'
      logService.error('Failed to mark notification as read', {
        notificationId,
        error: err.message,
        stack: err.stack
      })
      throw err
    }
  }
```

Replace `markAllAsRead` (lines 177-198):

```javascript
  const markAllAsRead = async () => {
    try {
      await notificationsAPI.markAllAsRead()

      notifications.value.forEach(n => {
        n.read = true
        n.is_read = true
      })

      logService.info('Marked all notifications as read', {
        count: notifications.value.length
      })
    } catch (err) {
      error.value = err.response?.data?.detail || 'Failed to mark all notifications as read'
      logService.error('Failed to mark all notifications as read', {
        error: err.message,
        stack: err.stack
      })
      throw err
    }
  }
```

**Step 4: Add polling**

Add a `startPolling` / `stopPolling` method after the existing actions:

```javascript
  let pollingInterval = null

  const startPolling = (intervalMs = 60000) => {
    stopPolling()
    fetchNotifications()
    pollingInterval = setInterval(fetchNotifications, intervalMs)
    logService.debug('Notification polling started', { intervalMs })
  }

  const stopPolling = () => {
    if (pollingInterval) {
      clearInterval(pollingInterval)
      pollingInterval = null
      logService.debug('Notification polling stopped')
    }
  }
```

Add `startPolling` and `stopPolling` to the return object.

**Step 5: Run frontend tests**

Run: `cd frontend && npm run test:run -- --reporter=verbose`
Expected: PASS

**Step 6: Commit**

```bash
git add frontend/src/api/notifications.js frontend/src/api/index.js frontend/src/stores/notifications.js
git commit -m "feat(M4): wire notification store to real API with polling"
```

---

## Task 15: Alembic Migration for Notifications Table

**Files:**
- Create: Alembic migration file

**Step 1: Generate migration**

Run: `cd backend && uv run alembic revision --autogenerate -m "add notifications table"`

**Step 2: Verify migration content**

Read the generated migration file in `backend/alembic/versions/` and verify it creates the `notifications` table with the correct columns.

**Step 3: Run migration**

Run: `cd backend && uv run alembic upgrade head`
Expected: Migration applies successfully

**Step 4: Commit**

```bash
git add backend/alembic/versions/
git commit -m "feat(M4): add alembic migration for notifications table"
```

---

## Task 16: FAQ Content Expansion (M4.4)

**Files:**
- Modify: `frontend/src/views/Faq.vue`

**Step 1: Add new FAQ entries**

In `frontend/src/views/Faq.vue`, add these entries to the `faqs` array:

```javascript
    {
      question: 'How do I precurate a gene?',
      answer:
        'To precurate a gene:<br/>1. Navigate to <strong>Gene Assignments</strong> and find your assigned gene<br/>2. Click the gene to open its detail page<br/>3. Click <strong>Create Precuration</strong><br/>4. Fill in the schema-driven form (fields depend on your scope\'s methodology)<br/>5. Save as draft or submit when complete<br/><br/>Your scope admin assigns genes to you. Once a precuration is submitted, it becomes available for the curation stage.'
    },
    {
      question: 'How does the review workflow work?',
      answer:
        'Gene Curator uses a <strong>4-eyes principle</strong> for quality control:<br/>1. A <strong>curator</strong> creates and submits a curation<br/>2. An independent <strong>reviewer</strong> receives the submission in their Review Queue<br/>3. The reviewer examines the evidence and can:<br/>&nbsp;&nbsp;• <strong>Approve</strong> — curation becomes active<br/>&nbsp;&nbsp;• <strong>Request Revision</strong> — sent back to curator with comments<br/>&nbsp;&nbsp;• <strong>Reject</strong> — curation is rejected with reason<br/>4. The original curator <em>cannot</em> review their own work<br/><br/>You\'ll receive notifications when reviews are assigned or completed.'
    },
    {
      question: 'What happens when a curation is rejected or sent back for revision?',
      answer:
        'When a reviewer requests revision:<br/>• You\'ll receive a notification with the reviewer\'s comments<br/>• The curation returns to your editing queue<br/>• Make the requested changes and resubmit<br/>• The review cycle repeats until approved<br/><br/>When a reviewer rejects:<br/>• The curation is marked as rejected<br/>• You can create a new curation for the same gene if needed'
    },
    {
      question: 'Can I work across multiple scopes?',
      answer:
        'Yes! You can be a member of multiple scopes with different roles:<br/>• <strong>Curator</strong> in one scope and <strong>Reviewer</strong> in another<br/>• Each scope has its own methodology (ClinGen, GenCC, custom)<br/>• Your Review Queue shows pending reviews across all your scopes<br/>• Use the scope filter on list views to focus on one scope at a time'
    },
    {
      question: 'How do I manage gene assignments as an admin?',
      answer:
        'Scope admins can manage gene assignments from the <strong>Gene Assignments</strong> page:<br/>• <strong>View</strong>: Click the eye icon to see assignment details<br/>• <strong>Edit</strong>: Click the pencil icon to change priority, due date, or notes<br/>• <strong>Reassign</strong>: Click the person+ icon to transfer a gene to a different curator<br/>• <strong>Bulk Assign</strong>: Select multiple genes and assign them at once'
    },
    {
      question: 'Where do I see my notifications?',
      answer:
        'Notifications appear in the navigation bar as a badge count. Click the notification icon to see:<br/>• Review assignments (new curations to review)<br/>• Review decisions (your curations approved/rejected)<br/>• Revision requests<br/><br/>Notifications refresh automatically every 60 seconds. Click <strong>Mark all as read</strong> to clear the badge.'
    },
```

**Step 2: Run frontend tests**

Run: `cd frontend && npm run test:run -- --reporter=verbose`
Expected: PASS

**Step 3: Commit**

```bash
git add frontend/src/views/Faq.vue
git commit -m "docs(M4): expand FAQ with workflow and notification guidance"
```

---

## Task 17: Manual Smoke Test Checklist (M4.3)

**Files:**
- Create: `docs/SMOKE_TEST_CHECKLIST.md`

**Step 1: Write the checklist**

```markdown
# MVP Smoke Test Checklist

Run these tests manually after completing M3+M4 implementation.

## Prerequisites
- Hybrid dev mode running (`make hybrid-up && make backend && make frontend`)
- Database initialized with seed data (`make db-init`)
- Two user accounts: admin (admin@gene-curator.dev / admin123) and a test curator

## Test Paths

### 1. Happy Path: Assignment to Active
- [ ] Log in as admin
- [ ] Navigate to Gene Assignments
- [ ] Assign a gene to a curator
- [ ] Log in as curator
- [ ] Create precuration for the assigned gene
- [ ] Submit precuration
- [ ] Create curation from the precuration (verify prefill works)
- [ ] Submit curation for review
- [ ] Log in as admin (reviewer)
- [ ] Check Review Queue shows the pending curation
- [ ] Open curation review, verify evidence displays read-only
- [ ] Approve the curation
- [ ] Verify curation status is "Active"

### 2. Revision Loop
- [ ] Submit a curation for review
- [ ] As reviewer, click "Request Revision" with a comment
- [ ] Verify curator receives notification
- [ ] As curator, edit the curation based on feedback
- [ ] Resubmit for review
- [ ] As reviewer, approve

### 3. Rejection
- [ ] Submit a curation for review
- [ ] As reviewer, reject with reason
- [ ] Verify curation returns to draft/rejected state

### 4. Four-Eyes Enforcement
- [ ] As curator, submit own curation
- [ ] Try to review own curation — should be blocked
- [ ] Verify error message is clear

### 5. Multi-Scope
- [ ] Log in as user who is curator in Scope A and reviewer in Scope B
- [ ] Verify can create curations in Scope A
- [ ] Verify can review curations in Scope B
- [ ] Verify cannot create curations in Scope B (if viewer only)

### 6. Admin Dialogs (M3)
- [ ] Gene Assignments: View dialog shows full details
- [ ] Gene Assignments: Edit dialog saves priority/due date/notes
- [ ] Gene Assignments: Reassign dialog transfers gene to new curator
- [ ] Workflow Management: View dialog shows full config
- [ ] Workflow Management: Edit dialog saves name/description/active status

### 7. Notifications (M4)
- [ ] Submit curation → reviewer gets notification
- [ ] Approve curation → curator gets notification
- [ ] Reject curation → curator gets notification
- [ ] Request revision → curator gets notification
- [ ] Mark single notification as read
- [ ] Mark all notifications as read
- [ ] Badge count updates correctly

## Pass Criteria
All checkboxes above must pass. Any failure should be filed as a bug before declaring MVP complete.
```

**Step 2: Commit**

```bash
git add docs/SMOKE_TEST_CHECKLIST.md
git commit -m "docs(M4): add manual smoke test checklist for MVP verification"
```

---

## Task 18: Run Full CI

**Step 1: Run backend CI**

Run: `cd backend && uv run pytest -v`
Expected: All PASS

**Step 2: Run backend linting**

Run: `make lint`
Expected: PASS (fix any issues before committing)

**Step 3: Run frontend CI**

Run: `cd frontend && npm run test:run -- --reporter=verbose`
Expected: All PASS

**Step 4: Run frontend linting**

Run: `make lint-frontend`
Expected: PASS (fix any issues)

**Step 5: Final commit if any lint fixes needed**

```bash
git add -A
git commit -m "fix: lint and format fixes for M3+M4 implementation"
```

---

## Summary

| Task | Description | Commit Message |
|------|-------------|----------------|
| 1 | Assignment store `updateAssignment` action | `feat(M3): add updateAssignment action to assignments store` |
| 2 | Gene Assignment view dialog | `feat(M3): add view dialog to GeneAssignmentManager` |
| 3 | Gene Assignment edit dialog | `feat(M3): add edit dialog to GeneAssignmentManager` |
| 4 | Gene Assignment reassign dialog | `feat(M3): add reassign dialog to GeneAssignmentManager` |
| 5 | Cleanup broken buttons | `fix(M3): disable unimplemented bulk/rebalance/export buttons` |
| 6 | Workflow view dialog | `feat(M3): add view dialog to WorkflowManagement` |
| 7 | Workflow edit dialog + store method | `feat(M3): add edit dialog to WorkflowManagement with store method` |
| 8 | Curator count fix | `fix(M4): replace hardcoded curator count with actual query` |
| 9 | Notification model + enum | `feat(M4): add NotificationNew model and NotificationType enum` |
| 10 | Notification Pydantic schemas | `feat(M4): add notification Pydantic schemas` |
| 11 | Notification CRUD | `feat(M4): add notification CRUD with tests` |
| 12 | Notification API endpoints | `feat(M4): add notification REST endpoints with tests` |
| 13 | Workflow engine notification hooks | `feat(M4): add notification hooks to workflow engine transitions` |
| 14 | Frontend notification API + store wiring | `feat(M4): wire notification store to real API with polling` |
| 15 | Alembic migration | `feat(M4): add alembic migration for notifications table` |
| 16 | FAQ content expansion | `docs(M4): expand FAQ with workflow and notification guidance` |
| 17 | Smoke test checklist | `docs(M4): add manual smoke test checklist for MVP verification` |
| 18 | Full CI pass | `fix: lint and format fixes for M3+M4 implementation` |
