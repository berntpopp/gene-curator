# Gene Curator - Complete UI Implementation Plan (Production-Ready)

**Date**: 2025-10-15  
**Version**: 2.0 (Comprehensive - incorporates critical infrastructure)  
**Status**: Ready for Implementation  
**Timeline**: 6 weeks (43 days) + 1 week buffer

---

## Executive Summary

This plan delivers a **production-ready UI/UX system** by addressing 55 critical issues identified during comprehensive review. The implementation prioritizes **data integrity, user experience, and security** over rapid feature delivery.

### What Makes This Production-Ready

**Critical Infrastructure (Week 1)**:
- ✅ Form recovery system (localStorage auto-save)
- ✅ Conflict resolution UI (optimistic locking)
- ✅ Undo/redo system (command pattern)
- ✅ Session timeout handler (5-minute warning)
- ✅ Skeleton screens (zero layout shift)
- ✅ Error boundaries (graceful failures)

**Fixed UX Anti-Patterns**:
- ✅ Validation strategy: On-blur (NOT real-time)
- ✅ UI pattern: Drawers (NOT dialog overload)
- ✅ Scope creation: Single form with progressive disclosure (NOT 4-step wizard)
- ✅ Responsive: Card/table toggle (mobile-friendly)
- ✅ Form composition: Shared components (DRY principle)

**Security & Performance**:
- ✅ XSS prevention (DOMPurify)
- ✅ Optimistic locking UI
- ✅ Virtual scrolling (>100 items)
- ✅ Performance budget (<3s load, >90 Lighthouse)

---

## Timeline: 6 Weeks (43 Days)

| Week | Focus | Days | Deliverables |
|------|-------|------|--------------|
| **1** | Critical Infrastructure | 5 | Form recovery, undo/redo, conflict resolution, session timeout, skeletons, error boundaries |
| **2-3** | Core Forms (with fixes) | 10 | PrecurationForm, CurationForm, ClinGenScoreCard using proper patterns |
| **4** | UX Patterns & Dashboard | 7 | Drawer components, simplified scope creation, GeneList, CurationList |
| **5** | Features & Polish | 6 | Notifications, empty states, keyboard shortcuts, accessibility |
| **6** | Testing & Documentation | 10 | Component tests, E2E tests, performance testing, documentation |
| **Buffer** | Contingency | 5 | Bug fixes, performance optimization, final polish |

---

## Part 1: Critical Infrastructure (Week 1 - 5 Days)

### Day 1-2: Data Integrity Systems

#### 1.1 Form Recovery System (`useFormRecovery.js`)

**Purpose**: Prevent data loss from browser crashes/navigation

```javascript
// frontend/src/composables/useFormRecovery.js
import { ref, watch, onMounted, onBeforeUnmount } from 'vue'
import { useLogger } from './useLogger'

export function useFormRecovery(formId, formData, options = {}) {
  const logger = useLogger()
  const recoveryKey = `form_recovery_${formId}`
  const maxAge = options.maxAge || 24 * 60 * 60 * 1000 // 24 hours
  const saveInterval = options.saveInterval || 5000 // 5 seconds

  const showRecoveryDialog = ref(false)
  const recoveryData = ref(null)
  const lastSaved = ref(null)

  let saveTimer = null

  function saveToLocalStorage() {
    try {
      const snapshot = {
        data: JSON.parse(JSON.stringify(formData.value)),
        timestamp: new Date().toISOString(),
        url: window.location.href
      }
      localStorage.setItem(recoveryKey, JSON.stringify(snapshot))
      lastSaved.value = snapshot.timestamp
    } catch (error) {
      logger.error('Failed to save form', { formId, error: error.message })
    }
  }

  onMounted(() => {
    try {
      const saved = localStorage.getItem(recoveryKey)
      if (saved) {
        const snapshot = JSON.parse(saved)
        const age = Date.now() - new Date(snapshot.timestamp).getTime()

        if (age < maxAge) {
          recoveryData.value = snapshot.data
          showRecoveryDialog.value = true
        } else {
          localStorage.removeItem(recoveryKey)
        }
      }
    } catch (error) {
      logger.error('Failed to check recovery', { formId, error: error.message })
    }

    saveTimer = setInterval(saveToLocalStorage, saveInterval)
  })

  onBeforeUnmount(() => {
    if (saveTimer) clearInterval(saveTimer)
  })

  watch(formData, saveToLocalStorage, { deep: true })

  function restoreRecovery() {
    if (recoveryData.value) {
      Object.assign(formData.value, recoveryData.value)
      showRecoveryDialog.value = false
    }
  }

  function discardRecovery() {
    localStorage.removeItem(recoveryKey)
    recoveryData.value = null
    showRecoveryDialog.value = false
  }

  function clearRecovery() {
    localStorage.removeItem(recoveryKey)
    lastSaved.value = null
  }

  return {
    showRecoveryDialog,
    recoveryData,
    lastSaved,
    restoreRecovery,
    discardRecovery,
    clearRecovery
  }
}
```

