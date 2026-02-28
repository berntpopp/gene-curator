# Enhancement #011 - Improvement Plan

**Date:** 2026-01-12
**Author:** Claude Code (Expert Review)
**Based on:** UI Gap Analysis Report + Vue 3/Pinia/Vuetify Best Practices

---

## Overview

This plan addresses the critical bugs and missing functionality identified in the UI Gap Analysis Report, following industry best practices from Vue 3, Pinia, and Vuetify documentation.

---

## Phase 1: Critical Bug Fixes (Priority: Immediate)

### 1.1 Fix SchemaManagement TypeError

**Problem:** `formatType()` and `formatStatus()` throw errors when values are undefined.

**Solution:** Implement defensive programming with null safety.

**File:** `src/views/SchemaManagement.vue`

```javascript
// BEFORE (broken)
const formatType = type => {
  return type.charAt(0).toUpperCase() + type.slice(1)
}

// AFTER (defensive with fallback)
const formatType = type => {
  if (!type) return 'Unknown'
  return type.charAt(0).toUpperCase() + type.slice(1)
}

const formatStatus = status => {
  if (!status) return 'Draft'  // Sensible default
  return status.charAt(0).toUpperCase() + status.slice(1)
}
```

**Additional Fix - Map backend field names:**
```javascript
// In computed property that processes schemas
const processedSchemas = computed(() => {
  return (schemasStore.schemas || []).map(schema => ({
    ...schema,
    type: schema.schema_type || schema.type || 'unknown',
    status: schema.is_active ? 'active' : 'draft'
  }))
})
```

