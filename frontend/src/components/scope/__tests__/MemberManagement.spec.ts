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
import { snackbarState } from '@/composables/useNotifications'

const confirm = vi.hoisted(() => vi.fn())
vi.mock('@/composables/useConfirm', () => ({ useConfirm: () => ({ confirm }) }))

vi.mock('@/services/scopeService', () => ({
  scopeService: { fetchMembers: vi.fn() }
}))

vi.mock('@/services/logService', () => ({
  logService: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() }
}))

interface MemberInternals {
  members: { user_id: string }[]
  existingMemberIds: string[]
  showRemoveDialog: boolean
  memberToRemove: { user_id: string } | null
  updateRole: (userId: string, role: string) => Promise<void>
  requestRoleChange: (member: { user_id: string; role: string }, role: string) => Promise<void>
  confirmRemoveMember: (member: { user_id: string; role: string }) => void
  removeMember: () => Promise<void>
  handleInvited: (payload: {
    direct?: boolean
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
    user_orcid: '0000-0002-1825-0097',
    is_pending: false
  },
  {
    user_id: 'u2',
    role: 'viewer',
    user_email: 'bob@example.org',
    invited_at: '2026-10-01T09:30:00Z',
    is_pending: true
  }
]

describe('MemberManagement', () => {
  let pinia: ReturnType<typeof createPinia>

  beforeEach(() => {
    pinia = createPinia()
    setActivePinia(pinia)
    confirm.mockReset()
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
    expect(wrapper.text()).toContain('Invited 2026-10-01')
  })

  it('shows initials and one role label per row, and ORCID as a link', async () => {
    const { wrapper } = await mountMembers()

    const rows = wrapper.findAll('.v-list-item')
    expect(rows[0]!.find('.v-avatar').text()).toBe('AL')
    expect(rows[0]!.find('.v-avatar .v-icon').exists()).toBe(false)
    expect(rows[0]!.text().match(/Admin/g)).toHaveLength(1)
    const orcid = rows[0]!.find('a[href="https://orcid.org/0000-0002-1825-0097"]')
    expect(orcid.exists()).toBe(true)
    expect(orcid.attributes('target')).toBe('_blank')
    expect(orcid.attributes('rel')).toContain('noopener')
  })

  it('marks an AI agent account (#639) and no person', async () => {
    vi.mocked(scopeService.fetchMembers).mockResolvedValue([
      { ...members[0], user_id: 'bot', user_full_name: 'Judge agent', user_is_agent: true },
      members[1]
    ] as never)
    const { wrapper } = await mountMembers()

    const rows = wrapper.findAll('.v-list-item')
    expect(rows[0]!.text()).toContain('Agent')
    expect(rows[1]!.text()).not.toContain('Agent')
  })

  it('uses the local calendar date for invitations across UTC midnight', async () => {
    const localMidnight = new Date(2026, 9, 22, 0, 30)
    vi.mocked(scopeService.fetchMembers).mockResolvedValue([
      { ...members[1], invited_at: localMidnight.toISOString() }
    ] as never)
    const { wrapper } = await mountMembers()
    expect(wrapper.text()).toContain('Invited 2026-10-22')
  })

  it('explains to non-admins who manages members', async () => {
    const viewer = await mountMembers('curator')
    expect(viewer.wrapper.text()).toContain('Only scope admins can manage members.')
    const admin = await mountMembers('admin')
    expect(admin.wrapper.text()).not.toContain('Only scope admins can manage members.')
  })

  it('confirms before changing a role and skips when declined or unchanged', async () => {
    const { store, vm } = await mountMembers()
    const update = vi.spyOn(store, 'updateMemberRole').mockResolvedValue({} as never)
    const bob = { user_id: 'u2', role: 'viewer' }

    confirm.mockResolvedValueOnce(false)
    await vm.requestRoleChange(bob, 'curator')
    expect(update).not.toHaveBeenCalled()

    await vm.requestRoleChange(bob, 'viewer')
    expect(confirm).toHaveBeenCalledTimes(1)

    confirm.mockResolvedValueOnce(true)
    await vm.requestRoleChange(bob, 'curator')
    expect(confirm).toHaveBeenLastCalledWith(
      expect.objectContaining({ title: expect.stringContaining('curator') })
    )
    expect(update).toHaveBeenCalledWith('scope-1', 'u2', 'curator')
  })

  it('says what removal does to gene assignments, and revokes pending invitations', async () => {
    const { vm } = await mountMembers()

    vm.confirmRemoveMember({ user_id: 'u1', role: 'admin', is_pending: false } as never)
    await flushPromises()
    expect(document.body.textContent).toContain('gene assignments are not changed')

    vm.confirmRemoveMember({ user_id: 'u2', role: 'viewer', is_pending: true } as never)
    await flushPromises()
    expect(document.body.textContent).toContain('Revoke invitation')
  })

  it('shows an empty state when the scope has no members', async () => {
    vi.mocked(scopeService.fetchMembers).mockResolvedValueOnce([] as never)
    const { wrapper } = await mountMembers()

    expect(wrapper.text()).toContain('No members found')
  })

  it('offers invitations to admins only', async () => {
    const admin = await mountMembers('admin')
    expect(admin.wrapper.text()).toContain('Invite member')

    const viewer = await mountMembers('viewer')
    expect(viewer.wrapper.text()).not.toContain('Invite member')
  })

  it('keeps the invite button out of the card title (which shrinks buttons)', async () => {
    const { wrapper } = await mountMembers('admin')

    const button = wrapper.findAll('button').find(b => b.text().includes('Invite member'))
    expect(button).toBeDefined()
    expect(button!.element.closest('.v-card-title')).toBeNull()
  })

  it('exposes the current member IDs for the invite search exclusion', async () => {
    const { vm } = await mountMembers()

    expect(vm.existingMemberIds).toEqual(['u1', 'u2'])
  })

  it('excludes a platform admin who is not a member from their own search', async () => {
    const { vm } = await mountMembers()
    const auth = useAuthStore()
    auth.user = { id: 'pa', role: 'admin' } as unknown as typeof auth.user

    expect(vm.existingMemberIds).toEqual(['u1', 'u2', 'pa'])
  })

  it('reports a failed member load', async () => {
    vi.mocked(scopeService.fetchMembers).mockRejectedValueOnce(new Error('403'))
    await mountMembers()

    expect(snackbarState.message).toBe('Failed to load members')
  })

  it('changes a role and reloads the list', async () => {
    const { store, vm } = await mountMembers()
    const update = vi.spyOn(store, 'updateMemberRole').mockResolvedValue({} as never)

    await vm.updateRole('u2', 'curator')
    await flushPromises()

    expect(update).toHaveBeenCalledWith('scope-1', 'u2', 'curator')
    expect(snackbarState.message).toBe('Member role updated successfully')
    expect(scopeService.fetchMembers).toHaveBeenCalledTimes(2)
  })

  it('reports a failed role change', async () => {
    const { store, vm } = await mountMembers()
    vi.spyOn(store, 'updateMemberRole').mockRejectedValueOnce(new Error('nope'))

    await vm.updateRole('u2', 'admin')

    expect(snackbarState.message).toBe('Failed to update member role')
  })

  it('asks for confirmation, then removes the member and reloads', async () => {
    const { store, vm, wrapper } = await mountMembers()
    const remove = vi.spyOn(store, 'removeMember').mockResolvedValue(undefined as never)

    vm.confirmRemoveMember({ user_id: 'u2', role: 'viewer' })
    expect(vm.showRemoveDialog).toBe(true)

    await vm.removeMember()
    await flushPromises()

    expect(remove).toHaveBeenCalledWith('scope-1', 'u2')
    expect(vm.showRemoveDialog).toBe(false)
    expect(vm.memberToRemove).toBeNull()
    expect(snackbarState.message).toBe('Member removed successfully')
    expect(wrapper.emitted('changed')).toHaveLength(1)
  })

  it('keeps the confirmation open and reports a failed removal', async () => {
    const { store, vm } = await mountMembers()
    vi.spyOn(store, 'removeMember').mockRejectedValueOnce(new Error('locked'))
    vm.confirmRemoveMember({ user_id: 'u2', role: 'viewer' })

    await vm.removeMember()

    expect(vm.showRemoveDialog).toBe(true)
    expect(snackbarState.message).toBe('Failed to remove member')
  })

  it('does nothing when no member is selected for removal', async () => {
    const { store, vm } = await mountMembers()
    const remove = vi.spyOn(store, 'removeMember')

    await vm.removeMember()

    expect(remove).not.toHaveBeenCalled()
  })

  it('announces an invitation and reloads the list', async () => {
    const { vm, wrapper } = await mountMembers()

    await vm.handleInvited({ userName: 'Grace Hopper', id: 'm-9' })
    await flushPromises()

    expect(snackbarState.message).toBe('Invitation sent to Grace Hopper')
    expect(scopeService.fetchMembers).toHaveBeenCalledTimes(2)
    expect(wrapper.emitted('changed')).toHaveLength(1) // the scope header's counts refresh (#393)
  })

  it('falls back to the invitee email in the announcement', async () => {
    const { vm } = await mountMembers()

    await vm.handleInvited({ userEmail: 'new@example.org' })

    expect(snackbarState.message).toBe('Invitation sent to new@example.org')
  })

  it('announces a direct add as added, not invited', async () => {
    const { vm } = await mountMembers()

    await vm.handleInvited({ userName: 'Grace Hopper', direct: true })

    expect(snackbarState.message).toBe('Grace Hopper added to the scope')
  })
})
