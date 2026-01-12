# Enhancement: Draft Auto-Save for Curation Forms

**Priority**: High
**Complexity**: Medium
**Estimated Effort**: 4-6 hours
**Status**: Backend ready (draft state in workflow), frontend pending

## Overview

Implement automatic draft saving for curation forms to prevent data loss during long curation sessions (5-10 minutes). This is a **core curation feature** that directly improves curator productivity and prevents frustration from browser crashes or network issues.

## Current State (from PLAN.md)

✅ **Backend Ready**: Draft state exists in workflow (`curation_status` enum has `draft`)
❌ **Frontend Pending**: No auto-save implementation, curators lose work if they navigate away

## Business Value

**Curator Pain Point**: Curations take 5-10 minutes with complex evidence collection. Losing work due to browser crash, accidental navigation, or session timeout is extremely frustrating.

**Expected Impact**:
- Reduce curator frustration from data loss
- Enable work-in-progress curation resumption
- Support "save and continue later" workflow
- Increase curator confidence in the platform

## Proposed Implementation

### Architecture

```
┌─────────────────────────────────────────────────────┐
│ Frontend (Vue 3)                                    │
│ ┌─────────────────────────────────────────────────┐ │
│ │ Curation Form Component                         │ │
│ │ - Auto-save every 30 seconds                    │ │
│ │ - Debounced save on field changes              │ │
│ │ - Visual indicator: "Saving..." / "Saved"      │ │
│ └─────────────────────────────────────────────────┘ │
└─────────────────┬───────────────────────────────────┘
                  │ PATCH /api/v1/curations/{id}
                  │ status=draft, evidence_data={...}
┌─────────────────▼───────────────────────────────────┐
│ Backend (FastAPI)                                   │
│ - Accepts draft updates without validation         │
│ - Full validation only on submit                   │
└─────────────────────────────────────────────────────┘
```

### Frontend Components

**1. Auto-Save Composable** (`frontend/src/composables/useAutoSave.js`)

```javascript
import { ref, watch, onUnmounted } from 'vue'
import { debounce } from 'lodash-es'

export function useAutoSave(saveFunction, options = {}) {
  const {
    interval = 30000,        // Auto-save every 30 seconds
    debounceDelay = 2000,    // Debounce user input by 2 seconds
    enabled = true
  } = options

  const isSaving = ref(false)
  const lastSaved = ref(null)
  const saveStatus = ref('idle') // idle, saving, saved, error

  let autoSaveTimer = null
  let isDirty = false

  // Debounced save triggered by user input
  const debouncedSave = debounce(async () => {
    if (!enabled || !isDirty) return
    await triggerSave()
  }, debounceDelay)

  // Actual save function
  async function triggerSave() {
    if (isSaving.value) return

    isSaving.value = true
    saveStatus.value = 'saving'

    try {
      await saveFunction()
      lastSaved.value = new Date()
      saveStatus.value = 'saved'
      isDirty = false

      // Clear "saved" status after 2 seconds
      setTimeout(() => {
        if (saveStatus.value === 'saved') {
          saveStatus.value = 'idle'
        }
      }, 2000)
    } catch (error) {
      console.error('Auto-save failed:', error)
      saveStatus.value = 'error'
    } finally {
      isSaving.value = false
    }
  }

  // Start auto-save timer
  function startAutoSave() {
    if (!enabled) return

    autoSaveTimer = setInterval(() => {
      if (isDirty) {
        triggerSave()
      }
    }, interval)
  }

  // Stop auto-save timer
  function stopAutoSave() {
    if (autoSaveTimer) {
      clearInterval(autoSaveTimer)
      autoSaveTimer = null
    }
  }

  // Mark as dirty (changes pending)
  function markDirty() {
    isDirty = true
    debouncedSave()
  }

  // Cleanup on unmount
  onUnmounted(() => {
    stopAutoSave()
    debouncedSave.cancel()
  })

  return {
    isSaving,
    lastSaved,
    saveStatus,
    startAutoSave,
    stopAutoSave,
    markDirty,
    triggerSave
  }
}
```

**2. Curation Form with Auto-Save** (`frontend/src/views/CurationForm.vue`)

