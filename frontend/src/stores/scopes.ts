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
import { toApiError, apiData } from './apiError'
import type { Schema } from '@/types/api'

export type ScopeRecord = Schema<'ScopeListItem'>
export type ScopeMember = Schema<'ScopeMembershipResponse'>

/** Scope statistics; `total_genes` is read by the log line but is not declared by the API schema. */
export type ScopeStatisticsRecord = Schema<'ScopeStatistics'> & { total_genes?: number }

/** Invitation payload; the invite form may also pass an email for users without an account. */
type InviteMemberData = Parameters<typeof scopeService.inviteMember>[1] & { email?: string }

export const useScopesStore = defineStore('scopes', () => {
  // ============================================
  // STATE
  // ============================================

  const scopes = ref<ScopeRecord[]>([])
  const currentScope = ref<ScopeRecord | null>(null)
  const currentUserRole = ref<string | null>(null)
  const scopeUsers = ref<Record<string, ScopeMember[]>>({}) // Map of scopeId -> users array
  const scopeStatistics = ref<Record<string, ScopeStatisticsRecord>>({}) // Map of scopeId -> statistics
  const loading = ref(false)
  const error = ref<string | null>(null)

  // ============================================
  // GETTERS
  // ============================================

  const userScopes = computed(() => scopes.value)

  const publicScopes = computed(() => scopes.value.filter(s => s.is_public))

  const privateScopes = computed(() => scopes.value.filter(s => !s.is_public))

  const activeScopesCount = computed(() => scopes.value.filter(s => s.is_active).length)

  const getScopeById = computed(() => {
    return (id: string) => scopes.value.find(s => s.id === id)
  })

  const getScopesByInstitution = computed(() => {
    return (institution: string) => scopes.value.filter(s => s.institution === institution)
  })

  const getScopeUsers = computed(() => {
    return (scopeId: string) => scopeUsers.value[scopeId] || []
  })

  const getScopeStatistics = computed(() => {
    return (scopeId: string) => scopeStatistics.value[scopeId] || null
  })

  // ============================================
  // ACTIONS
  // ============================================

  async function fetchUserScopes(params: Record<string, unknown> = {}) {
    loading.value = true
    error.value = null

    try {
      const data = apiData<ScopeRecord[]>(await scopeService.fetchScopes(params))
      scopes.value = data
      logService.info('Scopes fetched successfully', { count: scopes.value.length })
      return data
    } catch (err) {
      error.value = toApiError(err).message ?? null
      logService.error('Failed to fetch scopes', { error: toApiError(err).message })
      throw err
    } finally {
      loading.value = false
    }
  }

  async function fetchScope(scopeId: string) {
    loading.value = true
    error.value = null

    try {
      const scope = apiData<ScopeRecord>(await scopeService.fetchScope(scopeId))
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
      error.value = toApiError(err).message ?? null
      logService.error('Failed to fetch scope', {
        scope_id: scopeId,
        error: toApiError(err).message
      })
      throw err
    } finally {
      loading.value = false
    }
  }

  async function createScope(scopeData: Schema<'ScopeCreate'>) {
    loading.value = true
    error.value = null

    try {
      const newScope = apiData<ScopeRecord>(
        await scopeService.createScope(
          apiData<Parameters<typeof scopeService.createScope>[0]>(scopeData)
        )
      )
      scopes.value.push(newScope)
      currentScope.value = newScope
      currentUserRole.value = 'admin' // Creator is automatically admin

      logService.info('Scope created', { scope_id: newScope.id, name: newScope.name })
      return newScope
    } catch (err) {
      error.value = toApiError(err).message ?? null
      logService.error('Failed to create scope', {
        name: scopeData.name,
        error: toApiError(err).message
      })
      throw err
    } finally {
      loading.value = false
    }
  }

  async function updateScope(scopeId: string, scopeData: Schema<'ScopeUpdate'>) {
    loading.value = true
    error.value = null

    try {
      const updatedScope = apiData<ScopeRecord>(await scopeService.updateScope(scopeId, scopeData))

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
      error.value = toApiError(err).message ?? null
      logService.error('Failed to update scope', {
        scope_id: scopeId,
        error: toApiError(err).message
      })
      throw err
    } finally {
      loading.value = false
    }
  }

  async function deleteScope(scopeId: string) {
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
      error.value = toApiError(err).message ?? null
      logService.error('Failed to delete scope', {
        scope_id: scopeId,
        error: toApiError(err).message
      })
      throw err
    } finally {
      loading.value = false
    }
  }

  async function fetchUserRole(scopeId: string): Promise<string | null> {
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
      const members = apiData<ScopeMember[]>(await scopeService.fetchMembers(scopeId))
      const membership = members.find(m => m.user_id === currentUserId)
      currentUserRole.value = membership?.role || null

      logService.debug('User role fetched', { scope_id: scopeId, role: currentUserRole.value })
      return currentUserRole.value
    } catch (err) {
      currentUserRole.value = null
      logService.error('Failed to fetch user role', {
        scope_id: scopeId,
        error: toApiError(err).message
      })
      throw err
    }
  }

  async function fetchMembers(scopeId: string) {
    try {
      const members = apiData<ScopeMember[]>(await scopeService.fetchMembers(scopeId))
      scopeUsers.value[scopeId] = members
      logService.debug('Scope members fetched', { scope_id: scopeId, count: members.length })
      return members
    } catch (err) {
      logService.error('Failed to fetch members', {
        scope_id: scopeId,
        error: toApiError(err).message
      })
      throw err
    }
  }

  async function fetchStatistics(scopeId: string) {
    try {
      const stats = apiData<ScopeStatisticsRecord>(await scopeService.fetchStatistics(scopeId))
      scopeStatistics.value[scopeId] = stats
      logService.debug('Scope statistics fetched', {
        scope_id: scopeId,
        total_genes: stats.total_genes
      })
      return stats
    } catch (err) {
      logService.error('Failed to fetch statistics', {
        scope_id: scopeId,
        error: toApiError(err).message
      })
      throw err
    }
  }

  async function inviteMember(scopeId: string, invitationData: InviteMemberData) {
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
      logService.error('Failed to invite member', {
        scope_id: scopeId,
        error: toApiError(err).message
      })
      throw err
    }
  }

  async function updateMemberRole(scopeId: string, userId: string, newRole: string) {
    try {
      const result = await scopeService.updateMemberRole(scopeId, userId, newRole)

      // Update in cached users list
      const members = scopeUsers.value[scopeId]
      if (members) {
        const member = members.find(m => m.user_id === userId)
        if (member) {
          member.role = newRole as ScopeMember['role']
        }
      }

      logService.info('Member role updated', { scope_id: scopeId, user_id: userId, role: newRole })
      return result
    } catch (err) {
      logService.error('Failed to update member role', {
        scope_id: scopeId,
        error: toApiError(err).message
      })
      throw err
    }
  }

  async function removeMember(scopeId: string, userId: string) {
    try {
      await scopeService.removeMember(scopeId, userId)

      // Remove from cached users list
      if (scopeUsers.value[scopeId]) {
        scopeUsers.value[scopeId] = scopeUsers.value[scopeId].filter(m => m.user_id !== userId)
      }

      logService.info('Member removed', { scope_id: scopeId, user_id: userId })
    } catch (err) {
      logService.error('Failed to remove member', {
        scope_id: scopeId,
        error: toApiError(err).message
      })
      throw err
    }
  }

  function setCurrentScope(scope: ScopeRecord | null) {
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
