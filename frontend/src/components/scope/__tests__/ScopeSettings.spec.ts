/**
 * ScopeSettings Tests
 *
 * Workflow pair selection, editing and saving of scope fields, role-gated
 * editing, and the delete flow with its active-assignment confirmation.
 * Internals are reached through the component instance.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { scopesAPI } from '@/api/scopes'
import { schemasAPI } from '@/api/schemas'
import { useScopesStore } from '@/stores/scopes'
import { useAuthStore } from '@/stores/auth'
import ScopeSettings from '../ScopeSettings.vue'
import { snackbarState } from '@/composables/useNotifications'

const guard = vi.hoisted(() => ({ fn: null as null | (() => Promise<boolean> | boolean) }))
const confirm = vi.hoisted(() => vi.fn())
vi.mock('vue-router', () => ({
  onBeforeRouteLeave: (cb: () => Promise<boolean> | boolean) => (guard.fn = cb)
}))
vi.mock('@/composables/useConfirm', () => ({ useConfirm: () => ({ confirm }) }))

vi.mock('@/api/scopes', () => ({
  scopesAPI: { updateScope: vi.fn(), deleteScope: vi.fn() }
}))

vi.mock('@/api/schemas', () => ({
  schemasAPI: { getWorkflowPairs: vi.fn(), getSchemas: vi.fn() }
}))

vi.mock('@/services/logService', () => ({
  logService: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() }
}))

interface SettingsInternals {
  isDirty: boolean
  typedName: string
  showDeleteDialog: boolean
  editableScope: { display_name: string }
  selectedWorkflowPairId: string | null
  canEditSettings: boolean
  canDeleteScope: boolean
  hasActiveAssignments: boolean
  saveSettings: () => Promise<void>
  deleteScope: () => Promise<void>
  openDeleteDialog: () => void
  handleWorkflowPairChange: () => void
}

const pair = {
  id: 'wp-1',
  name: 'ClinGen SOP v11',
  version: '1.0',
  description: 'Standard workflow',
  precuration_schema_id: 'sch-pre',
  curation_schema_id: 'sch-cur',
  is_active: true,
  is_default: true
}
const schemas = [
  { id: 'sch-pre', name: 'Precuration v1' },
  { id: 'sch-cur', name: 'Curation v1' }
] as Awaited<ReturnType<typeof schemasAPI.getSchemas>>

const baseScope = {
  id: 'scope-1',
  name: 'kidney',
  display_name: 'Kidney',
  description: 'Renal',
  institution: 'Charité',
  is_public: false,
  created_by: 'user-1',
  default_workflow_pair_id: null as string | null
}

describe('ScopeSettings', () => {
  let pinia: ReturnType<typeof createPinia>

  beforeEach(() => {
    pinia = createPinia()
    setActivePinia(pinia)
    guard.fn = null
    confirm.mockReset()
    vi.mocked(schemasAPI.getWorkflowPairs).mockReset()
    vi.mocked(schemasAPI.getWorkflowPairs).mockResolvedValue([pair])
    vi.mocked(schemasAPI.getSchemas).mockReset()
    vi.mocked(schemasAPI.getSchemas).mockResolvedValue(schemas)
    vi.mocked(scopesAPI.updateScope).mockReset()
    vi.mocked(scopesAPI.updateScope).mockResolvedValue({} as never)
    vi.mocked(scopesAPI.deleteScope).mockReset()
    vi.mocked(scopesAPI.deleteScope).mockResolvedValue({} as never)
  })

  async function mountSettings(
    opts: {
      scope?: Partial<typeof baseScope>
      statistics?: { total_genes_assigned?: number } | null
      role?: 'admin' | 'curator' | 'user' | null
      userId?: string
    } = {}
  ) {
    const auth = useAuthStore()
    auth.user = (
      opts.role === null ? null : { id: opts.userId ?? 'user-2', role: opts.role ?? 'curator' }
    ) as typeof auth.user
    auth.isAuthenticated = true
    const wrapper = mount(ScopeSettings, {
      props: { scope: { ...baseScope, ...opts.scope }, statistics: opts.statistics ?? null },
      global: { plugins: [pinia] }
    })
    await flushPromises()
    return { wrapper, auth, vm: wrapper.vm as unknown as SettingsInternals }
  }

  it('loads active workflow pairs and warns when none is configured', async () => {
    const { wrapper, vm } = await mountSettings()

    expect(schemasAPI.getWorkflowPairs).toHaveBeenCalledWith({ active_only: true })
    expect(vm.selectedWorkflowPairId).toBeNull()
    expect(wrapper.text()).toContain('No workflow configured.')
    expect(wrapper.text()).not.toContain('Precuration schema')
  })

  it('shows the linked schemas of the configured workflow pair', async () => {
    const { wrapper } = await mountSettings({ scope: { default_workflow_pair_id: 'wp-1' } })

    expect(wrapper.text()).not.toContain('No workflow configured.')
    expect(wrapper.text()).toContain('Precuration schema')
    expect(wrapper.text()).toContain('Precuration v1')
    expect(wrapper.text()).toContain('Curation v1')
  })

  it('shows a fallback when the linked schemas cannot be resolved', async () => {
    vi.mocked(schemasAPI.getSchemas).mockResolvedValueOnce([])
    const { wrapper } = await mountSettings({ scope: { default_workflow_pair_id: 'wp-1' } })

    expect(wrapper.text()).toContain('Not configured')
  })

  it('reports a failure to load workflow pairs', async () => {
    vi.mocked(schemasAPI.getWorkflowPairs).mockRejectedValueOnce(new Error('offline'))
    await mountSettings()

    expect(snackbarState.show).toBe(true)
    expect(snackbarState.message).toBe('Failed to load workflow pairs')
  })

  it('makes the form read-only for non-admins', async () => {
    const { wrapper, vm } = await mountSettings({ role: 'curator' })

    expect(vm.canEditSettings).toBe(false)
    expect(wrapper.text()).not.toContain('Only scope administrators')
    expect(wrapper.findAll('button').some(b => b.text().includes('Save settings'))).toBe(false)
  })

  it('lets a scope admin edit settings even though the application role is user', async () => {
    useScopesStore().currentUserRole = 'admin'
    const { vm } = await mountSettings({ role: 'user' })

    expect(vm.canEditSettings).toBe(true)
  })

  it('keeps settings read-only for a scope curator with application role user', async () => {
    useScopesStore().currentUserRole = 'curator'
    const { vm } = await mountSettings({ role: 'user' })

    expect(vm.canEditSettings).toBe(false)
  })

  it('saves edited fields and the chosen workflow pair', async () => {
    const { wrapper, vm } = await mountSettings({ role: 'admin' })

    vm.editableScope.display_name = 'Kidney genetics'
    vm.handleWorkflowPairChange()
    expect(vm.isDirty).toBe(true)
    vm.selectedWorkflowPairId = 'wp-1'

    await vm.saveSettings()

    expect(scopesAPI.updateScope).toHaveBeenCalledWith('scope-1', {
      display_name: 'Kidney genetics',
      description: 'Renal',
      institution: 'Charité',
      is_public: false,
      default_workflow_pair_id: 'wp-1'
    })
    expect(vm.isDirty).toBe(false)
    expect(snackbarState.message).toBe('Settings saved successfully')
    expect(wrapper.emitted('updated')).toHaveLength(1)
  })

  it('reports a failed save with the error message', async () => {
    vi.mocked(scopesAPI.updateScope).mockRejectedValueOnce(new Error('conflict'))
    const { wrapper, vm } = await mountSettings({ role: 'admin' })

    await vm.saveSettings()

    expect(snackbarState.message).toBe('Failed to save settings: conflict')
    expect(wrapper.emitted('updated')).toBeUndefined()
  })

  it('re-initialises the form when the scope prop changes', async () => {
    const { wrapper, vm } = await mountSettings({ role: 'admin' })

    await wrapper.setProps({
      scope: { ...baseScope, display_name: 'Other', default_workflow_pair_id: 'wp-1' }
    })

    expect(vm.editableScope.display_name).toBe('Other')
    expect(vm.selectedWorkflowPairId).toBe('wp-1')
    expect(vm.isDirty).toBe(false)
  })

  it('lets app admins and the scope creator delete, but not other users', async () => {
    const creator = await mountSettings({ role: 'curator', userId: 'user-1' })
    expect(creator.vm.canDeleteScope).toBe(true)

    const admin = await mountSettings({ role: 'admin', userId: 'someone' })
    expect(admin.vm.canDeleteScope).toBe(true)

    const other = await mountSettings({ role: 'curator', userId: 'someone' })
    expect(other.vm.canDeleteScope).toBe(false)
  })

  it('requires typing the scope name before the delete button enables', async () => {
    const { vm } = await mountSettings({ role: 'admin', statistics: { total_genes_assigned: 3 } })
    expect(vm.hasActiveAssignments).toBe(true)

    vm.openDeleteDialog()
    await flushPromises()
    const button = () =>
      Array.from(document.body.querySelectorAll('button')).find(b =>
        b.textContent?.includes('Delete Kidney')
      )!
    expect(vm.showDeleteDialog).toBe(true)
    expect(vm.typedName).toBe('')
    expect(button().disabled).toBe(true)

    vm.typedName = 'Kidney'
    await flushPromises()
    expect(button().disabled).toBe(false)

    await vm.deleteScope()
    expect(scopesAPI.deleteScope).toHaveBeenCalledWith('scope-1', { force: true })
  })

  it('flattens the panel: one card, no nested alerts or tonal schema cards', async () => {
    useScopesStore().currentUserRole = 'admin'
    const { wrapper } = await mountSettings({
      role: 'admin',
      scope: { default_workflow_pair_id: 'wp-1' }
    })
    expect(wrapper.findAll('.v-card')).toHaveLength(1)
    expect(wrapper.findAll('.v-alert')).toHaveLength(0)
    expect(
      wrapper
        .findAll('li')
        .map(l => l.text())
        .join(' ')
    ).toContain('Precuration v1')
  })

  it('names the scope on the delete button with one red outline', async () => {
    const { wrapper } = await mountSettings({ role: 'admin' })
    const del = wrapper.findAll('button').find(b => b.text() === 'Delete Kidney')
    expect(del).toBeDefined()
    expect(wrapper.findAll('.text-error, .border-error').length).toBeLessThanOrEqual(2)
  })

  it('asks before leaving with unsaved edits, and not when clean', async () => {
    const { vm } = await mountSettings({ role: 'admin' })
    expect(await guard.fn!()).toBe(true)
    expect(confirm).not.toHaveBeenCalled()

    vm.handleWorkflowPairChange()
    confirm.mockResolvedValueOnce(false)
    expect(await guard.fn!()).toBe(false)
    confirm.mockResolvedValueOnce(true)
    expect(await guard.fn!()).toBe(true)
    expect(confirm).toHaveBeenCalledWith(expect.objectContaining({ destructive: true }))
  })

  it('deletes an empty scope without force and emits deleted', async () => {
    const { wrapper, vm } = await mountSettings({ role: 'admin' })
    vm.showDeleteDialog = true

    await vm.deleteScope()

    expect(scopesAPI.deleteScope).toHaveBeenCalledWith('scope-1', { force: false })
    expect(vm.showDeleteDialog).toBe(false)
    expect(wrapper.emitted('deleted')).toHaveLength(1)
  })

  it('clears the dirty flag on delete so leaving does not prompt', async () => {
    const { vm } = await mountSettings({ role: 'admin' })
    vm.isDirty = true

    await vm.deleteScope()

    expect(vm.isDirty).toBe(false)
  })

  it('shows the server detail when a delete is rejected', async () => {
    vi.mocked(scopesAPI.deleteScope).mockRejectedValueOnce(
      Object.assign(new Error('Request failed'), {
        isAxiosError: true,
        response: { data: { detail: 'Scope has schemas in use' } }
      })
    )
    const { wrapper, vm } = await mountSettings({ role: 'admin' })

    await vm.deleteScope()

    expect(snackbarState.message).toBe('Failed to delete scope: Scope has schemas in use')
    expect(wrapper.emitted('deleted')).toBeUndefined()
  })

  it('falls back to the plain error message for other delete failures', async () => {
    vi.mocked(scopesAPI.deleteScope).mockRejectedValueOnce(new Error('timeout'))
    const { vm } = await mountSettings({ role: 'admin' })

    await vm.deleteScope()

    expect(snackbarState.message).toBe('Failed to delete scope: timeout')
  })

  it('ignores Escape on the delete dialog while the delete is in flight', async () => {
    let finish: () => void = () => {}
    vi.mocked(scopesAPI.deleteScope).mockReturnValueOnce(
      new Promise<void>(resolve => {
        finish = resolve
      }) as never
    )
    const { wrapper, vm } = await mountSettings({ role: 'admin' })
    vm.showDeleteDialog = true
    const pending = vm.deleteScope()
    await flushPromises()

    const dialogs = wrapper.findAllComponents({ name: 'BaseDialog' })
    dialogs.forEach(d => d.vm.$emit('cancel'))
    expect(vm.showDeleteDialog).toBe(true)

    finish()
    await pending
    expect(wrapper.emitted('deleted')).toHaveLength(1)
  })
})
