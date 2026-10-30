import { describe, it, expect, vi, beforeEach } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import UserScopeRoles from '../UserScopeRoles.vue'
import { useUserScopeRoles } from '../useUserScopeRoles'
import { scopeService } from '@/services/scopeService'

const showSnackbar = vi.hoisted(() => vi.fn())
vi.mock('@/composables/useNotifications', () => ({ showSnackbar }))
vi.mock('@/services/scopeService', () => ({
  scopeService: {
    fetchScopes: vi.fn(),
    fetchMembers: vi.fn(),
    inviteMember: vi.fn(),
    updateMemberRole: vi.fn(),
    removeMember: vi.fn()
  }
}))
const svc = vi.mocked(scopeService)

const kidney = { id: 's1', name: 'kidney-genetics' }
const heart = { id: 's2', name: 'cardio' }

function mountRoles(disabled = false) {
  return mount(UserScopeRoles, {
    props: {
      userId: 'u1',
      roles: [{ scope_id: 's1', scope_name: 'kidney-genetics', role: 'curator' }],
      allScopes: [kidney, heart] as never,
      disabled
    }
  })
}
const select = (w: ReturnType<typeof mount>, testid: string) =>
  w.findAllComponents({ name: 'VSelect' }).find(c => c.attributes('data-testid') === testid)!

describe('UserScopeRoles (#218)', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    svc.fetchMembers.mockResolvedValue([])
  })

  it('grants a role directly, so the membership is accepted at once', async () => {
    svc.inviteMember.mockResolvedValue({} as never)
    const w = mountRoles()
    expect((select(w, 'grant-scope').props('items') as { id: string }[]).map(s => s.id)).toEqual([
      's2'
    ])
    select(w, 'grant-scope').vm.$emit('update:modelValue', 's2')
    select(w, 'grant-role').vm.$emit('update:modelValue', 'reviewer')
    await flushPromises()
    await w.find('[data-testid=grant]').trigger('click')
    await flushPromises()
    expect(svc.inviteMember).toHaveBeenCalledWith('s2', { user_id: 'u1', role: 'reviewer' }, true)
    expect(showSnackbar).toHaveBeenCalledWith('Added to cardio as reviewer', 'success')
    expect(w.emitted('changed')).toHaveLength(1)
  })

  it('changes and removes an existing role', async () => {
    svc.updateMemberRole.mockResolvedValue({} as never)
    svc.removeMember.mockResolvedValue()
    const w = mountRoles()
    select(w, 'role-s1').vm.$emit('update:modelValue', 'admin')
    await flushPromises()
    expect(svc.updateMemberRole).toHaveBeenCalledWith('s1', 'u1', 'admin')
    await w.find('[data-testid=remove-s1]').trigger('click')
    await flushPromises()
    expect(svc.removeMember).toHaveBeenCalledWith('s1', 'u1')
    expect(w.emitted('changed')).toHaveLength(2)
  })

  it('shows the API reason when a change is refused and keeps the choice', async () => {
    svc.inviteMember.mockRejectedValue({
      response: { data: { detail: 'You cannot add yourself to a scope' } }
    })
    const w = mountRoles()
    select(w, 'grant-scope').vm.$emit('update:modelValue', 's2')
    await flushPromises()
    await w.find('[data-testid=grant]').trigger('click')
    await flushPromises()
    expect(showSnackbar).toHaveBeenCalledWith('You cannot add yourself to a scope', 'error')
    expect(w.emitted('changed')).toBeUndefined()
    expect(select(w, 'grant-scope').props('modelValue')).toBe('s2')
  })

  it('is read-only for the own account', () => {
    const w = mountRoles(true)
    expect(w.text()).toContain('You cannot change your own scope roles.')
    expect(w.find('[data-testid=grant]').attributes('disabled')).toBeDefined()
  })
})

describe('useUserScopeRoles', () => {
  beforeEach(() => setActivePinia(createPinia()))

  it('groups the accepted members of every scope by user', async () => {
    svc.fetchScopes.mockResolvedValue([kidney, heart] as never)
    svc.fetchMembers.mockImplementation(
      async id =>
        (id === 's1'
          ? [{ user_id: 'u1', role: 'curator' }]
          : [
              { user_id: 'u1', role: 'viewer' },
              { user_id: 'u2', role: 'admin' }
            ]) as never
    )
    const { rolesByUser, scopes, load } = useUserScopeRoles()
    await load()
    expect(svc.fetchScopes).toHaveBeenCalledWith({ limit: 1000 })
    expect(scopes.value).toHaveLength(2)
    expect(rolesByUser.value).toEqual({
      u1: [
        { scope_id: 's1', scope_name: 'kidney-genetics', role: 'curator' },
        { scope_id: 's2', scope_name: 'cardio', role: 'viewer' }
      ],
      u2: [{ scope_id: 's2', scope_name: 'cardio', role: 'admin' }]
    })
  })
})
