import { describe, it, expect, vi, beforeEach } from 'vitest'
import { ref } from 'vue'
import { flushPromises, mount } from '@vue/test-utils'
import SchemaDrivenPrecurationForm from '../SchemaDrivenPrecurationForm.vue'

const logger = vi.hoisted(() => ({ debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() }))
const push = vi.hoisted(() => vi.fn())
const replace = vi.hoisted(() => vi.fn())
const addToast = vi.hoisted(() => vi.fn())
const precurationsStore = vi.hoisted(() => ({
  fetchPrecurationById: vi.fn(),
  saveDraft: vi.fn(),
  createPrecuration: vi.fn(),
  submitForReview: vi.fn()
}))
const history = vi.hoisted(() => ({ undo: vi.fn(), redo: vi.fn(), clearHistory: vi.fn() }))
const recovery = vi.hoisted(() => ({ clearRecovery: vi.fn() }))

vi.mock('@/composables/useLogger', () => ({ useLogger: () => logger }))
vi.mock('vue-router', () => ({ useRouter: () => ({ push, replace }) }))
vi.mock('@/stores/schemas', () => ({
  useSchemasStore: () => ({
    getSchemaById: (id: string) => ({ id, name: 'Panel schema' }),
    fetchSchemaById: vi.fn()
  })
}))
vi.mock('@/stores/precurations', () => ({ usePrecurationsStore: () => precurationsStore }))
vi.mock('@/stores/validation', () => ({
  useValidationStore: () => ({ generateJsonSchema: vi.fn() })
}))
vi.mock('@/stores/notifications', () => ({ useNotificationsStore: () => ({ addToast }) }))
vi.mock('@/composables/useFormRecovery', async () => {
  const { ref } = await import('vue')
  return {
    useFormRecovery: () => ({
      showRecoveryDialog: ref(false),
      recoveryData: ref(null),
      lastSaved: ref(null),
      restoreRecovery: vi.fn(),
      discardRecovery: vi.fn(),
      clearRecovery: recovery.clearRecovery
    })
  }
})
vi.mock('@/composables/useHistory', () => ({
  useHistory: () => ({
    canUndo: ref(false),
    canRedo: ref(false),
    recordAction: vi.fn(),
    undo: history.undo,
    redo: history.redo,
    clearHistory: history.clearHistory
  })
}))

/** Internal state read through wrapper.vm. */
interface SchemaPrecurationVm {
  evidenceData: Record<string, unknown>
  isValid: boolean
  handleKeydown(event: KeyboardEvent): void
  handleSaveDraft(): Promise<void>
  handleSubmit(): Promise<void>
  handleCancel(): void
  handleValidationChange(result: { is_valid?: boolean }): void
  handleEvidenceChange(data: Record<string, unknown>): void
  formatRelativeTime(timestamp: string | null): string
}

function internals(wrapper: { vm: unknown }): SchemaPrecurationVm {
  return wrapper.vm as SchemaPrecurationVm
}

const stubs = {
  ErrorBoundary: { template: '<div><slot /></div>' },
  DynamicForm: true,
  FormActions: true,
  FormRecoveryDialog: true
}

function mountForm(props: Record<string, unknown> = {}) {
  return mount(SchemaDrivenPrecurationForm, {
    props: { schemaId: 'schema-1', scopeId: 'scope-1', ...props },
    global: { stubs }
  })
}