#### 1.2 Undo/Redo System

**Files**: `stores/history.js` + `composables/useHistory.js`

```javascript
// frontend/src/stores/history.js
import { defineStore } from 'pinia'

export const useHistoryStore = defineStore('history', {
  state: () => ({
    contexts: new Map(),
    maxHistory: 50
  }),

  actions: {
    pushState(context, action, previousState, newState) {
      if (!this.contexts.has(context)) {
        this.contexts.set(context, { past: [], future: [] })
      }

      const history = this.contexts.get(context)
      history.past.push({
        action,
        previousState: JSON.parse(JSON.stringify(previousState)),
        newState: JSON.parse(JSON.stringify(newState)),
        timestamp: Date.now()
      })

      if (history.past.length > this.maxHistory) {
        history.past.shift()
      }

      history.future = []
    },

    undo(context) {
      const history = this.contexts.get(context)
      if (!history || history.past.length === 0) return null

      const action = history.past.pop()
      history.future.push(action)
      return action.previousState
    },

    redo(context) {
      const history = this.contexts.get(context)
      if (!history || history.future.length === 0) return null

      const action = history.future.pop()
      history.past.push(action)
      return action.newState
    }
  }
})
```

### Day 3-4: Conflict Resolution & Session Management

#### 1.3 Optimistic Locking Composable

```javascript
// frontend/src/composables/useOptimisticLocking.js
import { ref } from 'vue'

export function useOptimisticLocking() {
  const conflictDetected = ref(false)
  const conflictData = ref(null)

  async function saveWithLockCheck(apiCall, data, currentVersion) {
    try {
      const payload = { ...data, lock_version: currentVersion }
      return await apiCall(payload)
    } catch (error) {
      if (error.response?.status === 409) {
        conflictDetected.value = true
        conflictData.value = {
          yourChanges: data,
          theirChanges: error.response.data.current_state,
          theirVersion: error.response.data.lock_version
        }
        throw error
      }
      throw error
    }
  }

  function resolveConflict(resolution) {
    const resolved = { ...conflictData.value, resolution }
    conflictDetected.value = false
    conflictData.value = null
    return resolved
  }

  return {
    conflictDetected,
    conflictData,
    saveWithLockCheck,
    resolveConflict
  }
}
```

#### 1.4 Session Timeout Handler

```javascript
// frontend/src/composables/useSessionTimeout.js
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { useAuthStore } from '@/stores/auth'

export function useSessionTimeout() {
  const authStore = useAuthStore()
  const showWarning = ref(false)
  const timeRemaining = ref(0)
  const warningThreshold = 5 * 60 * 1000 // 5 minutes

  let checkInterval = null

  function checkTokenExpiry() {
    if (!authStore.token) return

    const remaining = authStore.tokenExpiresAt - Date.now()
    timeRemaining.value = Math.floor(remaining / 1000)

    if (remaining < warningThreshold && remaining > 0) {
      if (!showWarning.value) showWarning.value = true
    } else if (remaining <= 0) {
      showWarning.value = false
      authStore.logout()
    }
  }

  async function extendSession() {
    try {
      await authStore.refreshToken()
      showWarning.value = false
    } catch (error) {
      // Handle error
    }
  }

  onMounted(() => {
    checkInterval = setInterval(checkTokenExpiry, 60000)
    checkTokenExpiry()
  })

  onBeforeUnmount(() => {
    if (checkInterval) clearInterval(checkInterval)
  })

  return { showWarning, timeRemaining, extendSession }
}
```