**Best Practice Reference:** [Vue 3 Computed Properties](https://vuejs.org/guide/essentials/computed.html) - Use computed properties to transform data defensively.

---

### 1.2 Implement WorkflowManagement Data Loading

**Problem:** `workflowStore` is missing `workflowPairs` and `workflowStages` state/actions.

**Solution:** Extend workflow store following Pinia best practices.

**File:** `src/stores/workflow.js`

```javascript
import { defineStore } from 'pinia'
import { workflowAPI } from '@/api'

export const useWorkflowStore = defineStore('workflow', {
  state: () => ({
    // Existing state
    analytics: null,
    statistics: null,
    peerReviewers: [],
    curationTransitions: {},
    curationHistory: {},
    loading: false,
    error: null,
    currentWorkflowStage: null,

    // NEW: Add workflow pairs and stages
    workflowPairs: [],
    workflowStages: [],
    workflowPairsLoading: false,
    workflowStagesLoading: false
  }),

  getters: {
    // Existing getters...

    // NEW: Active workflow pairs
    activeWorkflowPairs: (state) => {
      return state.workflowPairs.filter(wp => wp.is_active)
    },

    // NEW: Get workflow pair by ID
    getWorkflowPairById: (state) => (id) => {
      return state.workflowPairs.find(wp => wp.id === id)
    }
  },

  actions: {
    // Existing actions...

    // NEW: Fetch workflow pairs
    async fetchWorkflowPairs(params = {}) {
      this.workflowPairsLoading = true
      this.error = null

      try {
        const response = await workflowAPI.getWorkflowPairs(params)
        this.workflowPairs = response.workflow_pairs || response || []
        return this.workflowPairs
      } catch (error) {
        this.error = error.message || 'Failed to fetch workflow pairs'
        console.error('fetchWorkflowPairs error:', error)
        throw error
      } finally {
        this.workflowPairsLoading = false
      }
    },

    // NEW: Fetch workflow stages
    async fetchWorkflowStages() {
      this.workflowStagesLoading = true
      this.error = null

      try {
        const response = await workflowAPI.getWorkflowStages()
        this.workflowStages = response || []
        return this.workflowStages
      } catch (error) {
        this.error = error.message || 'Failed to fetch workflow stages'
        console.error('fetchWorkflowStages error:', error)
        throw error
      } finally {
        this.workflowStagesLoading = false
      }
    },

    // NEW: Create workflow pair
    async createWorkflowPair(data) {
      this.loading = true
      this.error = null

      try {
        const result = await workflowAPI.createWorkflowPair(data)
        // Refresh list after creation
        await this.fetchWorkflowPairs()
        return result
      } catch (error) {
        this.error = error.message || 'Failed to create workflow pair'
        throw error
      } finally {
        this.loading = false
      }
    },

    // NEW: Delete workflow pair
    async deleteWorkflowPair(id) {
      this.loading = true
      this.error = null

      try {
        await workflowAPI.deleteWorkflowPair(id)
        // Remove from local state
        this.workflowPairs = this.workflowPairs.filter(wp => wp.id !== id)
      } catch (error) {
        this.error = error.message || 'Failed to delete workflow pair'
        throw error
      } finally {
        this.loading = false
      }
    }
  }
})
```

**File:** `src/api/workflow.js` (add missing API methods)

```javascript
export const workflowAPI = {
  // Existing methods...

  // NEW: Workflow pairs CRUD
  async getWorkflowPairs(params = {}) {
    const response = await apiClient.get('/schemas/workflow-pairs', { params })
    return response.data
  },

  async createWorkflowPair(data) {
    const response = await apiClient.post('/schemas/workflow-pairs', data)
    return response.data
  },

  async deleteWorkflowPair(id) {
    const response = await apiClient.delete(`/schemas/workflow-pairs/${id}`)
    return response.data
  },

  // NEW: Workflow stages
  async getWorkflowStages() {
    // Return default stages if no API endpoint exists
    return [
      { id: 1, name: 'Entry', stage_type: 'entry', order: 1, required_roles: ['curator'], description: 'Initial gene entry' },
      { id: 2, name: 'Precuration', stage_type: 'precuration', order: 2, required_roles: ['curator'], description: 'Preliminary assessment' },
      { id: 3, name: 'Curation', stage_type: 'curation', order: 3, required_roles: ['curator'], description: 'Full curation' },
      { id: 4, name: 'Review', stage_type: 'review', order: 4, required_roles: ['reviewer'], description: 'Peer review' },
      { id: 5, name: 'Active', stage_type: 'active', order: 5, required_roles: ['admin'], description: 'Published and active' }
    ]
  }
}
```

**File:** `src/views/WorkflowManagement.vue` (fix onMounted)

```javascript
onMounted(async () => {
  loading.value = true
  try {
    // Call ALL required methods in parallel
    await Promise.all([
      workflowStore.fetchWorkflowPairs(),      // NEW
      workflowStore.fetchWorkflowStages(),     // NEW
      workflowStore.fetchWorkflowAnalytics(),
      workflowStore.fetchPeerReviewers(),
      schemasStore.fetchSchemas()
    ])

    logger.info('WorkflowManagement mounted', {
      workflowPairsCount: workflowStore.workflowPairs?.length || 0,
      workflowStagesCount: workflowStore.workflowStages?.length || 0,
      schemasCount: schemasStore.schemas?.length || 0
    })
  } catch (error) {
    logger.error('Failed to load workflow data', {
      error: error.message,
      stack: error.stack
    })
    showError('Failed to load workflow data. Please refresh.')
  } finally {
    loading.value = false
  }
})
```

**Best Practice References:**
- [Pinia Actions](https://pinia.vuejs.org/core-concepts/actions.html) - Async actions with try-catch
- [Error Handling in Async Operations](https://app.studyraid.com/en/read/11883/378315/error-handling-in-async-operations) - Loading and error state management

---

### 1.3 Fix Gene Assignments API Error

**Problem:** `/gene-assignments` API call fails.

**Investigation Steps:**
1. Check if endpoint exists in backend
2. Verify API response format
3. Add proper error handling in store

**File:** `src/stores/assignments.js` (if exists, or create)

```javascript
export const useAssignmentsStore = defineStore('assignments', {
  state: () => ({
    assignments: [],
    loading: false,
    error: null
  }),

  actions: {
    async fetchAssignments(params = {}) {
      this.loading = true
      this.error = null

      try {
        const response = await apiClient.get('/gene-assignments', { params })
        this.assignments = response.data?.assignments || response.data || []
        return this.assignments
      } catch (error) {
        // Handle different error types
        if (error.response?.status === 404) {
          this.error = 'Gene assignments endpoint not available'
          this.assignments = [] // Empty array, not error state
        } else if (error.response?.status === 401) {
          this.error = 'Please log in to view assignments'
        } else {
          this.error = error.response?.data?.detail || 'Failed to load assignments'
        }
        console.error('fetchAssignments error:', error)
        throw error
      } finally {
        this.loading = false
      }
    }
  }
})
```

---

## Phase 2: UI/UX Improvements (Priority: High)

### 2.1 Fix Multiple Drawers Opening Simultaneously

**Problem:** Both "Add Genes" and "Assign Genes" drawers open at the same time.

**Solution:** Implement single-drawer state management.

**File:** `src/views/ScopeDashboard.vue` (or wherever drawers are managed)

```javascript
// Single state to track which drawer is open
const activeDrawer = ref(null) // 'addGenes' | 'assignGenes' | null

// Computed properties for v-model
const addGenesDrawerOpen = computed({
  get: () => activeDrawer.value === 'addGenes',
  set: (value) => {
    activeDrawer.value = value ? 'addGenes' : null
  }
})

const assignGenesDrawerOpen = computed({
  get: () => activeDrawer.value === 'assignGenes',
  set: (value) => {
    activeDrawer.value = value ? 'assignGenes' : null
  }
})

// Close all drawers
const closeAllDrawers = () => {
  activeDrawer.value = null
}

// Open specific drawer (closes others automatically)
const openDrawer = (drawerName) => {
  activeDrawer.value = drawerName
}
```

**Template Usage:**
```html
<AddGenesDrawer v-model="addGenesDrawerOpen" />
<AssignGenesDrawer v-model="assignGenesDrawerOpen" />

<v-btn @click="openDrawer('addGenes')">Add Genes</v-btn>
<v-btn @click="openDrawer('assignGenes')">Assign Genes</v-btn>
```

**Best Practice Reference:** [Vuetify Navigation Drawer](https://vuetifyjs.com/en/components/navigation-drawers/) - Use `v-model` for two-way binding.

---

### 2.2 Fix Viewport Positioning Issues

**Problem:** Elements outside viewport causing click failures.

**Solution:** Add scroll-into-view behavior and proper positioning.

**File:** `src/components/drawers/BaseDrawer.vue` (create reusable drawer component)

```vue
<template>
  <v-navigation-drawer
    v-model="modelValue"
    :location="location"
    :width="width"
    temporary
    class="drawer-container"
  >
    <div class="drawer-header">
      <slot name="header">
        <span class="text-h6">{{ title }}</span>
      </slot>
      <v-btn
        icon="mdi-close"
        variant="text"
        @click="close"
        class="drawer-close-btn"
      />
    </div>

    <div class="drawer-content">
      <slot />
    </div>

    <div class="drawer-actions" v-if="$slots.actions">
      <slot name="actions" />
    </div>
  </v-navigation-drawer>
</template>

<script setup>
const props = defineProps({
  modelValue: Boolean,
  title: String,
  location: { type: String, default: 'right' },
  width: { type: [Number, String], default: 400 }
})

const emit = defineEmits(['update:modelValue'])

const close = () => {
  emit('update:modelValue', false)
}
</script>

<style scoped>
.drawer-container {
  display: flex;
  flex-direction: column;
  max-height: 100vh;
  overflow: hidden;
}

.drawer-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px;
  border-bottom: 1px solid rgba(0, 0, 0, 0.12);
  flex-shrink: 0;
}

.drawer-close-btn {
  position: relative !important; /* Ensure it's in viewport */
}

.drawer-content {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
}

.drawer-actions {
  padding: 16px;
  border-top: 1px solid rgba(0, 0, 0, 0.12);
  flex-shrink: 0;
}
</style>
```

---

## Phase 3: Data Mapping Fixes (Priority: Medium)

### 3.1 Create Schema Data Transformer

**File:** `src/utils/schemaTransformer.js`

```javascript
/**
 * Transform backend schema format to frontend format
 * Handles field name differences between API and UI
 */
export const transformSchema = (schema) => {
  if (!schema) return null

  return {
    ...schema,
    // Map schema_type to type for UI
    type: schema.schema_type || schema.type || 'unknown',
    // Derive status from is_active flag
    status: schema.is_active === false ? 'deprecated' :
            schema.is_active === true ? 'active' : 'draft',
    // Ensure required fields have defaults
    name: schema.name || 'Unnamed Schema',
    version: schema.version || '1.0.0',
    description: schema.description || ''
  }
}

/**
 * Transform array of schemas
 */
export const transformSchemas = (schemas) => {
  if (!Array.isArray(schemas)) return []
  return schemas.map(transformSchema)
}

/**
 * Transform frontend format back to backend format for API calls
 */
export const prepareSchemaForAPI = (schema) => {
  const { type, status, ...rest } = schema
  return {
    ...rest,
    schema_type: type,
    is_active: status === 'active'
  }
}
```

**Usage in store:**
```javascript
import { transformSchemas } from '@/utils/schemaTransformer'

// In schemas store
async fetchSchemas() {
  const response = await apiClient.get('/schemas/curation-schemas')
  this.schemas = transformSchemas(response.data)
}
```

---

## Phase 4: Error Handling Improvements (Priority: Medium)

### 4.1 Global Error Handler with Pinia Integration

**File:** `src/plugins/errorHandler.js`

```javascript
import { useNotificationsStore } from '@/stores/notifications'
import { logService } from '@/services/logService'

export const setupGlobalErrorHandler = (app) => {
  // Vue error handler
  app.config.errorHandler = (err, instance, info) => {
    logService.error('Vue Error', {
      error: err.message,
      stack: err.stack,
      component: instance?.$options?.name,
      info
    })

    // Show user-friendly notification
    const notificationsStore = useNotificationsStore()
    notificationsStore.addToast(
      'An unexpected error occurred. Please try again.',
      'error'
    )
  }

  // Unhandled promise rejections
  window.addEventListener('unhandledrejection', (event) => {
    logService.error('Unhandled Promise Rejection', {
      reason: event.reason?.message || event.reason,
      stack: event.reason?.stack
    })
  })
}
```

### 4.2 Pinia Store Error Interceptor

**File:** `src/plugins/piniaErrorPlugin.js`

```javascript
import { logService } from '@/services/logService'

/**
 * Pinia plugin for global action error tracking
 * Reference: https://pinia.vuejs.org/core-concepts/actions.html#subscribing-to-actions
 */
export const piniaErrorPlugin = ({ store }) => {
  store.$onAction(({ name, args, after, onError }) => {
    const startTime = Date.now()

    after((result) => {
      const duration = Date.now() - startTime
      if (duration > 1000) {
        logService.warn(`Slow action: ${store.$id}.${name}`, { duration })
      }
    })

    onError((error) => {
      logService.error(`Store action failed: ${store.$id}.${name}`, {
        error: error.message,
        args: JSON.stringify(args).slice(0, 200)
      })
    })
  })
}
```

**Register in main.js:**
```javascript
import { createPinia } from 'pinia'
import { piniaErrorPlugin } from '@/plugins/piniaErrorPlugin'

const pinia = createPinia()
pinia.use(piniaErrorPlugin)
```

---

## Phase 5: Testing & Validation (Priority: Ongoing)

### 5.1 Add Unit Tests for Critical Functions

**File:** `src/utils/__tests__/schemaTransformer.test.js`

```javascript
import { describe, it, expect } from 'vitest'
import { transformSchema, transformSchemas } from '../schemaTransformer'

describe('schemaTransformer', () => {
  describe('transformSchema', () => {
    it('should map schema_type to type', () => {
      const input = { schema_type: 'curation', name: 'Test' }
      const result = transformSchema(input)
      expect(result.type).toBe('curation')
    })

    it('should derive status from is_active', () => {
      expect(transformSchema({ is_active: true }).status).toBe('active')
      expect(transformSchema({ is_active: false }).status).toBe('deprecated')
      expect(transformSchema({}).status).toBe('draft')
    })

    it('should handle null input', () => {
      expect(transformSchema(null)).toBeNull()
    })

    it('should provide default values', () => {
      const result = transformSchema({})
      expect(result.name).toBe('Unnamed Schema')
      expect(result.version).toBe('1.0.0')
    })
  })

  describe('transformSchemas', () => {
    it('should transform array of schemas', () => {
      const input = [
        { schema_type: 'curation' },
        { schema_type: 'precuration' }
      ]
      const result = transformSchemas(input)
      expect(result).toHaveLength(2)
      expect(result[0].type).toBe('curation')
    })

    it('should return empty array for non-array input', () => {
      expect(transformSchemas(null)).toEqual([])
      expect(transformSchemas(undefined)).toEqual([])
    })
  })
})
```

---

## Implementation Checklist

### Phase 1 - Critical Bugs (Day 1-2)
- [ ] Fix `formatType`/`formatStatus` null safety in SchemaManagement.vue
- [ ] Add `workflowPairs` and `workflowStages` to workflow store
- [ ] Add API methods for workflow pairs
- [ ] Fix WorkflowManagement.vue onMounted to fetch all required data
- [ ] Debug and fix gene assignments API error

### Phase 2 - UI/UX (Day 3-4)
- [ ] Implement single-drawer state management
- [ ] Create BaseDrawer component with proper positioning
- [ ] Fix viewport issues in drawer components
- [ ] Test drawer behavior on different screen sizes

### Phase 3 - Data Mapping (Day 4-5)
- [ ] Create schemaTransformer utility
- [ ] Update schemas store to use transformer
- [ ] Verify API field mappings match backend

### Phase 4 - Error Handling (Day 5-6)
- [ ] Implement global Vue error handler
- [ ] Add Pinia error interceptor plugin
- [ ] Add user-friendly error messages

### Phase 5 - Testing (Ongoing)
- [ ] Add unit tests for transformer functions
- [ ] Add integration tests for store actions
- [ ] Run E2E tests for complete workflow

---

## References

- [Vue 3 Documentation - Computed Properties](https://vuejs.org/guide/essentials/computed.html)
- [Vue 3 Documentation - Error Handling](https://vuejs.org/error-reference/)
- [Pinia Documentation - Actions](https://pinia.vuejs.org/core-concepts/actions.html)
- [Pinia Best Practices](https://seanwilson.ca/blog/pinia-vue-best-practices.html)
- [Vuetify Navigation Drawers](https://vuetifyjs.com/en/components/navigation-drawers/)
- [Error Handling in Async Operations](https://app.studyraid.com/en/read/11883/378315/error-handling-in-async-operations)

---

*Plan created based on Vue 3, Pinia, and Vuetify best practices.*
