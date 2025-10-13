# Frontend Implementation Plan: Scope-Centric UI

**Version:** 2.0 (DRY/SOLID Compliant)
**Date:** 2025-10-13
**Framework:** Vue 3.5 + Vuetify 3.9 + Pinia 2.1

---

## Implementation Order

### Phase 1: Shared Utilities & Composables (Week 5)
### Phase 2: Pinia Store Refactoring (Week 5)
### Phase 3: Core Components (Week 5-6)
### Phase 4: Views & Routing (Week 6)

---

## PHASE 1: Shared Utilities & Composables

### Step 1.1: Create Role Colors Composable (DRY Fix)

**File:** `frontend/src/composables/useRoleColors.js` (CREATE NEW)

```javascript
/**
 * Shared composable for scope role colors.
 * FIX: Eliminates duplication across 3+ components.
 */

export function useRoleColors() {
  const roleColors = Object.freeze({
    admin: 'red',
    curator: 'blue',
    reviewer: 'green',
    viewer: 'grey'
  })

  const roleIcons = Object.freeze({
    admin: 'mdi-shield-crown',
    curator: 'mdi-pencil',
    reviewer: 'mdi-check-circle',
    viewer: 'mdi-eye'
  })

  const getRoleColor = (role) => roleColors[role] || 'grey'
  const getRoleIcon = (role) => roleIcons[role] || 'mdi-account'

  return {
    roleColors,
    roleIcons,
    getRoleColor,
    getRoleIcon
  }
}
```

**Remove Duplicated Code:**
- Line 1199-1207 in `ScopeSelector.vue` (DELETE)
- Line 1338-1346 in `ScopeDashboard.vue` (DELETE)
- Line 1592-1600 in `MemberManagement.vue` (DELETE)

**Replace With:**
```javascript
import { useRoleColors } from '@/composables/useRoleColors'
const { getRoleColor } = useRoleColors()
```

---

### Step 1.2: Create Scope Utilities Composable

**File:** `frontend/src/composables/useScopeUtils.js` (CREATE NEW)

```javascript
/**
 * Utility functions for scope operations.
 */

export function useScopeUtils() {
  const formatDate = (date) => {
    if (!date) return 'No due date'
    return new Date(date).toLocaleDateString()
  }

  const calculateProgress = (completed, total) => {
    if (!total || total === 0) return 0
    return Math.round((completed / total) * 100)
  }

  const getScopeVisibilityIcon = (isPublic) => {
    return isPublic ? 'mdi-earth' : 'mdi-lock'
  }

  const getScopeVisibilityLabel = (isPublic) => {
    return isPublic ? 'Public' : 'Private'
  }

  return {
    formatDate,
    calculateProgress,
    getScopeVisibilityIcon,
    getScopeVisibilityLabel
  }
}
```

---

### Step 1.3: Create Permission Checker Composable

**File:** `frontend/src/composables/useScopePermissions.js` (CREATE NEW)

```javascript
/**
 * Scope permission checking utilities.
 */

import { computed } from 'vue'

export function useScopePermissions(userRole) {
  const canManageScope = computed(() => {
    return userRole.value === 'admin'
  })

  const canInviteMembers = computed(() => {
    return userRole.value === 'admin'
  })

  const canCurate = computed(() => {
    return ['admin', 'curator'].includes(userRole.value)
  })

  const canReview = computed(() => {
    return ['admin', 'reviewer'].includes(userRole.value)
  })

  const canViewMembers = computed(() => {
    return ['admin', 'curator', 'reviewer'].includes(userRole.value)
  })

  const isViewer = computed(() => {
    return userRole.value === 'viewer'
  })

  return {
    canManageScope,
    canInviteMembers,
    canCurate,
    canReview,
    canViewMembers,
    isViewer
  }
}
```

---

## PHASE 2: Pinia Store Refactoring (SOLID Fix)

### Step 2.1: Create Separate API Service Layer

**File:** `frontend/src/services/scopeService.js` (CREATE NEW)