describe('SchemaDrivenPrecurationForm', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    // happy-dom does not implement confirm()
    window.confirm = vi.fn(() => true)
  })

  it('creates a precuration on first draft save and navigates to its editor', async () => {
    precurationsStore.createPrecuration.mockResolvedValue({ id: 'new-p' })
    const wrapper = mountForm({ geneId: 'g-1' })
    await flushPromises()

    await internals(wrapper).handleSaveDraft()

    expect(precurationsStore.createPrecuration).toHaveBeenCalledWith({
      gene_id: 'g-1',
      scope_id: 'scope-1',
      precuration_schema_id: 'schema-1',
      evidence_data: {}
    })
    expect(replace).toHaveBeenCalledWith({
      name: 'scope-dashboard',
      params: { scopeId: 'scope-1' }
    })
    expect(addToast).toHaveBeenCalledWith('Draft saved', 'success')
  })

  it('does not create a precuration without a gene', async () => {
    const wrapper = mountForm()
    await flushPromises()

    await internals(wrapper).handleSaveDraft()

    expect(precurationsStore.createPrecuration).not.toHaveBeenCalled()
    expect(addToast).toHaveBeenCalledWith('Failed to save draft', 'error')
  })

  it('saves the draft of an existing precuration and emits saved', async () => {
    precurationsStore.saveDraft.mockResolvedValue({ id: 'p-1' })
    const wrapper = mountForm({ precurationId: 'p-1' })
    await flushPromises()

    await internals(wrapper).handleSaveDraft()

    expect(precurationsStore.saveDraft).toHaveBeenCalledWith('p-1', {})
    expect(wrapper.emitted('saved')).toHaveLength(1)
  })

  it('reports a failed draft save', async () => {
    precurationsStore.saveDraft.mockRejectedValue({ message: 'offline' })
    const wrapper = mountForm({ precurationId: 'p-1' })
    await flushPromises()

    await internals(wrapper).handleSaveDraft()

    expect(logger.error).toHaveBeenCalledWith('Failed to save draft', { error: 'offline' })
    expect(addToast).toHaveBeenCalledWith('Failed to save draft', 'error')
  })

  it('submits an existing precuration for review and emits submit', async () => {
    precurationsStore.submitForReview.mockResolvedValue({})
    const wrapper = mountForm({ precurationId: 'p-1' })
    await flushPromises()
    const vm = internals(wrapper)

    vm.handleValidationChange({ is_valid: true })
    await vm.handleSubmit()

    expect(precurationsStore.submitForReview).toHaveBeenCalledWith('p-1')
    expect(wrapper.emitted('submit')).toHaveLength(1)
    expect(addToast).toHaveBeenCalledWith('Precuration submitted for review', 'success')
  })

  it('creates and submits a new precuration in one step', async () => {
    precurationsStore.createPrecuration.mockResolvedValue({ id: 'new-p' })
    precurationsStore.submitForReview.mockResolvedValue({})
    const wrapper = mountForm({ geneId: 'g-1' })
    await flushPromises()

    await internals(wrapper).handleSubmit()

    expect(precurationsStore.submitForReview).toHaveBeenCalledWith('new-p')
  })

  it('does not submit while the evidence is invalid or read-only', async () => {
    const wrapper = mountForm({ precurationId: 'p-1', readonly: true })
    await flushPromises()
    const vm = internals(wrapper)

    vm.handleValidationChange({ is_valid: true })
    await vm.handleSubmit()

    expect(precurationsStore.submitForReview).not.toHaveBeenCalled()
  })

  it('reports a failed submission', async () => {
    precurationsStore.submitForReview.mockRejectedValue({ message: 'locked' })
    const wrapper = mountForm({ precurationId: 'p-1' })
    await flushPromises()

    await internals(wrapper).handleSubmit()

    expect(logger.error).toHaveBeenCalledWith('Failed to submit precuration', { error: 'locked' })
    expect(addToast).toHaveBeenCalledWith('Failed to submit precuration', 'error')
    expect(wrapper.emitted('submit')).toBeUndefined()
  })

  it('loads existing precuration data and draft state', async () => {
    precurationsStore.fetchPrecurationById.mockResolvedValue({
      evidence_data: { panel: 'x' },
      status: 'submitted'
    })
    const wrapper = mountForm({ precurationId: 'p-1' })
    await flushPromises()

    expect(internals(wrapper).evidenceData).toEqual({ panel: 'x' })
    expect(wrapper.text()).not.toContain('Draft')
  })

  it('reports a failed precuration load', async () => {
    precurationsStore.fetchPrecurationById.mockRejectedValue({ message: 'gone' })
    mountForm({ precurationId: 'p-1' })
    await flushPromises()

    expect(addToast).toHaveBeenCalledWith('Failed to load precuration', 'error')
  })

  it('tracks evidence and validation changes from DynamicForm', async () => {
    const wrapper = mountForm()
    await flushPromises()
    const vm = internals(wrapper)

    vm.handleEvidenceChange({ a: 1 })
    vm.handleValidationChange({ is_valid: false })

    expect(vm.evidenceData).toEqual({ a: 1 })
    expect(vm.isValid).toBe(false)
  })

  it('formats relative times for the saved indicator', () => {
    const wrapper = mountForm()
    const vm = internals(wrapper)
    const now = Date.now()

    expect(vm.formatRelativeTime(null)).toBe('')
    expect(vm.formatRelativeTime(new Date(now).toISOString())).toBe('just now')
    expect(vm.formatRelativeTime(new Date(now - 5 * 60_000).toISOString())).toBe('5m ago')
    expect(vm.formatRelativeTime(new Date(now - 3 * 3600_000).toISOString())).toBe('3h ago')
    expect(vm.formatRelativeTime(new Date(now - 2 * 86400_000).toISOString())).toBe('2d ago')
  })

  it('cancels only after confirmation when there is data', async () => {
    const wrapper = mountForm()
    await flushPromises()
    const vm = internals(wrapper)

    vm.handleEvidenceChange({ a: 1 })
    vi.mocked(window.confirm).mockReturnValueOnce(false)
    vm.handleCancel()
    expect(wrapper.emitted('cancel')).toBeUndefined()

    vm.handleCancel()
    expect(wrapper.emitted('cancel')).toHaveLength(1)
    expect(recovery.clearRecovery).toHaveBeenCalled()
  })

  it('routes Ctrl+Z and Escape keys from the form', async () => {
    const wrapper = mountForm()
    await flushPromises()
    const vm = internals(wrapper)

    vm.handleKeydown(new KeyboardEvent('keydown', { key: 'z', ctrlKey: true }))
    expect(history.undo).not.toHaveBeenCalled()

    // No evidence entered yet, so Escape cancels without asking for confirmation.
    vm.handleKeydown(new KeyboardEvent('keydown', { key: 'Escape' }))
    expect(window.confirm).not.toHaveBeenCalled()
    expect(wrapper.emitted('cancel')).toHaveLength(1)
  })
})
