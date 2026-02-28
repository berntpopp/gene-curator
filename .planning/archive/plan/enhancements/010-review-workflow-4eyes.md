# Enhancement: 4-Eyes Review Workflow (Frontend)

**Priority**: High
**Complexity**: Medium
**Estimated Effort**: 4-6 hours
**Status**: Backend ready (review table, workflow transitions), frontend pending

## Overview

Implement the mandatory peer review ("4-eyes principle") workflow in the frontend. This ensures quality assurance by requiring an independent reviewer to approve curations before activation, a core compliance requirement for clinical curation.

## Current State (from PLAN.md)

✅ **Backend Ready**:
- `reviews` table with approve/reject/needs_revision states
- Workflow transitions enforce different reviewer
- Review endpoint: `/api/v1/workflow/curation/{id}/transition`

❌ **Frontend Pending**:
- No review assignment interface
- No reviewer notifications
- No review comments/feedback UI
- Cannot approve/reject curations

## Business Value

**Regulatory Compliance**: 4-eyes principle is **mandatory** for clinical curation quality assurance. Without proper review workflow, curations cannot be trusted for clinical use.

**Quality Assurance**: Independent review catches errors before curations go live, protecting data quality and institutional reputation.

## Proposed Implementation

### Architecture

```
┌─────────────────────────────────────────────────────┐
│ Curator Workflow                                    │
│ 1. Create curation (draft)                          │
│ 2. Submit for review (status: in_review)           │
│    └─> Assigns available reviewer (not self)       │
└─────────────────┬───────────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────────┐
│ Reviewer Workflow                                   │
│ 1. Receives notification (email/in-app)            │
│ 2. Reviews evidence and scoring                    │
│ 3. Adds comments/feedback                          │
│ 4. Approves / Rejects / Requests Revision          │
└─────────────────┬───────────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────────┐
│ Resolution                                          │
│ - Approved: Curation → Active (one per gene-scope) │
│ - Rejected: Curation → Archived                    │
│ - Needs Revision: Back to curator for edits        │
└─────────────────────────────────────────────────────┘
```

### Frontend Components

**1. Review Queue** (`frontend/src/views/ReviewQueue.vue`)

```vue
<template>
  <v-container>
    <v-card>
      <v-card-title>
        <v-icon start>mdi-clipboard-check</v-icon>
        Review Queue
        <v-chip class="ml-2" color="primary">
          {{ pendingReviews.length }} pending
        </v-chip>
      </v-card-title>

      <v-card-text>
        <v-data-table
          :headers="headers"
          :items="pendingReviews"
          :loading="loading"
          @click:row="openReview"
        >
          <!-- Gene column -->
          <template v-slot:item.gene="{ item }">
            <div>
              <strong>{{ item.gene_symbol }}</strong>
              <div class="text-caption">{{ item.scope_name }}</div>
            </div>
          </template>

          <!-- Curator column -->
          <template v-slot:item.curator="{ item }">
            {{ item.curator_name }}
          </template>

          <!-- Submitted date -->
          <template v-slot:item.submitted="{ item }">
            {{ formatDate(item.submitted_at) }}
          </template>

          <!-- Verdict column -->
          <template v-slot:item.verdict="{ item }">
            <v-chip :color="getVerdictColor(item.verdict)" size="small">
              {{ item.verdict }}
            </v-chip>
          </template>

          <!-- Actions -->
          <template v-slot:item.actions="{ item }">
            <v-btn
              color="primary"
              size="small"
              @click.stop="openReview(item)"
            >
              Review
            </v-btn>
          </template>
        </v-data-table>
      </v-card-text>
    </v-card>
  </v-container>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useCurationsStore } from '@/stores/curations'

const router = useRouter()
const curationsStore = useCurationsStore()

const loading = ref(true)
const pendingReviews = ref([])

const headers = [
  { title: 'Gene', key: 'gene', sortable: true },
  { title: 'Curator', key: 'curator', sortable: true },
  { title: 'Submitted', key: 'submitted', sortable: true },
  { title: 'Verdict', key: 'verdict', sortable: false },
  { title: 'Actions', key: 'actions', sortable: false, width: 120 }
]

onMounted(async () => {
  loading.value = true
  try {
    // Fetch curations assigned for review
    pendingReviews.value = await curationsStore.fetchCurations({
      status: 'in_review',
      reviewer_id: 'me'
    })
  } finally {
    loading.value = false
  }
})

function openReview(curation) {
  router.push(`/curations/${curation.id}/review`)
}

function formatDate(dateString) {
  return new Date(dateString).toLocaleDateString()
}

function getVerdictColor(verdict) {
  const colors = {
    'Definitive': 'success',
    'Strong': 'info',
    'Moderate': 'warning',
    'Limited': 'error'
  }
  return colors[verdict] || 'default'
}
</script>
```