```javascript
/**
 * Scope API service (network layer only).
 * FIX: Separates network concerns from state management (SOLID - SRP).
 */

import api from '@/api/client'

export const scopeService = {
  /**
   * Fetch all scopes visible to current user
   */
  async fetchScopes(params = {}) {
    const response = await api.get('/scopes/', { params })
    return response.data
  },

  /**
   * Fetch single scope by ID
   */
  async fetchScope(scopeId) {
    const response = await api.get(`/scopes/${scopeId}`)
    return response.data
  },

  /**
   * Create new scope
   */
  async createScope(scopeData) {
    const response = await api.post('/scopes/', scopeData)
    return response.data
  },

  /**
   * Update existing scope
   */
  async updateScope(scopeId, scopeData) {
    const response = await api.patch(`/scopes/${scopeId}`, scopeData)
    return response.data
  },

  /**
   * Delete scope
   */
  async deleteScope(scopeId) {
    await api.delete(`/scopes/${scopeId}`)
  },

  /**
   * Fetch scope statistics
   */
  async fetchStatistics(scopeId) {
    const response = await api.get(`/scopes/${scopeId}/statistics`)
    return response.data
  },

  /**
   * Fetch scope members
   */
  async fetchMembers(scopeId) {
    const response = await api.get(`/scopes/${scopeId}/members`)
    return response.data
  },

  /**
   * Invite user to scope
   */
  async inviteMember(scopeId, invitationData) {
    const response = await api.post(`/scopes/${scopeId}/invitations`, invitationData)
    return response.data
  },

  /**
   * Update member role
   */
  async updateMemberRole(scopeId, userId, newRole) {
    const response = await api.patch(`/scopes/${scopeId}/members/${userId}`, {
      role: newRole
    })
    return response.data
  },

  /**
   * Remove member from scope
   */
  async removeMember(scopeId, userId) {
    await api.delete(`/scopes/${scopeId}/members/${userId}`)
  }
}
```

---

### Step 2.2: Refactor Scopes Store (SOLID Compliance)

**File:** `frontend/src/stores/scopes.js`

**Replace entire file with:**