### Day 5: Skeleton Screens & Error Boundaries

#### 1.5 Table Skeleton Component

```vue
<!-- frontend/src/components/skeletons/TableSkeleton.vue -->
<template>
  <v-data-table
    :items="displayItems"
    :headers="headers"
    :loading="false"
  >
    <template #item="{ item }">
      <tr v-if="item.isSkeleton">
        <td v-for="header in headers" :key="header.key">
          <v-skeleton-loader type="text" />
        </td>
      </tr>
      <slot v-else name="item" :item="item" />
    </template>
  </v-data-table>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  loading: Boolean,
  items: Array,
  headers: Array,
  skeletonCount: { type: Number, default: 5 }
})

const displayItems = computed(() => {
  if (props.loading) {
    return Array.from({ length: props.skeletonCount }, (_, i) => ({
      isSkeleton: true,
      id: `skeleton-${i}`
    }))
  }
  return props.items
})
</script>
```

#### 1.6 Error Boundary

```vue
<!-- frontend/src/components/ErrorBoundary.vue -->
<template>
  <div v-if="error" class="error-boundary">
    <v-alert
      type="error"
      variant="tonal"
      closable
      @click:close="reset"
    >
      <v-alert-title>Something went wrong</v-alert-title>
      <div>{{ error.message }}</div>
      <template #append>
        <v-btn size="small" @click="reset">Try Again</v-btn>
      </template>
    </v-alert>
  </div>
  <slot v-else />
</template>

<script setup>
import { ref, onErrorCaptured } from 'vue'
import { useLogger } from '@/composables/useLogger'

const logger = useLogger()
const error = ref(null)

onErrorCaptured((err, instance, info) => {
  error.value = err
  logger.error('Component error', { error: err.message, info })
  return false
})

function reset() {
  error.value = null
}
</script>
```

---

## Part 2: Core Forms (Week 2-3 - 10 Days)

### Validation Strategy (CRITICAL FIX)

**❌ WRONG** (Real-time validation - antipattern):
```vue
<v-text-field @input="validateGene" />  <!-- Fires 10+ times/second -->
```

**✅ RIGHT** (On-blur validation):
```vue
<v-text-field
  @blur="validateGene"           <!-- Fires once when done -->
  @keydown.enter="validateGene"  <!-- Or on Enter -->
/>
```

### Day 6-8: Shared Evidence Components

```vue
<!-- frontend/src/components/evidence/PMIDInput.vue -->
<template>
  <v-combobox
    v-model="pmids"
    label="PubMed IDs"
    multiple
    chips
    @blur="validatePMIDs"
  >
    <template #chip="{ item }">
      <v-chip :color="getChipColor(item)">
        <v-icon v-if="isValidating(item)" size="small">
          mdi-loading mdi-spin
        </v-icon>
        <v-icon v-else-if="isValid(item)" size="small">
          mdi-check-circle
        </v-icon>
        {{ item }}
      </v-chip>
    </template>
  </v-combobox>
</template>

<script setup>
import { ref } from 'vue'
import { useExternalValidationStore } from '@/stores/externalValidation'

const props = defineProps({
  modelValue: Array
})

const emit = defineEmits(['update:modelValue'])
const validationStore = useExternalValidationStore()
const pmids = ref(props.modelValue || [])

async function validatePMIDs() {
  if (pmids.value.length === 0) return
  await validationStore.validateBatch('pubmed', pmids.value)
}

function isValid(pmid) {
  const result = validationStore.getCachedResult('pubmed', pmid)
  return result?.is_valid === true
}

function getChipColor(pmid) {
  if (isValid(pmid)) return 'success'
  return 'error'
}
</script>
```