```vue
<template>
  <v-container>
    <!-- Save Status Indicator -->
    <v-alert
      v-if="saveStatus !== 'idle'"
      :type="saveStatus === 'saved' ? 'success' : saveStatus === 'error' ? 'error' : 'info'"
      density="compact"
      class="mb-4"
    >
      <v-icon v-if="saveStatus === 'saving'" start>mdi-loading</v-icon>
      <v-icon v-else-if="saveStatus === 'saved'" start>mdi-check-circle</v-icon>
      <v-icon v-else-if="saveStatus === 'error'" start>mdi-alert-circle</v-icon>

      {{ saveStatusText }}
      <span v-if="lastSaved" class="ml-2 text-caption">
        (Last saved: {{ formatLastSaved(lastSaved) }})
      </span>
    </v-alert>

    <!-- Curation Form -->
    <v-form ref="form">
      <v-card>
        <v-card-title>Curate Gene: {{ gene?.symbol }}</v-card-title>

        <v-card-text>
          <!-- Evidence Fields -->
          <v-text-field
            v-model="curation.title"
            label="Curation Title"
            @input="markDirty"
          />

          <v-textarea
            v-model="curation.description"
            label="Description"
            rows="3"
            @input="markDirty"
          />

          <!-- Dynamic fields based on schema -->
          <component
            v-for="field in schemaFields"
            :key="field.id"
            :is="getFieldComponent(field.type)"
            v-model="curation.evidence_data[field.id]"
            :field="field"
            @update:modelValue="markDirty"
          />
        </v-card-text>

        <v-card-actions>
          <v-btn
            color="primary"
            :loading="isSaving"
            @click="saveDraft"
          >
            Save Draft
          </v-btn>

          <v-btn
            color="success"
            :disabled="!isValid"
            @click="submitCuration"
          >
            Submit for Review
          </v-btn>

          <v-spacer />

          <v-btn @click="cancel">Cancel</v-btn>
        </v-card-actions>
      </v-card>
    </v-form>
  </v-container>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAutoSave } from '@/composables/useAutoSave'
import { useCurationsStore } from '@/stores/curations'
import { useGenesStore } from '@/stores/genes'

const route = useRoute()
const router = useRouter()
const curationsStore = useCurationsStore()
const genesStore = useGenesStore()

const curation = ref({
  gene_id: null,
  scope_id: null,
  status: 'draft',
  title: '',
  description: '',
  evidence_data: {}
})

const gene = ref(null)
const schemaFields = ref([])

// Auto-save setup
const {
  isSaving,
  lastSaved,
  saveStatus,
  startAutoSave,
  stopAutoSave,
  markDirty,
  triggerSave
} = useAutoSave(saveDraftToBackend, {
  interval: 30000,      // Auto-save every 30 seconds
  debounceDelay: 2000,  // Debounce user input by 2 seconds
  enabled: true
})

const saveStatusText = computed(() => {
  switch (saveStatus.value) {
    case 'saving': return 'Saving draft...'
    case 'saved': return 'Draft saved'
    case 'error': return 'Failed to save draft'
    default: return ''
  }
})

// Save draft to backend (no validation)
async function saveDraftToBackend() {
  if (curation.value.id) {
    // Update existing draft
    await curationsStore.updateCuration(curation.value.id, {
      ...curation.value,
      status: 'draft'
    })
  } else {
    // Create new draft
    const created = await curationsStore.createCuration({
      ...curation.value,
      status: 'draft'
    })
    curation.value.id = created.id
  }
}

// Manual save draft
async function saveDraft() {
  await triggerSave()
}

// Submit curation (with validation)
async function submitCuration() {
  // Validate form
  const { valid } = await form.value.validate()
  if (!valid) return

  // Update status to submitted
  curation.value.status = 'submitted'
  await curationsStore.updateCuration(curation.value.id, curation.value)

  // Navigate to curation list
  router.push('/curations')
}

// Format last saved time
function formatLastSaved(date) {
  const seconds = Math.floor((new Date() - date) / 1000)
  if (seconds < 60) return `${seconds}s ago`
  const minutes = Math.floor(seconds / 60)
  if (minutes < 60) return `${minutes}m ago`
  return date.toLocaleTimeString()
}

// Warn before leaving with unsaved changes
function beforeUnloadHandler(e) {
  if (saveStatus.value === 'saving') {
    e.preventDefault()
    e.returnValue = 'You have unsaved changes. Are you sure you want to leave?'
  }
}

onMounted(async () => {
  // Load gene and schema
  const geneId = route.params.geneId
  gene.value = await genesStore.fetchGeneById(geneId)

  // Load existing draft or create new
  const curationId = route.params.curationId
  if (curationId) {
    curation.value = await curationsStore.fetchCurationById(curationId)
  } else {
    curation.value.gene_id = geneId
    curation.value.scope_id = route.query.scopeId
  }

  // Start auto-save
  startAutoSave()

  // Warn before leaving
  window.addEventListener('beforeunload', beforeUnloadHandler)
})

onBeforeUnmount(() => {
  stopAutoSave()
  window.removeEventListener('beforeunload', beforeUnloadHandler)
})
</script>
```

**3. Resume Draft List** (`frontend/src/views/DraftCurations.vue`)