```javascript
/**
 * Scopes Pinia store (state management only).
 * FIX: Follows SOLID - Single Responsibility Principle.
 * Network calls delegated to scopeService.
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { scopeService } from '@/services/scopeService'
import { logService } from '@/services/logService'

export const useScopeStore = defineStore('scopes', () => {
  // ============================================
  // STATE
  // ============================================

  const scopes = ref([])
  const currentScope = ref(null)
  const currentUserRole = ref(null)
  const loading = ref(false)
  const error = ref(null)

  // ============================================
  // GETTERS
  // ============================================

  const userScopes = computed(() => scopes.value)
  const publicScopes = computed(() => scopes.value.filter(s => s.is_public))
  const privateScopes = computed(() => scopes.value.filter(s => !s.is_public))

  const getScopeById = computed(() => {
    return (id) => scopes.value.find(s => s.id === id)
  })

  // ============================================
  // ACTIONS
  // ============================================

  async function fetchUserScopes(params = {}) {
    loading.value = true
    error.value = null

    try {
      const data = await scopeService.fetchScopes(params)
      scopes.value = data.scopes || data
      logService.info('Scopes fetched successfully', { count: scopes.value.length })
    } catch (err) {
      error.value = err.message
      logService.error('Failed to fetch scopes', { error: err.message })
      throw err
    } finally {
      loading.value = false
    }
  }

  async function fetchScope(scopeId) {
    loading.value = true
    error.value = null

    try {
      const scope = await scopeService.fetchScope(scopeId)
      currentScope.value = scope

      // Update in list if exists
      const index = scopes.value.findIndex(s => s.id === scopeId)
      if (index !== -1) {
        scopes.value[index] = scope
      } else {
        scopes.value.push(scope)
      }

      logService.info('Scope fetched', { scope_id: scopeId })
      return scope
    } catch (err) {
      error.value = err.message
      logService.error('Failed to fetch scope', { scope_id: scopeId, error: err.message })
      throw err
    } finally {
      loading.value = false
    }
  }

  async function createScope(scopeData) {
    loading.value = true
    error.value = null

    try {
      const newScope = await scopeService.createScope(scopeData)
      scopes.value.push(newScope)
      currentScope.value = newScope
      currentUserRole.value = 'admin' // Creator is admin

      logService.info('Scope created', { scope_id: newScope.id, name: newScope.name })
      return newScope
    } catch (err) {
      error.value = err.message
      logService.error('Failed to create scope', { error: err.message })
      throw err
    } finally {
      loading.value = false
    }
  }

  async function updateScope(scopeId, scopeData) {
    loading.value = true
    error.value = null

    try {
      const updatedScope = await scopeService.updateScope(scopeId, scopeData)

      // Update in list
      const index = scopes.value.findIndex(s => s.id === scopeId)
      if (index !== -1) {
        scopes.value[index] = updatedScope
      }

      // Update current if same
      if (currentScope.value?.id === scopeId) {
        currentScope.value = updatedScope
      }

      logService.info('Scope updated', { scope_id: scopeId })
      return updatedScope
    } catch (err) {
      error.value = err.message
      logService.error('Failed to update scope', { scope_id: scopeId, error: err.message })
      throw err
    } finally {
      loading.value = false
    }
  }

  async function deleteScope(scopeId) {
    loading.value = true
    error.value = null

    try {
      await scopeService.deleteScope(scopeId)

      // Remove from list
      scopes.value = scopes.value.filter(s => s.id !== scopeId)

      // Clear current if deleted
      if (currentScope.value?.id === scopeId) {
        currentScope.value = null
        currentUserRole.value = null
      }

      logService.info('Scope deleted', { scope_id: scopeId })
    } catch (err) {
      error.value = err.message
      logService.error('Failed to delete scope', { scope_id: scopeId, error: err.message })
      throw err
    } finally {
      loading.value = false
    }
  }

  async function fetchUserRole(scopeId) {
    try {
      const members = await scopeService.fetchMembers(scopeId)
      const userStore = useAuthStore()
      const currentUserId = userStore.user?.id

      const membership = members.find(m => m.user_id === currentUserId)
      currentUserRole.value = membership?.role || null

      return currentUserRole.value
    } catch (err) {
      currentUserRole.value = null
      logService.error('Failed to fetch user role', { scope_id: scopeId, error: err.message })
      throw err
    }
  }

  async function fetchMembers(scopeId) {
    try {
      return await scopeService.fetchMembers(scopeId)
    } catch (err) {
      logService.error('Failed to fetch members', { scope_id: scopeId, error: err.message })
      throw err
    }
  }

  async function inviteMember(scopeId, invitationData) {
    try {
      const result = await scopeService.inviteMember(scopeId, invitationData)
      logService.info('Member invited', { scope_id: scopeId, email: invitationData.email })
      return result
    } catch (err) {
      logService.error('Failed to invite member', { scope_id: scopeId, error: err.message })
      throw err
    }
  }

  async function updateMemberRole(scopeId, userId, newRole) {
    try {
      const result = await scopeService.updateMemberRole(scopeId, userId, newRole)
      logService.info('Member role updated', { scope_id: scopeId, user_id: userId, role: newRole })
      return result
    } catch (err) {
      logService.error('Failed to update member role', { scope_id: scopeId, error: err.message })
      throw err
    }
  }

  async function removeMember(scopeId, userId) {
    try {
      await scopeService.removeMember(scopeId, userId)
      logService.info('Member removed', { scope_id: scopeId, user_id: userId })
    } catch (err) {
      logService.error('Failed to remove member', { scope_id: scopeId, error: err.message })
      throw err
    }
  }

  function setCurrentScope(scope) {
    currentScope.value = scope
    logService.debug('Current scope set', { scope_id: scope?.id })
  }

  function clearCurrentScope() {
    currentScope.value = null
    currentUserRole.value = null
    logService.debug('Current scope cleared')
  }

  function clearError() {
    error.value = null
  }

  // ============================================
  // RETURN (Composition API Pattern)
  // ============================================

  return {
    // State
    scopes,
    currentScope,
    currentUserRole,
    loading,
    error,

    // Getters
    userScopes,
    publicScopes,
    privateScopes,
    getScopeById,

    // Actions
    fetchUserScopes,
    fetchScope,
    createScope,
    updateScope,
    deleteScope,
    fetchUserRole,
    fetchMembers,
    inviteMember,
    updateMemberRole,
    removeMember,
    setCurrentScope,
    clearCurrentScope,
    clearError
  }
})
```

