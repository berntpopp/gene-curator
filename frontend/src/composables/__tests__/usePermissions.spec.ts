/**
 * usePermissions Composable Tests
 *
 * Tests for the usePermissions composable to ensure correct
 * role-based access control logic.
 *
 * Test Coverage:
 * - View permissions
 * - Action permissions
 * - Admin permissions
 * - Scope admin permissions
 * - Helper methods
 * - Edge cases (no user, invalid roles)
 *
 * @see src/composables/usePermissions.js
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { isRef } from 'vue'
import { usePermissions } from '../usePermissions'
import { useAuthStore } from '@/stores/auth'

/** Writable view of the auth store for these tests (the JS store infers narrow state types). */
interface TestAuthStore {
  isAuthenticated: boolean
  user: { role?: string; email: string } | null
  hasRole: (role: string) => boolean
  hasAnyRole: (roles: string[]) => boolean
}

const useTestAuthStore = (): TestAuthStore => useAuthStore() as unknown as TestAuthStore

describe('usePermissions', () => {
  beforeEach(() => {
    // Create fresh Pinia instance for each test
    setActivePinia(createPinia())
  })

  it('exposes user, role and authentication state from the store', () => {
    const authStore = useTestAuthStore()
    authStore.isAuthenticated = true
    authStore.user = { role: 'reviewer', email: 'r@example.com' }

    const { user, userRole, isAuthenticated } = usePermissions()

    expect(user.value).toEqual({ role: 'reviewer', email: 'r@example.com' })
    expect(userRole.value).toBe('reviewer')
    expect(isAuthenticated.value).toBe(true)
  })

  it('every permission flag is a boolean computed', () => {
    const authStore = useTestAuthStore()
    authStore.isAuthenticated = true
    authStore.user = { role: 'admin', email: 'a@example.com' }
    authStore.hasRole = vi.fn((role: string) => role === 'admin')
    authStore.hasAnyRole = vi.fn((roles: string[]) => roles.includes('admin'))

    const { can } = usePermissions()
    const flags = Object.values(can).filter(isRef)

    expect(flags.length).toBeGreaterThan(20)
    for (const flag of flags) {
      expect(typeof flag.value).toBe('boolean')
    }
    expect(can.manageUsers.value).toBe(true)
    expect(can.viewScopeStats.value).toBe(true)
  })

  it('hasAllRoles requires every listed role', () => {
    const authStore = useTestAuthStore()
    authStore.hasRole = vi.fn((role: string) => role === 'admin')

    const { can } = usePermissions()

    expect(can.hasAllRoles(['admin'])).toBe(true)
    expect(can.hasAllRoles(['admin', 'curator'])).toBe(false)
  })

  describe('View Permissions', () => {
    it('should allow authenticated users to view dashboard', () => {
      const authStore = useTestAuthStore()
      authStore.isAuthenticated = true
      authStore.user = { role: 'viewer', email: 'test@example.com' }

      const { can } = usePermissions()

      expect(can.viewDashboard.value).toBe(true)
    })

    it('should not allow unauthenticated users to view dashboard', () => {
      const authStore = useTestAuthStore()
      authStore.isAuthenticated = false
      authStore.user = null

      const { can } = usePermissions()

      expect(can.viewDashboard.value).toBe(false)
    })

    it('should allow curators to view curations', () => {
      const authStore = useTestAuthStore()
      authStore.isAuthenticated = true
      authStore.user = { role: 'curator', email: 'curator@example.com' }

      // Mock hasAnyRole method
      authStore.hasAnyRole = vi.fn(roles => {
        return roles.includes('curator')
      })

      const { can } = usePermissions()

      expect(can.viewCurations.value).toBe(true)
    })

    it('should not allow viewers to view curations', () => {
      const authStore = useTestAuthStore()
      authStore.isAuthenticated = true
      authStore.user = { role: 'viewer', email: 'viewer@example.com' }

      // Mock hasAnyRole method
      authStore.hasAnyRole = vi.fn(() => {
        return false
      })

      const { can } = usePermissions()

      expect(can.viewCurations.value).toBe(false)
    })
  })

  describe('Action Permissions', () => {
    it('should allow curators to create assignments', () => {
      const authStore = useTestAuthStore()
      authStore.isAuthenticated = true
      authStore.user = { role: 'curator', email: 'curator@example.com' }

      authStore.hasAnyRole = vi.fn(roles => {
        return roles.includes('curator')
      })

      const { can } = usePermissions()

      expect(can.createAssignment.value).toBe(true)
    })

    it('should allow reviewers to review curations', () => {
      const authStore = useTestAuthStore()
      authStore.isAuthenticated = true
      authStore.user = { role: 'reviewer', email: 'reviewer@example.com' }

      authStore.hasAnyRole = vi.fn(roles => {
        return roles.includes('reviewer')
      })

      const { can } = usePermissions()

      expect(can.reviewCuration.value).toBe(true)
    })

    it('should not allow viewers to create curations', () => {
      const authStore = useTestAuthStore()
      authStore.isAuthenticated = true
      authStore.user = { role: 'viewer', email: 'viewer@example.com' }

      authStore.hasAnyRole = vi.fn(() => false)

      const { can } = usePermissions()

      expect(can.createCuration.value).toBe(false)
    })
  })

  describe('Admin Permissions', () => {
    it('should allow admins to manage users', () => {
      const authStore = useTestAuthStore()
      authStore.isAuthenticated = true
      authStore.user = { role: 'admin', email: 'admin@example.com' }

      authStore.hasRole = vi.fn(role => role === 'admin')

      const { can } = usePermissions()

      expect(can.manageUsers.value).toBe(true)
    })

    it('should allow admins to configure curation', () => {
      const authStore = useTestAuthStore()
      authStore.isAuthenticated = true
      authStore.user = { role: 'admin', email: 'admin@example.com' }

      authStore.hasRole = vi.fn(role => role === 'admin')

      const { can } = usePermissions()

      expect(can.configureCuration.value).toBe(true)
    })

    it('should not allow curators to manage users', () => {
      const authStore = useTestAuthStore()
      authStore.isAuthenticated = true
      authStore.user = { role: 'curator', email: 'curator@example.com' }

      authStore.hasRole = vi.fn(() => false)

      const { can } = usePermissions()

      expect(can.manageUsers.value).toBe(false)
    })
  })

  describe('Scope Admin Permissions', () => {
    it('should allow scope admins to manage scope users', () => {
      const authStore = useTestAuthStore()
      authStore.isAuthenticated = true
      authStore.user = {
        role: 'scope_admin',
        email: 'scope_admin@example.com'
      }

      authStore.hasAnyRole = vi.fn(roles => {
        return roles.includes('scope_admin')
      })

      const { can } = usePermissions()

      expect(can.manageScopeUsers.value).toBe(true)
    })

    it('should allow admins to manage scope users', () => {
      const authStore = useTestAuthStore()
      authStore.isAuthenticated = true
      authStore.user = { role: 'admin', email: 'admin@example.com' }

      authStore.hasAnyRole = vi.fn(roles => {
        return roles.includes('admin')
      })

      const { can } = usePermissions()

      expect(can.manageScopeUsers.value).toBe(true)
    })
  })

  describe('Helper Methods', () => {
    it('should provide hasRole helper', () => {
      const authStore = useTestAuthStore()
      authStore.isAuthenticated = true
      authStore.user = { role: 'admin', email: 'admin@example.com' }

      authStore.hasRole = vi.fn(role => role === 'admin')

      const { can } = usePermissions()

      expect(can.hasRole('admin')).toBe(true)
      expect(can.hasRole('curator')).toBe(false)
    })

    it('should provide hasAnyRole helper', () => {
      const authStore = useTestAuthStore()
      authStore.isAuthenticated = true
      authStore.user = { role: 'curator', email: 'curator@example.com' }

      authStore.hasAnyRole = vi.fn(roles => {
        return roles.includes('curator')
      })

      const { can } = usePermissions()

      expect(can.hasAnyRole(['curator', 'admin'])).toBe(true)
      expect(can.hasAnyRole(['admin'])).toBe(false)
    })
  })

  describe('User Information', () => {
    it('should expose user information', () => {
      const authStore = useTestAuthStore()
      authStore.isAuthenticated = true
      authStore.user = { role: 'curator', email: 'curator@example.com' }

      const { user, userRole, isAuthenticated } = usePermissions()

      expect(user.value).toEqual({
        role: 'curator',
        email: 'curator@example.com'
      })
      expect(userRole.value).toBe('curator')
      expect(isAuthenticated.value).toBe(true)
    })
  })

  describe('Edge Cases', () => {
    it('should handle null user gracefully', () => {
      const authStore = useTestAuthStore()
      authStore.isAuthenticated = false
      authStore.user = null

      authStore.hasRole = vi.fn(() => false)
      authStore.hasAnyRole = vi.fn(() => false)

      const { can } = usePermissions()

      expect(can.viewDashboard.value).toBe(false)
      expect(can.createCuration.value).toBe(false)
      expect(can.manageUsers.value).toBe(false)
    })

    it('should handle missing role gracefully', () => {
      const authStore = useTestAuthStore()
      authStore.isAuthenticated = true
      authStore.user = { email: 'test@example.com' } // No role

      authStore.hasRole = vi.fn(() => false)
      authStore.hasAnyRole = vi.fn(() => false)

      const { can } = usePermissions()

      expect(can.createCuration.value).toBe(false)
    })
  })
})
