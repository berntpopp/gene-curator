/**
 * usePermissions Composable
 *
 * Provides reactive permission checking for role-based access control.
 * Wraps the auth store with computed properties for better performance
 * and provides a single source of truth for all permission checks.
 *
 * Benefits:
 * - DRY: No scattered role checks throughout components
 * - Type-safe: Centralized permission definitions
 * - Reactive: Automatically updates when auth state changes
 * - Testable: Easy to mock for testing
 *
 * @example
 * ```vue
 * <template>
 *   <v-btn v-if="can.createCuration.value" @click="create">New Curation</v-btn>
 * </template>
 *
 * <script setup lang="ts">
 * import { usePermissions } from '@/composables/usePermissions'
 * const { can } = usePermissions()
 * </script>
 * ```
 *
 * @see docs/NAVIGATION_RESTRUCTURE_PLAN.md#permissions-management-dry
 */

import { computed } from 'vue'
import type { ComputedRef } from 'vue'
import { useAuthStore } from '@/stores/auth'

/** Computed permission flags. Each is a ComputedRef<boolean> that tracks auth state. */
export interface PermissionChecks {
  // View permissions
  viewDashboard: ComputedRef<boolean>
  viewCurations: ComputedRef<boolean>
  viewValidation: ComputedRef<boolean>
  viewAdminPages: ComputedRef<boolean>

  // Action permissions
  createAssignment: ComputedRef<boolean>
  createPrecuration: ComputedRef<boolean>
  createCuration: ComputedRef<boolean>
  reviewCuration: ComputedRef<boolean>
  editOwnCuration: ComputedRef<boolean>
  deleteOwnCuration: ComputedRef<boolean>
  submitForReview: ComputedRef<boolean>
  approveCuration: ComputedRef<boolean>
  rejectCuration: ComputedRef<boolean>

  // Admin permissions
  manageUsers: ComputedRef<boolean>
  manageGenes: ComputedRef<boolean>
  configureCuration: ComputedRef<boolean>
  manageScopes: ComputedRef<boolean>
  manageSchemas: ComputedRef<boolean>
  manageWorkflows: ComputedRef<boolean>

  // Scope admin permissions
  manageScopeUsers: ComputedRef<boolean>
  assignCurators: ComputedRef<boolean>
  viewScopeStats: ComputedRef<boolean>

  // Helper methods
  hasRole: (role: string) => boolean
  hasAnyRole: (roles: string[]) => boolean
  hasAllRoles: (roles: string[]) => boolean
}

export interface UsePermissionsReturn {
  can: PermissionChecks
  user: ComputedRef<ReturnType<typeof useAuthStore>['user']>
  userRole: ComputedRef<string>
  isAuthenticated: ComputedRef<boolean>
}

/**
 * Permission check composable
 */
export function usePermissions(): UsePermissionsReturn {
  const authStore = useAuthStore()

  /**
   * Reactive permission checks
   * Each property is a computed that automatically updates with auth state
   */
  const can: PermissionChecks = {
    viewDashboard: computed(() => authStore.isAuthenticated),
    viewCurations: computed(() => authStore.hasAnyRole(['curator', 'reviewer', 'admin'])),
    viewValidation: computed(() => authStore.hasAnyRole(['curator', 'reviewer', 'admin'])),
    viewAdminPages: computed(() => authStore.hasRole('admin')),

    createAssignment: computed(() => authStore.hasAnyRole(['curator', 'admin'])),
    createPrecuration: computed(() => authStore.hasAnyRole(['curator', 'admin'])),
    createCuration: computed(() => authStore.hasAnyRole(['curator', 'admin'])),
    reviewCuration: computed(() => authStore.hasAnyRole(['reviewer', 'admin'])),
    editOwnCuration: computed(() => authStore.hasAnyRole(['curator', 'admin'])),
    deleteOwnCuration: computed(() => authStore.hasAnyRole(['curator', 'admin'])),
    submitForReview: computed(() => authStore.hasAnyRole(['curator', 'admin'])),
    approveCuration: computed(() => authStore.hasAnyRole(['reviewer', 'admin'])),
    rejectCuration: computed(() => authStore.hasAnyRole(['reviewer', 'admin'])),

    manageUsers: computed(() => authStore.hasRole('admin')),
    manageGenes: computed(() => authStore.hasRole('admin')),
    configureCuration: computed(() => authStore.hasRole('admin')),
    manageScopes: computed(() => authStore.hasRole('admin')),
    manageSchemas: computed(() => authStore.hasRole('admin')),
    manageWorkflows: computed(() => authStore.hasRole('admin')),

    manageScopeUsers: computed(() => authStore.hasAnyRole(['scope_admin', 'admin'])),
    assignCurators: computed(() => authStore.hasAnyRole(['scope_admin', 'admin'])),
    viewScopeStats: computed(() => authStore.hasAnyRole(['scope_admin', 'admin'])),

    hasRole: (role: string): boolean => authStore.hasRole(role),
    hasAnyRole: (roles: string[]): boolean => authStore.hasAnyRole(roles),
    hasAllRoles: (roles: string[]): boolean => roles.every(role => authStore.hasRole(role))
  }

  /**
   * Get user information
   */
  const user = computed(() => authStore.user)
  const userRole = computed(() => authStore.userRole)
  const isAuthenticated = computed(() => authStore.isAuthenticated)

  return {
    can,
    user,
    userRole,
    isAuthenticated
  }
}

export default usePermissions