### Day 9-11: PrecurationForm.vue

```vue
<!-- frontend/src/components/PrecurationForm.vue -->
<template>
  <error-boundary>
    <v-form ref="formRef" @submit.prevent="handleSubmit">
      <v-card>
        <v-card-title>
          ClinGen Precuration
          <v-chip v-if="isDraft" color="warning" size="small">Draft</v-chip>
        </v-card-title>

        <v-card-text>
          <!-- Gene Selection -->
          <v-text-field
            v-model="formData.gene_symbol"
            label="Gene Symbol"
            @blur="validateGene"
            required
          />

          <!-- Other fields... -->

          <!-- Auto-save indicator -->
          <v-alert v-if="lastSaved" type="success" density="compact">
            Auto-saved {{ formatTime(lastSaved) }}
          </v-alert>
        </v-card-text>

        <v-card-actions>
          <v-btn @click="handleCancel">Cancel</v-btn>
          <v-spacer />

          <!-- Undo/Redo -->
          <v-btn-group variant="outlined" density="compact">
            <v-btn :disabled="!canUndo" @click="undo">
              <v-icon>mdi-undo</v-icon>
            </v-btn>
            <v-btn :disabled="!canRedo" @click="redo">
              <v-icon>mdi-redo</v-icon>
            </v-btn>
          </v-btn-group>

          <v-btn variant="outlined" :loading="savingDraft" @click="handleSaveDraft">
            Save Draft
          </v-btn>
          <v-btn color="primary" type="submit" :loading="submitting">
            Submit
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-form>

    <!-- Recovery Dialog -->
    <form-recovery-dialog
      v-model="showRecoveryDialog"
      @restore="restoreRecovery"
      @discard="discardRecovery"
    />

    <!-- Conflict Resolution -->
    <conflict-resolution-dialog
      v-model="conflictDetected"
      :your-changes="conflictData?.yourChanges"
      :their-changes="conflictData?.theirChanges"
      @resolve="handleConflictResolution"
    />

    <!-- Session Timeout Warning -->
    <session-timeout-warning
      v-model="showTimeoutWarning"
      :time-remaining="timeRemaining"
      @extend="extendSession"
    />
  </error-boundary>
</template>

<script setup>
import { ref, watch } from 'vue'
import { useFormRecovery } from '@/composables/useFormRecovery'
import { useHistory } from '@/composables/useHistory'
import { useOptimisticLocking } from '@/composables/useOptimisticLocking'
import { useSessionTimeout } from '@/composables/useSessionTimeout'

const formData = ref({})

// Form recovery
const { showRecoveryDialog, lastSaved, restoreRecovery, discardRecovery, clearRecovery } = 
  useFormRecovery('precuration-new', formData)

// Undo/redo
const { canUndo, canRedo, recordAction, undo: undoAction, redo: redoAction } = 
  useHistory('precuration-new', (state) => {
    formData.value = { ...state }
  })

watch(formData, (newVal, oldVal) => {
  if (oldVal) recordAction('edit', oldVal, newVal)
}, { deep: true })

// Optimistic locking
const { conflictDetected, conflictData, saveWithLockCheck } = useOptimisticLocking()

// Session timeout
const { showTimeoutWarning, timeRemaining, extendSession } = useSessionTimeout()

// ... rest of implementation
</script>
```

### Day 12-16: CurationForm.vue

Similar pattern to PrecurationForm, but with:
- Tabbed evidence sections (Genetic, Experimental, Contradictory)
- Real-time score calculation via `useScoring` composable
- Evidence item management

### Day 17-18: ClinGenScoreCard.vue