```vue
<template>
  <v-container>
    <v-card>
      <v-card-title>Your Draft Curations</v-card-title>

      <v-card-text>
        <v-list v-if="drafts.length">
          <v-list-item
            v-for="draft in drafts"
            :key="draft.id"
            @click="resumeDraft(draft)"
          >
            <v-list-item-title>
              {{ draft.gene_symbol }} - {{ draft.title || 'Untitled' }}
            </v-list-item-title>

            <v-list-item-subtitle>
              Last edited: {{ formatDate(draft.updated_at) }}
            </v-list-item-subtitle>

            <template #append>
              <v-btn
                icon="mdi-delete"
                size="small"
                @click.stop="deleteDraft(draft.id)"
              />
            </template>
          </v-list-item>
        </v-list>

        <v-alert v-else type="info">
          No draft curations found.
        </v-alert>
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

const drafts = ref([])

onMounted(async () => {
  // Fetch user's draft curations
  drafts.value = await curationsStore.fetchCurations({
    status: 'draft',
    curator_id: 'me'  // Current user
  })
})

function resumeDraft(draft) {
  router.push(`/curations/${draft.id}/edit`)
}

async function deleteDraft(draftId) {
  if (confirm('Delete this draft? This cannot be undone.')) {
    await curationsStore.deleteCuration(draftId)
    drafts.value = drafts.value.filter(d => d.id !== draftId)
  }
}

function formatDate(dateString) {
  return new Date(dateString).toLocaleString()
}
</script>
```

### Backend API (Already Exists)

**Draft CRUD** (`backend/app/api/v1/endpoints/curations.py`)

```python
@router.patch("/curations/{curation_id}")
async def update_curation_draft(
    curation_id: int,
    curation_update: CurationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update curation (including drafts).

    For status='draft': No validation, allows partial data
    For status='submitted': Full validation required
    """
    curation = crud_curation.update(db, curation_id, curation_update)
    return curation
```

## Implementation Steps

1. **Create useAutoSave composable** (~100 lines)
   - Auto-save timer (30s interval)
   - Debounced save on user input (2s)
   - Save status indicator
   - Before-unload warning

2. **Update CurationForm component** (~50 lines changed)
   - Integrate useAutoSave
   - Add save status indicator
   - Wire up markDirty on field changes

3. **Create DraftCurations view** (~80 lines)
   - List user's drafts
   - Resume draft editing
   - Delete draft option

4. **Add route for drafts**
   ```javascript
   // frontend/src/router/index.js
   {
     path: '/drafts',
     component: () => import('@/views/DraftCurations.vue'),
     meta: { requiresAuth: true }
   }
   ```

5. **Update navigation**
   - Add "My Drafts" link to sidebar/header

6. **Update CLAUDE.md**
   ```markdown
   ## Draft Auto-Save

   All curation forms use auto-save (30s + debounced on input).
   Backend accepts partial data for status='draft'.
   ```

## Benefits

- **Data Loss Prevention**: Curators never lose work from browser crash/network issues
- **Work Resumption**: "Save and continue later" workflow
- **User Confidence**: Visual feedback ("Saving..." / "Saved") reduces anxiety
- **Production-Ready Pattern**: Based on standard UX patterns (Google Docs, Notion, etc.)

## Testing

```javascript
// tests/unit/useAutoSave.test.js
describe('useAutoSave', () => {
  it('should auto-save after interval', async () => {
    const saveFn = vi.fn()
    const { markDirty, startAutoSave } = useAutoSave(saveFn, { interval: 1000 })

    startAutoSave()
    markDirty()

    await new Promise(resolve => setTimeout(resolve, 1100))
    expect(saveFn).toHaveBeenCalled()
  })

  it('should debounce rapid changes', async () => {
    const saveFn = vi.fn()
    const { markDirty } = useAutoSave(saveFn, { debounceDelay: 500 })

    // Rapid changes
    markDirty()
    markDirty()
    markDirty()

    await new Promise(resolve => setTimeout(resolve, 600))
    expect(saveFn).toHaveBeenCalledTimes(1) // Debounced to 1 call
  })
})
```

## Dependencies

- `lodash-es` for debounce (likely already in project)
- No backend dependencies (already supports drafts)

## Acceptance Criteria

- [ ] useAutoSave composable implemented and tested
- [ ] CurationForm integrates auto-save with visual indicator
- [ ] Auto-save triggers every 30 seconds if dirty
- [ ] User input debounced (saves 2 seconds after last change)
- [ ] DraftCurations view lists user's drafts
- [ ] Resume draft functionality working
- [ ] Before-unload warning when unsaved changes exist
- [ ] "My Drafts" navigation link added
- [ ] Unit tests for useAutoSave composable
- [ ] Manual testing: Data persists after browser refresh

---

**Impact**: Directly improves curator experience, prevents frustration from data loss. This is a **high-value curation feature**, not infrastructure optimization.
