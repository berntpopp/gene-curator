/**
 * InviteMemberDialog Tests
 *
 * Role options, invitation payload building, success/failure handling, form
 * reset on open, and validation rules. Internals are reached through the
 * component instance; the user search is stubbed.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { useScopesStore } from '@/stores/scopes'
import InviteMemberDialog from '../InviteMemberDialog.vue'

const confirmMock = vi.hoisted(() => vi.fn())
vi.mock('@/composables/useConfirm', () => ({ useConfirm: () => ({ confirm: confirmMock }) }))

vi.mock('@/services/logService', () => ({
  logService: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() }
}))

interface InviteInternals {
  selectedUser: { id: string; name?: string | null; email?: string | null } | undefined
  selectedRole: string
  notes: string
  canSubmit: boolean
  roleOptions: { value: string; title: string }[]
  notesRules: ((v: string) => true | string)[]
  getInitials: (name: string | null | undefined) => string
  handleSubmit: () => Promise<void>
  handleCancel: () => Promise<void>
  keepDialogOpenWhileMenuOpen: (e: Event) => void
}

describe('InviteMemberDialog', () => {
  let pinia: ReturnType<typeof createPinia>

  beforeEach(() => {
    pinia = createPinia()
    setActivePinia(pinia)
  })

  function mountDialog(props: Record<string, unknown> = {}) {
    const wrapper = mount(InviteMemberDialog, {
      props: { modelValue: true, scopeId: 'scope-1', ...props },
      global: { plugins: [pinia], stubs: { UserSearchAutocomplete: true } }
    })
    return { wrapper, vm: wrapper.vm as unknown as InviteInternals }
  }

  it('offers the four scope roles with descriptions', () => {
    const { vm } = mountDialog()

    expect(vm.roleOptions.map(r => r.value)).toEqual(['admin', 'curator', 'reviewer', 'viewer'])
    expect(vm.selectedRole).toBe('viewer')
  })

  it('enables sending only once a user is chosen', () => {
    const { vm } = mountDialog()
    expect(vm.canSubmit).toBeFalsy()

    vm.selectedUser = { id: 'u1', name: 'Ada' }
    expect(vm.canSubmit).toBeTruthy()
  })

  it('sends the chosen user and role, with notes when given, then emits invited and closes', async () => {
    const store = useScopesStore()
    const invite = vi.spyOn(store, 'inviteMember').mockResolvedValue({ id: 'm-1' } as never)
    const { wrapper, vm } = mountDialog()
    vm.selectedUser = { id: 'u1', name: 'Ada Lovelace', email: 'ada@example.org' }
    vm.selectedRole = 'curator'
    vm.notes = 'Welcome'

    await vm.handleSubmit()
    await flushPromises()

    expect(invite).toHaveBeenCalledWith('scope-1', {
      role: 'curator',
      user_id: 'u1',
      notes: 'Welcome'
    })
    expect(wrapper.emitted('invited')?.[0]).toEqual([
      { id: 'm-1', userName: 'Ada Lovelace', userEmail: 'ada@example.org' }
    ])
    expect(wrapper.emitted('update:modelValue')?.at(-1)).toEqual([false])
  })

  it('does nothing when submitting without a user', async () => {
    const store = useScopesStore()
    const invite = vi.spyOn(store, 'inviteMember')
    const { vm } = mountDialog()

    await vm.handleSubmit()

    expect(invite).not.toHaveBeenCalled()
  })

  it('rethrows a failed invitation so the caller can show it', async () => {
    const store = useScopesStore()
    vi.spyOn(store, 'inviteMember').mockRejectedValueOnce(new Error('already a member'))
    const { vm } = mountDialog()
    vm.selectedUser = { id: 'u1' }

    await expect(vm.handleSubmit()).rejects.toThrow('already a member')
  })

  it('cancels by emitting a closed state after confirming the discard', async () => {
    confirmMock.mockResolvedValue(true)
    const { wrapper, vm } = mountDialog()
    vm.selectedUser = { id: 'u1' }

    await vm.handleCancel()

    expect(confirmMock).toHaveBeenCalledWith(
      expect.objectContaining({ title: 'Discard invitation?' })
    )

    expect(wrapper.emitted('update:modelValue')?.at(-1)).toEqual([false])
    expect(vm.selectedUser).toBeNull()
  })

  it('routes the dialog Escape (cancel) through the discard confirmation', async () => {
    confirmMock.mockResolvedValue(true)
    const { wrapper, vm } = mountDialog()
    vm.notes = 'typed'

    wrapper.findComponent({ name: 'BaseDialog' }).vm.$emit('cancel')
    await flushPromises()

    expect(confirmMock).toHaveBeenCalledWith(
      expect.objectContaining({ title: 'Discard invitation?' })
    )
    expect(wrapper.emitted('update:modelValue')?.at(-1)).toEqual([false])
  })

  it('resets the form each time the dialog opens', async () => {
    const { wrapper, vm } = mountDialog({ modelValue: false })
    vm.selectedRole = 'admin'
    vm.notes = 'old'

    await wrapper.setProps({ modelValue: true })

    expect(vm.selectedRole).toBe('viewer')
    expect(vm.notes).toBe('')
  })

  it('derives initials from the name', () => {
    const { vm } = mountDialog()

    expect(vm.getInitials('Ada Lovelace')).toBe('AL')
    expect(vm.getInitials('Plato')).toBe('P')
    expect(vm.getInitials('  Grace   Hopper ')).toBe('GH')
    expect(vm.getInitials('')).toBe('?')
    expect(vm.getInitials(null)).toBe('?')
  })

  it('validates the notes length', () => {
    const { vm } = mountDialog()

    expect(vm.notesRules[0]?.('x'.repeat(201))).toBe('Notes must be 200 characters or less')
    expect(vm.notesRules[0]?.('short')).toBe(true)
  })

  it('keeps the input when the discard is declined', async () => {
    confirmMock.mockResolvedValue(false)
    const { wrapper, vm } = mountDialog()
    vm.notes = 'remember me'

    await vm.handleCancel()

    expect(vm.notes).toBe('remember me')
    expect(wrapper.emitted('update:modelValue')).toBeUndefined()
  })

  it('closes without asking when the form is empty', async () => {
    confirmMock.mockClear()
    const { wrapper, vm } = mountDialog()

    await vm.handleCancel()

    expect(confirmMock).not.toHaveBeenCalled()
    expect(wrapper.emitted('update:modelValue')?.at(-1)).toEqual([false])
  })

  it('stops an Escape that only closes the open autocomplete menu', () => {
    const { vm } = mountDialog()
    const input = document.createElement('input')
    const event = new KeyboardEvent('keydown', { key: 'Escape' })
    Object.defineProperty(event, 'target', { value: input })
    const stop = vi.spyOn(event, 'stopPropagation')

    input.setAttribute('aria-expanded', 'false')
    vm.keepDialogOpenWhileMenuOpen(event)
    expect(stop).not.toHaveBeenCalled()

    input.setAttribute('aria-expanded', 'true')
    vm.keepDialogOpenWhileMenuOpen(event)
    expect(stop).toHaveBeenCalled()
  })
})