```vue
<!-- frontend/src/components/clingen/ClinGenScoreCard.vue -->
<template>
  <v-card>
    <v-card-title>
      ClinGen SOP v11 Score
      <v-chip :color="classificationColor" size="large">
        {{ classification }}
      </v-chip>
    </v-card-title>

    <v-card-text>
      <!-- Total Score -->
      <div class="text-center">
        <div class="text-h2" :style="{ color: classificationColor }">
          {{ totalScore.toFixed(2) }}
        </div>
        <div class="text-caption">out of 18 points</div>
        <v-progress-linear
          :model-value="(totalScore / 18) * 100"
          :color="classificationColor"
          height="12"
          class="mt-2"
        />
      </div>

      <!-- Score Breakdown -->
      <v-row class="mt-4">
        <v-col cols="6">
          <v-card variant="outlined">
            <v-card-text>
              <div class="text-caption">Genetic Evidence</div>
              <div class="text-h5">{{ geneticScore.toFixed(2) }}</div>
              <v-progress-linear
                :model-value="(geneticScore / 12) * 100"
                color="primary"
                height="4"
              />
              <div class="text-caption">max 12 points</div>
            </v-card-text>
          </v-card>
        </v-col>
        <v-col cols="6">
          <v-card variant="outlined">
            <v-card-text>
              <div class="text-caption">Experimental Evidence</div>
              <div class="text-h5">{{ experimentalScore.toFixed(2) }}</div>
              <v-progress-linear
                :model-value="(experimentalScore / 6) * 100"
                color="secondary"
                height="4"
              />
              <div class="text-caption">max 6 points</div>
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>

      <!-- Expandable Category Breakdown -->
      <v-expansion-panels class="mt-4">
        <v-expansion-panel>
          <v-expansion-panel-title>
            Detailed Breakdown
          </v-expansion-panel-title>
          <v-expansion-panel-text>
            <!-- Category scores -->
          </v-expansion-panel-text>
        </v-expansion-panel>
      </v-expansion-panels>
    </v-card-text>
  </v-card>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  breakdown: { type: Object, required: true }
})

const totalScore = computed(() => props.breakdown.total_score || 0)
const geneticScore = computed(() => props.breakdown.genetic_total || 0)
const experimentalScore = computed(() => props.breakdown.experimental_total || 0)
const classification = computed(() => props.breakdown.classification || 'No Known')

const classificationColor = computed(() => {
  switch (classification.value) {
    case 'Definitive': return 'success'
    case 'Strong': return 'info'
    case 'Moderate': return 'warning'
    case 'Limited': return 'grey'
    default: return 'error'
  }
})
</script>
```

---

## Part 3: UX Patterns & Dashboard (Week 4 - 7 Days)

### Day 19-20: Replace Dialogs with Drawers

**Pattern** (Fix dialog overload antipattern):

```vue
<!-- WRONG: Modal dialog blocks entire UI -->
<v-dialog v-model="showAssign" max-width="600">
  <assign-form />
</v-dialog>

<!-- RIGHT: Slide-over drawer, non-blocking -->
<v-navigation-drawer
  v-model="showAssign"
  location="right"
  temporary
  width="500"
>
  <v-toolbar density="compact" color="primary">
    <v-toolbar-title>Assign Genes</v-toolbar-title>
    <v-spacer />
    <v-btn icon @click="showAssign = false">
      <v-icon>mdi-close</v-icon>
    </v-btn>
  </v-toolbar>
  <v-card-text>
    <assign-form @success="showAssign = false" />
  </v-card-text>
</v-navigation-drawer>
```

**Components to Convert**:
- AssignGenesDialog → AssignGenesDrawer
- InviteMemberDialog → InviteMemberDrawer
- EvidenceItemDialog → EvidenceItemDrawer

### Day 21-22: Simplified Scope Creation

**WRONG** (4-step wizard - 40-60% abandonment):
```
Step 1 → Step 2 → Step 3 → Step 4
```

**RIGHT** (Single form with progressive disclosure - <20% abandonment):

