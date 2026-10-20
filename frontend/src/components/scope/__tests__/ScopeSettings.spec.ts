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
  deleteConfirmed: boolean
  showDeleteDialog: boolean
  showSnackbar: boolean
  snackbarMessage: string
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
  is_active: true
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
    expect(wrapper.text()).not.toContain('Linked Schemas')
  })

  it('shows the linked schemas of the configured workflow pair', async () => {
    const { wrapper } = await mountSettings({ scope: { default_workflow_pair_id: 'wp-1' } })

    expect(wrapper.text()).not.toContain('No workflow configured.')
    expect(wrapper.text()).toContain('Linked Schemas')
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
    const { vm } = await mountSettings()

    expect(vm.showSnackbar).toBe(true)
    expect(vm.snackbarMessage).toBe('Failed to load workflow pairs')
  })

  it('makes the form read-only for non-admins', async () => {
    const { wrapper, vm } = await mountSettings({ role: 'curator' })

    expect(vm.canEditSettings).toBe(false)
    expect(wrapper.text()).toContain('Only scope administrators can modify these settings.')
    expect(wrapper.findAll('button').some(b => b.text().includes('Save Settings'))).toBe(false)
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
    expect(vm.snackbarMessage).toBe('Settings saved successfully')
    expect(wrapper.emitted('updated')).toHaveLength(1)
  })

  it('reports a failed save with the error message', async () => {
    vi.mocked(scopesAPI.updateScope).mockRejectedValueOnce(new Error('conflict'))
    const { wrapper, vm } = await mountSettings({ role: 'admin' })

    await vm.saveSettings()

    expect(vm.snackbarMessage).toBe('Failed to save settings: conflict')
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

  it('requires confirmation before deleting a scope with gene assignments', async () => {
    const { vm } = await mountSettings({ role: 'admin', statistics: { total_genes_assigned: 3 } })
    expect(vm.hasActiveAssignments).toBe(true)

    vm.openDeleteDialog()
    expect(vm.showDeleteDialog).toBe(true)
    expect(vm.deleteConfirmed).toBe(false)

    vm.deleteConfirmed = true
    await vm.deleteScope()

    expect(scopesAPI.deleteScope).toHaveBeenCalledWith('scope-1', { force: true })
  })

  it('deletes an empty scope without force and emits deleted', async () => {
    const { wrapper, vm } = await mountSettings({ role: 'admin' })
    vm.showDeleteDialog = true

    await vm.deleteScope()

    expect(scopesAPI.deleteScope).toHaveBeenCalledWith('scope-1', { force: false })
    expect(vm.showDeleteDialog).toBe(false)
    expect(wrapper.emitted('deleted')).toHaveLength(1)
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

    expect(vm.snackbarMessage).toBe('Failed to delete scope: Scope has schemas in use')
    expect(wrapper.emitted('deleted')).toBeUndefined()
  })

  it('falls back to the plain error message for other delete failures', async () => {
    vi.mocked(scopesAPI.deleteScope).mockRejectedValueOnce(new Error('timeout'))
    const { vm } = await mountSettings({ role: 'admin' })

    await vm.deleteScope()

    expect(vm.snackbarMessage).toBe('Failed to delete scope: timeout')
  })
})
