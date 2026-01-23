/**
 * Scopes Pinia Store
 *
 * **SOLID - Single Responsibility Principle (SRP)**
 * This store handles ONLY state management for scopes.
 * Network calls are delegated to scopeService.
 *
 * **Architecture**:
 * - Store: State management, caching, reactive computeds
 * - Service: Network calls, HTTP logic
 * - Components: UI rendering, user interactions
 *
 * **Composition API Pattern**:
 * Uses Vue 3 Composition API (setup function) for better:
 * - Type inference
 * - Code organization
 * - Reusability
 * - Performance
 *
 * @see docs/refactoring/FRONTEND_IMPLEMENTATION.md#step-22-refactor-scopes-store
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { scopeService } from '@/services/scopeService'
import { logService } from '@/services/logService'
import { useAuthStore } from '@/stores/auth'

export const useScopesStore = defineStore('scopes', () => {
  // ============================================
  // STATE
  // ============================================

  const scopes = ref([])
  const currentScope = ref(null)
  const currentUserRole = ref(null)
  const scopeUsers = ref({}) // Map of scopeId -> users array
  const scopeStatistics = ref({}) // Map of scopeId -> statistics
  const loading = ref(false)
  const error = ref(null)

  // ============================================
  // GETTERS
  // ============================================

  const userScopes = computed(() => scopes.value)

  const publicScopes = computed(() => scopes.value.filter(s => s.is_public))

  const privateScopes = computed(() => scopes.value.filter(s => !s.is_public))

  const activeScopesCount = computed(() => scopes.value.filter(s => s.is_active).length)

  const getScopeById = computed(() => {
    return id => scopes.value.find(s => s.id === id)
  })

  const getScopesByInstitution = computed(() => {
    return institution => scopes.value.filter(s => s.institution === institution)
  })

  const getScopeUsers = computed(() => {
    return scopeId => scopeUsers.value[scopeId] || []
  })

  const getScopeStatistics = computed(() => {
    return scopeId => scopeStatistics.value[scopeId] || null
  })

  // ============================================
  // ACTIONS
  // ============================================

  async function fetchUserScopes(params = {}) {
    loading.value = true
    error.value = null

    try {
      const data = await scopeService.fetchScopes(params)
      scopes.value = data
      logService.info('Scopes fetched successfully', { count: scopes.value.length })
      return data
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

      logService.info('Scope fetched', { scope_id: scopeId, name: scope.name })
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
      currentUserRole.value = 'admin' // Creator is automatically admin

      logService.info('Scope created', { scope_id: newScope.id, name: newScope.name })
      return newScope
    } catch (err) {
      error.value = err.message
      logService.error('Failed to create scope', { name: scopeData.name, error: err.message })
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

      logService.info('Scope updated', { scope_id: scopeId, changes: Object.keys(scopeData) })
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

      // Clear cached data
      delete scopeUsers.value[scopeId]
      delete scopeStatistics.value[scopeId]

      logService.info('Scope deleted', { scope_id: scopeId })
      return true
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
      const authStore = useAuthStore()
      const currentUserId = authStore.user?.id

      if (!currentUserId) {
        currentUserRole.value = null
        return null
      }

      // RBAC hierarchy: Application admins have implicit admin access to all scopes
      if (authStore.isAdmin) {
        currentUserRole.value = 'admin'
        logService.debug('User role fetched (app admin)', { scope_id: scopeId, role: 'admin' })
        return 'admin'
      }

      // For non-admin users, check scope membership
      const members = await scopeService.fetchMembers(scopeId)
      const membership = members.find(m => m.user_id === currentUserId)
      currentUserRole.value = membership?.role || null

      logService.debug('User role fetched', { scope_id: scopeId, role: currentUserRole.value })
      return currentUserRole.value
    } catch (err) {
      currentUserRole.value = null
      logService.error('Failed to fetch user role', { scope_id: scopeId, error: err.message })
      throw err
    }
  }

  async function fetchMembers(scopeId) {
    try {
      const members = await scopeService.fetchMembers(scopeId)
      scopeUsers.value[scopeId] = members
      logService.debug('Scope members fetched', { scope_id: scopeId, count: members.length })
      return members
    } catch (err) {
      logService.error('Failed to fetch members', { scope_id: scopeId, error: err.message })
      throw err
    }
  }

  async function fetchStatistics(scopeId) {
    try {
      const stats = await scopeService.fetchStatistics(scopeId)
      scopeStatistics.value[scopeId] = stats
      logService.debug('Scope statistics fetched', {
        scope_id: scopeId,
        total_genes: stats.total_genes
      })
      return stats
    } catch (err) {
      logService.error('Failed to fetch statistics', { scope_id: scopeId, error: err.message })
      throw err
    }
  }

  async function inviteMember(scopeId, invitationData) {
    try {
      const result = await scopeService.inviteMember(scopeId, invitationData)

      // Refresh members list
      await fetchMembers(scopeId)

      logService.info('Member invited', {
        scope_id: scopeId,
        email: invitationData.email || 'existing_user',
        role: invitationData.role
      })
      return result
    } catch (err) {
      logService.error('Failed to invite member', { scope_id: scopeId, error: err.message })
      throw err
    }
  }

  async function updateMemberRole(scopeId, userId, newRole) {
    try {
      const result = await scopeService.updateMemberRole(scopeId, userId, newRole)

      // Update in cached users list
      if (scopeUsers.value[scopeId]) {
        const memberIndex = scopeUsers.value[scopeId].findIndex(m => m.user_id === userId)
        if (memberIndex !== -1) {
          scopeUsers.value[scopeId][memberIndex].role = newRole
        }
      }

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

      // Remove from cached users list
      if (scopeUsers.value[scopeId]) {
        scopeUsers.value[scopeId] = scopeUsers.value[scopeId].filter(m => m.user_id !== userId)
      }

      logService.info('Member removed', { scope_id: scopeId, user_id: userId })
    } catch (err) {
      logService.error('Failed to remove member', { scope_id: scopeId, error: err.message })
      throw err
    }
  }

  function setCurrentScope(scope) {
    currentScope.value = scope
    logService.debug('Current scope set', { scope_id: scope?.id, name: scope?.name })
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
    scopeUsers,
    scopeStatistics,
    loading,
    error,

    // Getters
    userScopes,
    publicScopes,
    privateScopes,
    activeScopesCount,
    getScopeById,
    getScopesByInstitution,
    getScopeUsers,
    getScopeStatistics,

    // Actions
    fetchUserScopes,
    fetchScope,
    createScope,
    updateScope,
    deleteScope,
    fetchUserRole,
    fetchMembers,
    fetchStatistics,
    inviteMember,
    updateMemberRole,
    removeMember,
    setCurrentScope,
    clearCurrentScope,
    clearError
  }
})

export default useScopesStore