```vue
<template>
  <v-form>
    <!-- Essential fields (always visible) -->
    <v-text-field v-model="name" label="Scope Name" required />
    <v-textarea v-model="description" rows="3" />

    <!-- Optional sections (expandable) -->
    <v-expansion-panels class="mt-4">
      <v-expansion-panel>
        <v-expansion-panel-title>
          Add Genes (Optional)
          <v-chip v-if="genes.length > 0" size="small">
            {{ genes.length }} selected
          </v-chip>
        </v-expansion-panel-title>
        <v-expansion-panel-text>
          <v-autocomplete
            v-model="genes"
            :items="availableGenes"
            multiple
            chips
          />
          <v-file-input
            v-model="geneFile"
            label="Or upload CSV"
            hint="You can add genes later"
          />
        </v-expansion-panel-text>
      </v-expansion-panel>

      <v-expansion-panel>
        <v-expansion-panel-title>
          Invite Members (Optional)
          <v-chip v-if="invites.length > 0" size="small">
            {{ invites.length }} invited
          </v-chip>
        </v-expansion-panel-title>
        <v-expansion-panel-text>
          <!-- Invite form -->
        </v-expansion-panel-text>
      </v-expansion-panel>
    </v-expansion-panels>

    <v-btn color="primary" @click="createScope">Create Scope</v-btn>
  </v-form>
</template>
```

### Day 23-24: Responsive Card Layouts

```vue
<!-- Toggle between cards (mobile) and table (desktop) -->
<template>
  <v-container fluid>
    <v-toolbar flat>
      <v-spacer />
      <v-btn-toggle v-model="viewMode">
        <v-btn value="cards"><v-icon>mdi-view-grid</v-icon></v-btn>
        <v-btn value="table"><v-icon>mdi-table</v-icon></v-btn>
      </v-btn-toggle>
    </v-toolbar>

    <!-- Card View -->
    <v-row v-if="viewMode === 'cards'">
      <v-col v-for="item in items" cols="12" sm="6" md="4">
        <item-card :item="item" />
      </v-col>
    </v-row>

    <!-- Table View -->
    <table-skeleton v-else :loading="loading" :items="items" :headers="headers">
      <template #item="{ item }">
        <tr>
          <td>{{ item.name }}</td>
          <td>{{ item.status }}</td>
        </tr>
      </template>
    </table-skeleton>
  </v-container>
</template>
```

### Day 24-25: GeneList & CurationList Components

```vue
<!-- frontend/src/components/GeneList.vue -->
<template>
  <v-container fluid>
    <!-- Filters -->
    <v-row dense>
      <v-col cols="12" md="4">
        <v-text-field
          v-model="search"
          prepend-inner-icon="mdi-magnify"
          label="Search genes"
          variant="outlined"
          density="compact"
        />
      </v-col>
      <v-col cols="12" md="3">
        <v-select
          v-model="filterCurator"
          :items="curators"
          label="Curator"
          clearable
        />
      </v-col>
      <v-col cols="12" md="3">
        <v-select
          v-model="filterStatus"
          :items="statuses"
          label="Status"
          clearable
        />
      </v-col>
      <v-col cols="12" md="2">
        <v-btn color="primary" block @click="showAssignDrawer = true">
          <v-icon start>mdi-plus</v-icon>
          Assign
        </v-btn>
      </v-col>
    </v-row>

    <!-- Table with skeleton loading -->
    <table-skeleton
      :loading="loading"
      :items="filteredGenes"
      :headers="headers"
    >
      <template #item="{ item }">
        <tr>
          <td>
            <router-link :to="`/genes/${item.gene_id}`">
              {{ item.gene_symbol }}
            </router-link>
          </td>
          <td>
            <v-chip v-if="item.curator" size="small">
              {{ item.curator_name }}
            </v-chip>
            <v-chip v-else variant="outlined" size="small">
              Unassigned
            </v-chip>
          </td>
          <td>
            <v-chip :color="getStatusColor(item.status)" size="small">
              {{ item.status }}
            </v-chip>
          </td>
          <td>{{ formatDate(item.due_date) }}</td>
          <td>
            <v-menu>
              <template #activator="{ props }">
                <v-btn icon size="small" v-bind="props">
                  <v-icon>mdi-dots-vertical</v-icon>
                </v-btn>
              </template>
              <v-list>
                <v-list-item @click="viewGene(item)">
                  <template #prepend><v-icon>mdi-eye</v-icon></template>
                  <v-list-item-title>View</v-list-item-title>
                </v-list-item>
                <v-list-item @click="startCuration(item)">
                  <template #prepend><v-icon>mdi-pencil</v-icon></template>
                  <v-list-item-title>Start Curation</v-list-item-title>
                </v-list-item>
              </v-list>
            </v-menu>
          </td>
        </tr>
      </template>
    </table-skeleton>

    <!-- Empty State -->
    <v-alert v-if="!loading && filteredGenes.length === 0" type="info">
      <v-alert-title>No genes assigned</v-alert-title>
      <div>Start by assigning genes to curators.</div>
      <template #append>
        <v-btn color="primary" @click="showAssignDrawer = true">
          Assign Genes
        </v-btn>
      </template>
    </v-alert>

    <!-- Assign Drawer -->
    <assign-genes-drawer
      v-model="showAssignDrawer"
      :scope-id="scopeId"
      @assigned="refreshGenes"
    />
  </v-container>
</template>
```