**2. Review Interface** (`frontend/src/views/CurationReview.vue`)

```vue
<template>
  <v-container>
    <v-card>
      <v-card-title>
        Review Curation: {{ curation?.gene_symbol }}
        <v-chip class="ml-2" size="small">{{ curation?.scope_name }}</v-chip>
      </v-card-title>

      <v-card-subtitle>
        Curated by: {{ curation?.curator_name }} •
        Submitted: {{ formatDate(curation?.submitted_at) }}
      </v-card-subtitle>

      <v-divider />

      <!-- Curation Evidence (Read-Only) -->
      <v-card-text>
        <h3 class="mb-4">Evidence Summary</h3>

        <!-- Dynamic form in read-only mode -->
        <dynamic-form
          v-model="curation.evidence_data"
          :schema="schema"
          :readonly="true"
        />

        <!-- Computed Score -->
        <v-alert
          type="info"
          class="mt-4"
          prominent
        >
          <v-row align="center">
            <v-col cols="auto">
              <v-icon size="large">mdi-calculator</v-icon>
            </v-col>
            <v-col>
              <div class="text-h6">Computed Score: {{ curation.score }}</div>
              <div class="text-h5">Verdict: {{ curation.verdict }}</div>
            </v-col>
          </v-row>
        </v-alert>
      </v-card-text>

      <v-divider />

      <!-- Review Comments -->
      <v-card-text>
        <h3 class="mb-4">Review Comments</h3>

        <!-- Previous comments (if needs_revision) -->
        <v-timeline
          v-if="previousComments.length"
          density="compact"
          class="mb-4"
        >
          <v-timeline-item
            v-for="comment in previousComments"
            :key="comment.id"
            :dot-color="comment.status === 'approved' ? 'success' : 'error'"
            size="small"
          >
            <template #opposite>
              <div class="text-caption">{{ formatDate(comment.created_at) }}</div>
            </template>

            <v-card>
              <v-card-subtitle>
                {{ comment.reviewer_name }} - {{ comment.status }}
              </v-card-subtitle>
              <v-card-text>{{ comment.comments }}</v-card-text>
            </v-card>
          </v-timeline-item>
        </v-timeline>

        <!-- New review comment -->
        <v-textarea
          v-model="reviewComment"
          label="Review Comments"
          hint="Provide feedback for the curator"
          rows="4"
          outlined
        />
      </v-card-text>

      <v-divider />

      <!-- Review Actions -->
      <v-card-actions class="pa-4">
        <v-btn
          color="success"
          size="large"
          prepend-icon="mdi-check-circle"
          :loading="approving"
          @click="approveCuration"
        >
          Approve
        </v-btn>

        <v-btn
          color="warning"
          size="large"
          prepend-icon="mdi-pencil"
          :loading="requesting"
          @click="requestRevision"
        >
          Request Revision
        </v-btn>

        <v-btn
          color="error"
          size="large"
          prepend-icon="mdi-close-circle"
          :loading="rejecting"
          @click="rejectCuration"
        >
          Reject
        </v-btn>

        <v-spacer />

        <v-btn @click="cancel">Cancel</v-btn>
      </v-card-actions>
    </v-card>

    <!-- Confirmation Dialog -->
    <v-dialog v-model="confirmDialog" max-width="500">
      <v-card>
        <v-card-title>Confirm {{ confirmAction }}</v-card-title>
        <v-card-text>
          Are you sure you want to {{ confirmAction.toLowerCase() }} this curation?
          {{ confirmAction === 'Reject' ? 'This action cannot be undone.' : '' }}
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn @click="confirmDialog = false">Cancel</v-btn>
          <v-btn
            :color="confirmAction === 'Reject' ? 'error' : 'success'"
            @click="executeReviewAction"
          >
            Confirm
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-container>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import DynamicForm from '@/components/DynamicForm.vue'
import { useCurationsStore } from '@/stores/curations'
import { useWorkflowStore } from '@/stores/workflow'

const route = useRoute()
const router = useRouter()
const curationsStore = useCurationsStore()
const workflowStore = useWorkflowStore()

const loading = ref(true)
const approving = ref(false)
const rejecting = ref(false)
const requesting = ref(false)

const curation = ref(null)
const schema = ref(null)
const previousComments = ref([])
const reviewComment = ref('')

const confirmDialog = ref(false)
const confirmAction = ref('')
const pendingAction = ref(null)

onMounted(async () => {
  loading.value = true
  try {
    const curationId = route.params.id

    // Load curation with evidence
    curation.value = await curationsStore.fetchCurationById(curationId)

    // Load schema for rendering
    schema.value = await schemasStore.fetchSchemaById(curation.value.schema_id)

    // Load previous review comments
    previousComments.value = await workflowStore.fetchReviewHistory(curationId)
  } finally {
    loading.value = false
  }
})

function approveCuration() {
  confirmAction.value = 'Approve'
  pendingAction.value = 'approved'
  confirmDialog.value = true
}

function requestRevision() {
  if (!reviewComment.value.trim()) {
    alert('Please provide comments for the curator.')
    return
  }

  confirmAction.value = 'Request Revision'
  pendingAction.value = 'needs_revision'
  confirmDialog.value = true
}

function rejectCuration() {
  if (!reviewComment.value.trim()) {
    alert('Please provide a reason for rejection.')
    return
  }

  confirmAction.value = 'Reject'
  pendingAction.value = 'rejected'
  confirmDialog.value = true
}

async function executeReviewAction() {
  confirmDialog.value = false

  const actionMap = {
    'approved': () => { approving.value = true },
    'needs_revision': () => { requesting.value = true },
    'rejected': () => { rejecting.value = true }
  }

  actionMap[pendingAction.value]()

  try {
    // Submit review via workflow transition
    await workflowStore.transitionCuration(curation.value.id, {
      target_stage: pendingAction.value === 'approved' ? 'active' : 'curation',
      review_status: pendingAction.value,
      review_comments: reviewComment.value
    })

    // Navigate back to review queue
    router.push('/reviews')
  } catch (error) {
    alert(`Review submission failed: ${error.message}`)
  } finally {
    approving.value = false
    requesting.value = false
    rejecting.value = false
  }
}

function cancel() {
  router.push('/reviews')
}

function formatDate(dateString) {
  return new Date(dateString).toLocaleString()
}
</script>
```