---

## PHASE 3: Core Components

### Step 3.1: Scope Selector Component

**File:** `frontend/src/components/scope/ScopeSelector.vue`

**Replace entire file with:**

```vue
<template>
  <v-menu offset-y>
    <template v-slot:activator="{ props }">
      <v-btn
        v-bind="props"
        color="primary"
        variant="outlined"
        prepend-icon="mdi-folder-outline"
      >
        {{ currentScope?.display_name || 'Select Scope' }}
        <v-icon end>mdi-chevron-down</v-icon>
      </v-btn>
    </template>

    <v-list>
      <v-list-subheader>My Scopes</v-list-subheader>

      <v-list-item
        v-for="scope in userScopes"
        :key="scope.id"
        @click="selectScope(scope)"
        :active="currentScope?.id === scope.id"
      >
        <template v-slot:prepend>
          <v-icon :icon="getScopeVisibilityIcon(scope.is_public)"></v-icon>
        </template>

        <v-list-item-title>{{ scope.display_name }}</v-list-item-title>

        <v-list-item-subtitle>
          <v-chip size="x-small" :color="getRoleColor(scope.role)">
            {{ scope.role }}
          </v-chip>
        </v-list-item-subtitle>
      </v-list-item>

      <v-divider class="my-2"></v-divider>

      <v-list-item @click="createScope" prepend-icon="mdi-plus">
        <v-list-item-title>Create New Scope</v-list-item-title>
      </v-list-item>
    </v-list>
  </v-menu>
</template>

<script setup>
import { computed } from 'vue'
import { useScopeStore } from '@/stores/scopes'
import { useRouter } from 'vue-router'
import { useRoleColors } from '@/composables/useRoleColors'
import { useScopeUtils } from '@/composables/useScopeUtils'

const scopeStore = useScopeStore()
const router = useRouter()
const { getRoleColor } = useRoleColors()
const { getScopeVisibilityIcon } = useScopeUtils()

const currentScope = computed(() => scopeStore.currentScope)
const userScopes = computed(() => scopeStore.userScopes)

const selectScope = (scope) => {
  scopeStore.setCurrentScope(scope)
  router.push({ name: 'scope-dashboard', params: { scopeId: scope.id } })
}

const createScope = () => {
  router.push({ name: 'scope-create' })
}
</script>
```

---

### Step 3.2: Member Management Component (Fixed)

**File:** `frontend/src/components/scope/MemberManagement.vue`

**Key Changes:**
- Import composables (useRoleColors, useScopePermissions)
- Remove duplicated getRoleColor function
- Use logService instead of console.error (line 1576)
- Add proper error notifications

**Lines 1-10:** Add imports
```vue
<script setup>
import { ref, computed, onMounted } from 'vue'
import { useScopeStore } from '@/stores/scopes'
import { useAuthStore } from '@/stores/auth'
import { useRoleColors } from '@/composables/useRoleColors'
import { useScopePermissions } from '@/composables/useScopePermissions'
import { logService } from '@/services/logService'

const props = defineProps({
  scopeId: { type: String, required: true }
})
```

**Lines 1520-1524:** Replace permission computed
```vue
const { getRoleColor } = useRoleColors()
const scopeStore = useScopeStore()
const authStore = useAuthStore()

const userRole = computed(() => scopeStore.currentUserRole)
const { canInvite, canManageMembers } = useScopePermissions(userRole)
```

