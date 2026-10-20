/**
 * MemberManagement Tests
 *
 * Member list with pending state, role-gated actions, role change, removal and
 * invitation refresh, with feedback snackbars. Internals are reached through the
 * component instance.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { scopeService } from '@/services/scopeService'
import { useScopesStore } from '@/stores/scopes'
import { useAuthStore } from '@/stores/auth'
import MemberManagement from '../MemberManagement.vue'
import { stubVisualViewport } from './overlayStubs'

vi.mock('@/services/scopeService', () => ({
  scopeService: { fetchMembers: vi.fn() }
}))

vi.mock('@/services/logService', () => ({
  logService: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() }
}))

interface MemberInternals {
  members: { user_id: string }[]
  existingMemberIds: string[]
  snackbarMessage: string
  showRemoveDialog: boolean
  memberToRemove: { user_id: string } | null
  updateRole: (userId: string, role: string) => Promise<void>
  confirmRemoveMember: (member: { user_id: string; role: string }) => void
  removeMember: () => Promise<void>
  handleInvited: (payload: {
    userName?: string | null
    userEmail?: string | null
    id?: string
  }) => Promise<void>
}

const members = [
  {
    user_id: 'u1',
    role: 'admin',
    user_full_name: 'Ada Lovelace',
    user_email: 'ada@example.org',
    is_pending: false
  },
  {
    user_id: 'u2',
    role: 'viewer',
    user_email: 'bob@example.org',
    user_orcid: '0000-0001',
    is_pending: true
  }
]

describe('MemberManagement', () => {
  let pinia: ReturnType<typeof createPinia>

  beforeEach(() => {
    stubVisualViewport()
    pinia = createPinia()
    setActivePinia(pinia)
    vi.mocked(scopeService.fetchMembers).mockReset()
    vi.mocked(scopeService.fetchMembers).mockResolvedValue(members as never)
  })

  async function mountMembers(role: string | null = 'admin') {
    const store = useScopesStore()
    store.currentUserRole = role as never
    const auth = useAuthStore()
    auth.user = { id: 'u1', role: 'admin' } as unknown as typeof auth.user
    const wrapper = mount(MemberManagement, {
      props: { scopeId: 'scope-1' },
      global: { plugins: [pinia], stubs: { InviteMemberDialog: true } }
    })
    await flushPromises()
    return { wrapper, store, vm: wrapper.vm as unknown as MemberManagementInternals }
  }
  type MemberManagementInternals = MemberInternals

  it('lists members with names, emails, ORCID and the Invited state', async () => {
    const { wrapper } = await mountMembers()

    expect(scopeService.fetchMembers).toHaveBeenCalledWith('scope-1', { includePending: true })
    expect(wrapper.text()).toContain('Ada Lovelace')
    expect(wrapper.text()).toContain('bob@example.org')
    expect(wrapper.text()).toContain('ORCID: 0000-0001')
    expect(wrapper.text()).toContain('Invited')
  })

  it('shows an empty state when the scope has no members', async () => {
    vi.mocked(scopeService.fetchMembers).mockResolvedValueOnce([] as never)
    const { wrapper } = await mountMembers()

    expect(wrapper.text()).toContain('No members found')
  })

  it('offers invitations to admins only', async () => {
    const admin = await mountMembers('admin')
    expect(admin.wrapper.text()).toContain('Invite Member')

    const viewer = await mountMembers('viewer')
    expect(viewer.wrapper.text()).not.toContain('Invite Member')
  })

  it('exposes the current member IDs for the invite search exclusion', async () => {
    const { vm } = await mountMembers()

    expect(vm.existingMemberIds).toEqual(['u1', 'u2'])
  })

  it('reports a failed member load', async () => {
    vi.mocked(scopeService.fetchMembers).mockRejectedValueOnce(new Error('403'))
    const { vm } = await mountMembers()

    expect(vm.snackbarMessage).toBe('Failed to load members')
  })

  it('changes a role and reloads the list', async () => {
    const { store, vm } = await mountMembers()
    const update = vi.spyOn(store, 'updateMemberRole').mockResolvedValue({} as never)

    await vm.updateRole('u2', 'curator')
    await flushPromises()

    expect(update).toHaveBeenCalledWith('scope-1', 'u2', 'curator')
    expect(vm.snackbarMessage).toBe('Member role updated successfully')
    expect(scopeService.fetchMembers).toHaveBeenCalledTimes(2)
  })

  it('reports a failed role change', async () => {
    const { store, vm } = await mountMembers()
    vi.spyOn(store, 'updateMemberRole').mockRejectedValueOnce(new Error('nope'))

    await vm.updateRole('u2', 'admin')

    expect(vm.snackbarMessage).toBe('Failed to update member role')
  })

  it('asks for confirmation, then removes the member and reloads', async () => {
    const { store, vm } = await mountMembers()
    const remove = vi.spyOn(store, 'removeMember').mockResolvedValue(undefined as never)

    vm.confirmRemoveMember({ user_id: 'u2', role: 'viewer' })
    expect(vm.showRemoveDialog).toBe(true)

    await vm.removeMember()
    await flushPromises()

    expect(remove).toHaveBeenCalledWith('scope-1', 'u2')
    expect(vm.showRemoveDialog).toBe(false)
    expect(vm.memberToRemove).toBeNull()
    expect(vm.snackbarMessage).toBe('Member removed successfully')
  })

  it('keeps the confirmation open and reports a failed removal', async () => {
    const { store, vm } = await mountMembers()
    vi.spyOn(store, 'removeMember').mockRejectedValueOnce(new Error('locked'))
    vm.confirmRemoveMember({ user_id: 'u2', role: 'viewer' })

    await vm.removeMember()

    expect(vm.showRemoveDialog).toBe(true)
    expect(vm.snackbarMessage).toBe('Failed to remove member')
  })

  it('does nothing when no member is selected for removal', async () => {
    const { store, vm } = await mountMembers()
    const remove = vi.spyOn(store, 'removeMember')

    await vm.removeMember()

    expect(remove).not.toHaveBeenCalled()
  })

  it('announces an invitation and reloads the list', async () => {
    const { vm } = await mountMembers()

    await vm.handleInvited({ userName: 'Grace Hopper', id: 'm-9' })
    await flushPromises()

    expect(vm.snackbarMessage).toBe('Invitation sent to Grace Hopper')
    expect(scopeService.fetchMembers).toHaveBeenCalledTimes(2)
  })

  it('falls back to the invitee email in the announcement', async () => {
    const { vm } = await mountMembers()

    await vm.handleInvited({ userEmail: 'new@example.org' })

    expect(vm.snackbarMessage).toBe('Invitation sent to new@example.org')
  })
})