**3. Review Notification Badge** (`frontend/src/layouts/DefaultLayout.vue`)

```vue
<template>
  <v-navigation-drawer>
    <!-- ... other nav items ... -->

    <v-list-item
      prepend-icon="mdi-clipboard-check"
      title="Review Queue"
      to="/reviews"
    >
      <template #append>
        <v-badge
          v-if="pendingReviewCount > 0"
          :content="pendingReviewCount"
          color="error"
        />
      </template>
    </v-list-item>
  </v-navigation-drawer>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useWorkflowStore } from '@/stores/workflow'

const workflowStore = useWorkflowStore()
const pendingReviewCount = ref(0)

let refreshInterval

onMounted(async () => {
  // Fetch initial count
  await refreshReviewCount()

  // Refresh every 60 seconds
  refreshInterval = setInterval(refreshReviewCount, 60000)
})

onUnmounted(() => {
  if (refreshInterval) {
    clearInterval(refreshInterval)
  }
})

async function refreshReviewCount() {
  pendingReviewCount.value = await workflowStore.getPendingReviewCount()
}
</script>
```

### Backend Integration (Already Exists)

**Review Endpoint** (`backend/app/api/v1/endpoints/workflow.py`)

```python
@router.post("/workflow/curation/{curation_id}/transition")
async def transition_curation(
    curation_id: int,
    transition: WorkflowTransition,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Transition curation through workflow stages.

    Enforces 4-eyes principle: reviewer must be different from curator.
    """
    # Validate transition (enforces different reviewer)
    # Create review record
    # Update curation status
    # Send notification to curator
    pass
```