**Lines 1592-1600:** DELETE getRoleColor function (DRY fix)

**Line 1576:** Replace console.error
```vue
} catch (error) {
  logService.error('Failed to send invitation', { error: error.message })
  // Show user notification (add Vuetify snackbar)
}
```

---

## PHASE 4: Views & Routing

### Step 4.1: Scope Dashboard View

**File:** `frontend/src/views/scope/ScopeDashboard.vue`

**Key Changes:**
- Import composables (useRoleColors, useScopeUtils, useScopePermissions)
- Remove duplicated functions (getRoleColor, formatDate)
- Use composable for progress calculation

**Lines 1-15:** Update imports
```vue
<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useScopeStore } from '@/stores/scopes'
import { useRoleColors } from '@/composables/useRoleColors'
import { useScopeUtils } from '@/composables/useScopeUtils'
import { useScopePermissions } from '@/composables/useScopePermissions'
import ScopeOverview from '@/components/scope/ScopeOverview.vue'
import GeneList from '@/components/gene/GeneList.vue'
import CurationList from '@/components/curation/CurationList.vue'
import MemberManagement from '@/components/scope/MemberManagement.vue'
import ScopeSettings from '@/components/scope/ScopeSettings.vue'

const route = useRoute()
const scopeStore = useScopeStore()
```

**Lines 1320-1332:** Replace with composables
```vue
const scopeId = computed(() => route.params.scopeId)
const scope = computed(() => scopeStore.currentScope)
const userRole = computed(() => scopeStore.currentUserRole)

// Use composables (DRY)
const { getRoleColor } = useRoleColors()
const { formatDate, calculateProgress } = useScopeUtils()
const { canManageScope, canViewMembers } = useScopePermissions(userRole)

const activeTab = ref('overview')

const curateProgress = computed(() =>
  calculateProgress(scope.value?.completed_genes, scope.value?.total_genes)
)
```

**Lines 1338-1355:** DELETE duplicated functions

---

### Step 4.2: Create Scope View

**File:** `frontend/src/views/scope/ScopeCreate.vue` (CREATE NEW)

```vue
<template>
  <v-container>
    <v-card max-width="800" class="mx-auto">
      <v-card-title>Create New Scope</v-card-title>

      <v-card-text>
        <v-form ref="form" v-model="valid" @submit.prevent="handleSubmit">
          <v-text-field
            v-model="scopeData.name"
            label="Scope Name (machine-readable)"
            :rules="nameRules"
            hint="lowercase-with-dashes (e.g., kidney-genetics)"
            persistent-hint
            prepend-icon="mdi-identifier"
          ></v-text-field>

          <v-text-field
            v-model="scopeData.display_name"
            label="Display Name"
            :rules="displayNameRules"
            prepend-icon="mdi-format-title"
          ></v-text-field>

          <v-textarea
            v-model="scopeData.description"
            label="Description"
            rows="3"
            prepend-icon="mdi-text"
          ></v-textarea>

          <v-switch
            v-model="scopeData.is_public"
            label="Public Scope"
            color="primary"
            hint="Public scopes are visible to all users"
            persistent-hint
          ></v-switch>

          <v-text-field
            v-model="scopeData.due_date"
            label="Due Date (optional)"
            type="date"
            prepend-icon="mdi-calendar"
          ></v-text-field>
        </v-form>
      </v-card-text>

      <v-card-actions>
        <v-spacer></v-spacer>
        <v-btn @click="cancel">Cancel</v-btn>
        <v-btn
          color="primary"
          :disabled="!valid || loading"
          :loading="loading"
          @click="handleSubmit"
        >
          Create Scope
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-container>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useScopeStore } from '@/stores/scopes'
import { logService } from '@/services/logService'

const router = useRouter()
const scopeStore = useScopeStore()

const valid = ref(false)
const loading = ref(false)

const scopeData = ref({
  name: '',
  display_name: '',
  description: '',
  is_public: false,
  due_date: null
})

const nameRules = [
  v => !!v || 'Scope name is required',
  v => /^[a-z][a-z0-9-]{2,62}[a-z0-9]$/.test(v) || 'Must be 4-64 chars, lowercase, dashes allowed',
  v => !v.includes('--') || 'No consecutive dashes'
]

const displayNameRules = [
  v => !!v || 'Display name is required',
  v => v.length >= 4 || 'Minimum 4 characters'
]

const handleSubmit = async () => {
  if (!valid.value) return

  loading.value = true
  try {
    const newScope = await scopeStore.createScope(scopeData.value)
    logService.info('Scope created successfully', { scope_id: newScope.id })
    router.push({ name: 'scope-dashboard', params: { scopeId: newScope.id } })
  } catch (error) {
    logService.error('Failed to create scope', { error: error.message })
    // Show error notification
  } finally {
    loading.value = false
  }
}

const cancel = () => {
  router.back()
}
</script>
```

