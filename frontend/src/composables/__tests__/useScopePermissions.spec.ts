import { describe, it, expect } from 'vitest'
import { ref } from 'vue'
import { useScopePermissions } from '../useScopePermissions'

describe('useScopePermissions', () => {
  it('admin has every scope permission', () => {
    const p = useScopePermissions('admin')

    expect(p.canManageScope.value).toBe(true)
    expect(p.canInviteMembers.value).toBe(true)
    expect(p.canCurate.value).toBe(true)
    expect(p.canReview.value).toBe(true)
    expect(p.canViewMembers.value).toBe(true)
    expect(p.canEditMemberRoles.value).toBe(true)
    expect(p.canRemoveMembers.value).toBe(true)
    expect(p.canViewStatistics.value).toBe(true)
    expect(p.canCreateAssignments.value).toBe(true)
    expect(p.canManageWorkflows.value).toBe(true)
    expect(p.isAdmin.value).toBe(true)
  })

  it('curator can curate, view members and create assignments only', () => {
    const p = useScopePermissions('curator')

    expect(p.canCurate.value).toBe(true)
    expect(p.canCreateAssignments.value).toBe(true)
    expect(p.canViewMembers.value).toBe(true)
    expect(p.canViewStatistics.value).toBe(true)
    expect(p.canReview.value).toBe(false)
    expect(p.canManageScope.value).toBe(false)
    expect(p.canInviteMembers.value).toBe(false)
    expect(p.isCurator.value).toBe(true)
  })

  it('reviewer can review and view members but not curate', () => {
    const p = useScopePermissions('reviewer')

    expect(p.canReview.value).toBe(true)
    expect(p.canViewMembers.value).toBe(true)
    expect(p.canCurate.value).toBe(false)
    expect(p.canManageWorkflows.value).toBe(false)
    expect(p.isReviewer.value).toBe(true)
  })

  it('viewer is read-only with no management permissions', () => {
    const p = useScopePermissions('viewer')

    expect(p.isViewer.value).toBe(true)
    expect(p.hasAnyRole.value).toBe(true)
    expect(p.canCurate.value).toBe(false)
    expect(p.canReview.value).toBe(false)
    expect(p.canViewMembers.value).toBe(false)
    expect(p.canViewStatistics.value).toBe(false)
  })

  it('null, undefined or empty role grants nothing', () => {
    for (const role of [null, undefined, ''] as const) {
      const p = useScopePermissions(role)

      expect(p.hasAnyRole.value).toBe(false)
      expect(p.canCurate.value).toBe(false)
      expect(p.isAdmin.value).toBe(false)
    }
  })

  it('reacts to a reactive role ref', () => {
    const role = ref<string | null>('viewer')
    const p = useScopePermissions(role)

    expect(p.canCurate.value).toBe(false)
    role.value = 'curator'
    expect(p.canCurate.value).toBe(true)
  })
})