## Implementation Steps

1. **Create ReviewQueue view** (~150 lines)
   - Data table of pending reviews
   - Filter by assigned reviewer
   - Click to open review

2. **Create CurationReview view** (~250 lines)
   - Display curation evidence (read-only)
   - Show computed score and verdict
   - Review comment textarea
   - Approve / Request Revision / Reject buttons

3. **Add review notification badge** (~50 lines)
   - Display pending review count in sidebar
   - Refresh every 60 seconds
   - Red badge if > 0

4. **Update workflow store** (~100 lines)
   - fetchReviewHistory(curationId)
   - getPendingReviewCount()
   - transitionCuration(curationId, transition)

5. **Add routes**
   ```javascript
   // frontend/src/router/index.js
   {
     path: '/reviews',
     component: () => import('@/views/ReviewQueue.vue'),
     meta: { requiresAuth: true, roles: ['reviewer', 'admin'] }
   },
   {
     path: '/curations/:id/review',
     component: () => import('@/views/CurationReview.vue'),
     meta: { requiresAuth: true, roles: ['reviewer', 'admin'] }
   }
   ```

6. **Email notifications** (backend, optional)
   - Send email when curation submitted for review
   - Send email when review completed (approved/rejected/needs_revision)

7. **Update CLAUDE.md**
   ```markdown
   ## 4-Eyes Review Workflow

   All curations require independent peer review before activation.
   Backend enforces reviewer != curator.
   Frontend: ReviewQueue and CurationReview components.
   ```

## Benefits

- **Quality Assurance**: Independent review catches errors before activation
- **Regulatory Compliance**: 4-eyes principle is mandatory for clinical curation
- **Audit Trail**: All reviews tracked with comments and timestamps
- **Transparency**: Curators see reviewer feedback for improvements

## Testing

```javascript
// tests/unit/CurationReview.test.js
describe('CurationReview', () => {
  it('should display curation evidence in read-only mode', () => {
    const curation = {
      gene_symbol: 'BRCA1',
      evidence_data: { title: 'Test Curation' }
    }

    const wrapper = mount(CurationReview, {
      props: { curation }
    })

    expect(wrapper.text()).toContain('BRCA1')
    expect(wrapper.findComponent(DynamicForm).props('readonly')).toBe(true)
  })

  it('should require comments for rejection', async () => {
    const wrapper = mount(CurationReview)

    // Try to reject without comments
    await wrapper.find('[data-test="reject-btn"]').trigger('click')

    // Should show alert
    expect(window.alert).toHaveBeenCalledWith(expect.stringContaining('provide a reason'))
  })

  it('should submit review with comments', async () => {
    const mockTransition = vi.fn()
    const wrapper = mount(CurationReview, {
      global: {
        mocks: {
          workflowStore: { transitionCuration: mockTransition }
        }
      }
    })

    // Add comments and approve
    await wrapper.find('textarea').setValue('Looks good!')
    await wrapper.find('[data-test="approve-btn"]').trigger('click')
    await wrapper.find('[data-test="confirm-btn"]').trigger('click')

    expect(mockTransition).toHaveBeenCalledWith(
      expect.any(Number),
      expect.objectContaining({
        review_comments: 'Looks good!',
        review_status: 'approved'
      })
    )
  })
})
```

## Dependencies

- Vuetify 3 components (already in project)
- No new dependencies required

## Acceptance Criteria

- [ ] ReviewQueue view displays pending reviews for current user
- [ ] CurationReview view shows evidence in read-only mode
- [ ] Review comments textarea required for reject/needs_revision
- [ ] Approve / Request Revision / Reject actions working
- [ ] Confirmation dialog before review submission
- [ ] Review notification badge in sidebar (refreshes every 60s)
- [ ] Backend enforces different reviewer (4-eyes principle)
- [ ] Review history visible for curations with previous reviews
- [ ] Email notifications for review events (optional)
- [ ] Unit tests for review actions and validation
- [ ] Integration test: Complete approve/reject workflow

---

**Impact**: Enables the **mandatory quality assurance process** for clinical curation. Without 4-eyes review, Gene Curator cannot be used for clinical decision-making. Critical for regulatory compliance.