---

### Step 4.3: Update Router

**File:** `frontend/src/router/index.js`

**Add routes:**
```javascript
{
  path: '/scopes',
  name: 'scopes',
  component: () => import('@/views/scope/ScopeList.vue'),
  meta: { requiresAuth: true }
},
{
  path: '/scopes/create',
  name: 'scope-create',
  component: () => import('@/views/scope/ScopeCreate.vue'),
  meta: { requiresAuth: true }
},
{
  path: '/scopes/:scopeId',
  name: 'scope-dashboard',
  component: () => import('@/views/scope/ScopeDashboard.vue'),
  meta: { requiresAuth: true }
}
```

---

## Summary of Files to Create/Modify

### Create New Files:
1. `frontend/src/composables/useRoleColors.js` - Shared role colors (DRY)
2. `frontend/src/composables/useScopeUtils.js` - Scope utilities
3. `frontend/src/composables/useScopePermissions.js` - Permission checking
4. `frontend/src/services/scopeService.js` - API service layer (SOLID-SRP)
5. `frontend/src/views/scope/ScopeCreate.vue` - Create scope view
6. `frontend/src/views/scope/ScopeList.vue` - List all scopes view

### Modify Existing Files:
1. `frontend/src/stores/scopes.js` - Complete refactor (SOLID-SRP)
2. `frontend/src/components/scope/ScopeSelector.vue` - Use composables
3. `frontend/src/components/scope/MemberManagement.vue` - Use composables + logging
4. `frontend/src/views/scope/ScopeDashboard.vue` - Use composables
5. `frontend/src/router/index.js` - Add scope routes

---

## Testing Checklist

### Component Testing:
- [ ] Scope Selector renders correctly
- [ ] Role colors display correctly (verify DRY fix)
- [ ] Member management shows correct permissions
- [ ] Create scope form validation works
- [ ] Scope dashboard loads data correctly

### Integration Testing:
- [ ] Scope creation flow end-to-end
- [ ] Member invitation flow
- [ ] Role updates reflect immediately
- [ ] Navigation between scopes
- [ ] Public/private scope visibility

### Performance Testing:
- [ ] Scope list with 100+ scopes renders quickly
- [ ] Member list with 50+ members performs well
- [ ] Composables don't cause re-render issues
- [ ] Store updates trigger minimal re-renders

---

## Migration Notes

### Gradual Migration Path:
1. **Week 5**: Create new composables and service layer
2. **Week 5**: Refactor stores (backward compatible)
3. **Week 5-6**: Update components one by one
4. **Week 6**: Add new routes and views
5. **Week 6**: Remove old code after verification

### Backward Compatibility:
- Keep old endpoints working during migration
- Old components can coexist with new ones
- Gradual route migration (redirect old → new)

---

## Performance Targets

- Initial page load: < 2s
- Scope switching: < 500ms
- Member list load: < 1s
- Form submission: < 1s
- Composable overhead: < 10ms