---

## Part 4: Features & Polish (Week 5 - 6 Days)

### Day 26-27: Notification System

```javascript
// frontend/src/stores/notifications.js
export const useNotificationStore = defineStore('notifications', {
  state: () => ({
    notifications: [],
    unreadCount: 0
  }),

  actions: {
    addToast(message, type = 'info') {
      const toast = {
        id: Date.now(),
        message,
        type,
        timestamp: new Date()
      }
      this.notifications.unshift(toast)
      
      // Auto-dismiss after 5 seconds
      setTimeout(() => {
        this.dismissToast(toast.id)
      }, 5000)
    },

    dismissToast(id) {
      const index = this.notifications.findIndex(n => n.id === id)
      if (index !== -1) {
        this.notifications.splice(index, 1)
      }
    }
  }
})
```

### Day 28-29: Empty States & Success Animations

```vue
<!-- Empty State Pattern -->
<v-alert v-if="!loading && items.length === 0" type="info" border="start">
  <v-alert-title>
    <v-icon size="large">mdi-inbox</v-icon>
    No {{ itemType }} found
  </v-alert-title>
  <div>{{ emptyMessage }}</div>
  <template #append>
    <v-btn color="primary" @click="primaryAction">
      <v-icon start>mdi-plus</v-icon>
      {{ actionLabel }}
    </v-btn>
  </template>
</v-alert>

<!-- Success Dialog -->
<v-dialog v-model="showSuccess" max-width="400">
  <v-card class="text-center pa-6">
    <v-icon color="success" size="80">mdi-check-circle</v-icon>
    <v-card-title>Success!</v-card-title>
    <v-card-text>{{ successMessage }}</v-card-text>
    <v-btn color="primary" @click="showSuccess = false">Continue</v-btn>
  </v-card>
</v-dialog>
```

### Day 30-31: Keyboard Shortcuts & Accessibility

```javascript
// frontend/src/composables/useKeyboardShortcuts.js
export function useKeyboardShortcuts(shortcuts) {
  function handleKeydown(event) {
    const key = event.key.toLowerCase()
    const ctrl = event.ctrlKey || event.metaKey
    const shift = event.shiftKey

    // Match shortcut
    for (const [combo, handler] of Object.entries(shortcuts)) {
      if (matchesCombo(combo, key, ctrl, shift)) {
        event.preventDefault()
        handler()
        break
      }
    }
  }

  onMounted(() => {
    window.addEventListener('keydown', handleKeydown)
  })

  onBeforeUnmount(() => {
    window.removeEventListener('keydown', handleKeydown)
  })
}

// Usage in form:
useKeyboardShortcuts({
  'ctrl+s': handleSaveDraft,
  'ctrl+enter': handleSubmit,
  'ctrl+z': undo,
  'ctrl+shift+z': redo,
  'esc': handleCancel
})
```

**Accessibility Checklist**:
- [ ] All interactive elements keyboard-navigable
- [ ] Focus indicators visible (outline: 2px solid)
- [ ] ARIA labels on icon-only buttons
- [ ] Color contrast ≥ 4.5:1 (WCAG AA)
- [ ] Screen reader announcements
- [ ] Skip navigation links
- [ ] Form labels properly associated

---

## Part 5: Testing & Documentation (Week 6 - 10 Days)

### Day 32-36: Component Testing

```javascript
// frontend/tests/components/PrecurationForm.spec.js
import { describe, it, expect, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia } from 'pinia'
import PrecurationForm from '@/components/PrecurationForm.vue'

describe('PrecurationForm.vue', () => {
  let wrapper

  beforeEach(() => {
    wrapper = mount(PrecurationForm, {
      global: { plugins: [createPinia()] }
    })
  })

  it('renders form fields', () => {
    expect(wrapper.find('[data-test="gene-symbol"]').exists()).toBe(true)
    expect(wrapper.find('[data-test="rationale"]').exists()).toBe(true)
  })

  it('recovers data from localStorage', () => {
    localStorage.setItem('form_recovery_precuration-new', JSON.stringify({
      data: { gene_symbol: 'BRCA1' },
      timestamp: new Date().toISOString()
    }))

    expect(wrapper.vm.showRecoveryDialog).toBe(true)
  })

  it('validates required fields', async () => {
    await wrapper.find('form').trigger('submit')
    expect(wrapper.vm.isValid).toBe(false)
  })

  it('enables undo after edit', async () => {
    await wrapper.setData({ formData: { gene_symbol: 'BRCA1' } })
    expect(wrapper.vm.canUndo).toBe(true)
  })
})
```

### Day 37-38: Performance Testing

**Performance Budget**:
- Initial page load: < 3 seconds
- Time to interactive: < 5 seconds
- Lighthouse score: > 90
- Bundle size: < 500KB (gzipped)

**Testing Tools**:
- Lighthouse CI
- Webpack Bundle Analyzer
- Chrome DevTools Performance

**Optimization Checklist**:
- [ ] Lazy load routes
- [ ] Code splitting for large components
- [ ] Virtual scrolling for long lists (>100 items)
- [ ] Debounce expensive operations
- [ ] Memoize computed properties

### Day 39-41: Documentation

1. **USER_GUIDE_CURATION.md** (8 hours)
2. **COMPONENT_REFERENCE.md** (8 hours)
3. **DEPLOYMENT_GUIDE.md** (4 hours)
4. **API_INTEGRATION_GUIDE.md** (4 hours)

### Day 42-43: Buffer & Final Polish

Reserved for:
- Bug fixes from testing
- Performance optimizations
- Accessibility improvements
- Code review feedback
- Deployment preparation

---

## Success Metrics

### Quantitative
1. Time to First Curation: < 5 minutes
2. Form Completion Rate: > 90%
3. Validation Error Rate: < 10%
4. Page Load Time: < 3 seconds
5. Lighthouse Score: > 90
6. Test Coverage: > 70%

### Qualitative
1. User Satisfaction: > 4.0/5.0
2. Support Tickets: < 5 per 100 curations
3. Workflow Adoption: > 80%
4. WCAG 2.1 AA compliant

---

## Risks & Mitigation

### High Risk
1. **Timeline Slippage**
   - Mitigation: Daily standup, weekly milestones, buffer days
   - Contingency: Cut low-priority features

2. **Performance Issues**
   - Mitigation: Performance budget, continuous monitoring
   - Contingency: Virtual scrolling, lazy loading

### Medium Risk
1. **External API Failures**
   - Mitigation: Caching, timeouts, fallbacks
   - Contingency: Manual validation bypass

2. **Browser Compatibility**
   - Mitigation: Test in Chrome, Firefox, Safari, Edge
   - Contingency: Polyfills, progressive enhancement

---

## Next Steps

### Week 1 (Starting Monday)
1. Review and approve this plan
2. Set up development environment
3. Create GitHub issues
4. Begin: Form Recovery System

### Daily Workflow
- Morning: Review goals
- Work: Implement, test
- Evening: Commit, update progress
- Friday: Demo features

---

**Document Version**: 2.0 (Production-Ready)
**Last Updated**: 2025-10-15
**Estimated Completion**: 2025-12-09 (6 weeks + buffer)

**This plan addresses all 55 critical issues and delivers a production-ready, secure, performant system.**
