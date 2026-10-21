import { describe, it, expect, vi, beforeEach } from 'vitest'
import { ref } from 'vue'
import { flushPromises, mount } from '@vue/test-utils'
import SchemaDrivenPrecurationForm from '../SchemaDrivenPrecurationForm.vue'

const confirmMock = vi.hoisted(() => vi.fn())
vi.mock('@/composables/useConfirm', () => ({ useConfirm: () => ({ confirm: confirmMock }) }))

const logger = vi.hoisted(() => ({ debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() }))
const push = vi.hoisted(() => vi.fn())
const replace = vi.hoisted(() => vi.fn())
const addToast = vi.hoisted(() => vi.fn())
const precurationsStore = vi.hoisted(() => ({
  fetchPrecurationById: vi.fn(),
  saveDraft: vi.fn(),
  createPrecuration: vi.fn(),
  submitForReview: vi.fn(),
  error: null as { message?: string; isConflict?: boolean } | null
}))
const history = vi.hoisted(() => ({ undo: vi.fn(), redo: vi.fn(), clearHistory: vi.fn() }))
const recovery = vi.hoisted(() => ({ clearRecovery: vi.fn(), dropIfSaved: vi.fn() }))
const schemaFields = vi.hoisted(() => ({ value: undefined as Record<string, unknown> | undefined }))

vi.mock('@/composables/useLogger', () => ({ useLogger: () => logger }))
vi.mock('vue-router', () => ({ useRouter: () => ({ push, replace }) }))
vi.mock('@/stores/schemas', () => ({
  useSchemasStore: () => ({
    getSchemaById: (id: string) => ({ id, name: 'Panel schema' }),
    fetchPinnedVersion: (versionId: string | null) =>
      Promise.resolve({
        id: versionId ?? 'latest',
        snapshot: { field_definitions: schemaFields.value }
      })
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
      clearRecovery: recovery.clearRecovery,
      dropIfSaved: recovery.dropIfSaved
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
    precurationsStore.error = null
    vi.clearAllMocks()
    confirmMock.mockResolvedValue(true)
    schemaFields.value = undefined
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
      name: 'precuration-edit',
      params: { scopeId: 'scope-1', precurationId: 'new-p' }
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

  describe('conflict (another tab saved first)', () => {
    const conflictError = {
      message: 'Another user or tab has modified this precuration.',
      isConflict: true
    }

    it('shows Edited elsewhere with Reload, and blocks further saves', async () => {
      precurationsStore.saveDraft.mockResolvedValue(null)
      precurationsStore.error = conflictError
      const wrapper = mountForm({ precurationId: 'p-1' })
      await internals(wrapper).handleSaveDraft()
      await flushPromises()

      expect(wrapper.text()).toContain('Edited elsewhere')
      expect(wrapper.find('[role="alert"] button').text()).toBe('Reload')

      precurationsStore.saveDraft.mockClear()
      await internals(wrapper).handleSaveDraft()
      await internals(wrapper).handleSubmit()
      expect(precurationsStore.saveDraft).not.toHaveBeenCalled()
      expect(precurationsStore.submitForReview).not.toHaveBeenCalled()
      // Reload must not offer the stale local copy back
      expect(recovery.clearRecovery).toHaveBeenCalled()
    })

    it('shows it when the submit itself is refused as stale', async () => {
      precurationsStore.saveDraft.mockResolvedValue({ id: 'p-1' })
      precurationsStore.submitForReview.mockRejectedValue({ message: 'Request failed' })
      precurationsStore.error = conflictError
      const wrapper = mountForm({ precurationId: 'p-1' })
      internals(wrapper).handleEvidenceChange({ a: 1 })
      internals(wrapper).handleValidationChange({ is_valid: true })
      await internals(wrapper).handleSubmit()
      await flushPromises()

      expect(wrapper.text()).toContain('Edited elsewhere')
      expect(addToast).not.toHaveBeenCalledWith('Precuration submitted for review', 'success')
    })
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
    precurationsStore.saveDraft.mockResolvedValue({ id: 'p-1' })
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

  it('retries a failed new submission on the same record and shows the API detail', async () => {
    precurationsStore.createPrecuration.mockResolvedValue({ id: 'new-p' })
    precurationsStore.submitForReview
      .mockRejectedValueOnce({ response: { data: { detail: 'Invalid transition' } } })
      .mockResolvedValueOnce({})
    precurationsStore.saveDraft.mockResolvedValue({})
    const wrapper = mountForm({ geneId: 'g-1' })
    await flushPromises()

    await internals(wrapper).handleSubmit()
    expect(addToast).toHaveBeenCalledWith('Invalid transition', 'error')
    await internals(wrapper).handleSubmit()

    expect(precurationsStore.createPrecuration).toHaveBeenCalledTimes(1)
    expect(precurationsStore.submitForReview).toHaveBeenLastCalledWith('new-p')
    expect(wrapper.emitted('submit')).toHaveLength(1)
    // The retry saves the curator's current edits to the created record first.
    expect(precurationsStore.saveDraft).toHaveBeenCalledTimes(1)
    expect(precurationsStore.saveDraft.mock.calls[0]?.[0]).toBe('new-p')
  })

  it('saves to the record created by a failed submit instead of creating another', async () => {
    precurationsStore.createPrecuration.mockResolvedValue({ id: 'new-p' })
    precurationsStore.submitForReview.mockRejectedValueOnce({ message: 'locked' })
    precurationsStore.saveDraft.mockResolvedValue({})
    const wrapper = mountForm({ geneId: 'g-1' })
    await flushPromises()

    await internals(wrapper).handleSubmit()
    await internals(wrapper).handleSaveDraft()

    expect(precurationsStore.createPrecuration).toHaveBeenCalledTimes(1)
    expect(precurationsStore.saveDraft.mock.calls[0]?.[0]).toBe('new-p')
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
    precurationsStore.submitForReview.mockRejectedValue({
      message: 'locked',
      response: { data: { detail: 'locked' } }
    })
    const wrapper = mountForm({ precurationId: 'p-1' })
    await flushPromises()

    await internals(wrapper).handleSubmit()

    expect(logger.error).toHaveBeenCalledWith('Failed to submit precuration', { error: 'locked' })
    expect(addToast).toHaveBeenCalledWith('locked', 'error')
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

  it('renders and validates the version the precuration is pinned to', async () => {
    precurationsStore.fetchPrecurationById.mockResolvedValue({
      evidence_data: {},
      status: 'draft',
      methodology_version_id: 'v-old'
    })
    const wrapper = mountForm({ precurationId: 'p-1' })
    await flushPromises()
    expect(wrapper.html()).toContain('methodologyversionid="v-old"')
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
    confirmMock.mockResolvedValueOnce(false)
    await vm.handleCancel()
    expect(wrapper.emitted('cancel')).toBeUndefined()

    await vm.handleCancel()
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
    expect(confirmMock).not.toHaveBeenCalled()
    expect(wrapper.emitted('cancel')).toHaveLength(1)
  })

  it('leaves Escape in a field or select to that control', async () => {
    const wrapper = mountForm()
    await flushPromises()
    const vm = internals(wrapper)
    for (const html of ['<input>', '<input role="combobox" aria-expanded="false">']) {
      const form = document.createElement('form')
      form.innerHTML = html
      form.addEventListener('keydown', e => vm.handleKeydown(e))
      form.firstElementChild!.dispatchEvent(
        new KeyboardEvent('keydown', { key: 'Escape', bubbles: true })
      )
    }
    expect(wrapper.emitted('cancel')).toBeUndefined()
  })

  describe('monkey-test findings', () => {
    const required = {
      entity_definition: {
        type: 'object',
        properties: {
          disease_name: { type: 'string', required: true, label: 'Disease name' },
          mode_of_inheritance: { type: 'enum', required: true }
        }
      }
    }

    it('refuses to submit an empty precuration and names the missing fields by label', async () => {
      schemaFields.value = required
      const wrapper = mountForm({ precurationId: 'p-1' })
      await flushPromises()

      await internals(wrapper).handleSubmit()

      expect(precurationsStore.submitForReview).not.toHaveBeenCalled()
      const [message, kind] = addToast.mock.calls.at(-1) as [string, string]
      expect(kind).toBe('error')
      expect(message).toContain('Disease name')
      expect(message).toContain('Mode of inheritance')
      expect(message).not.toContain('entity_definition')
    })

    it('submits once the required fields are filled', async () => {
      schemaFields.value = required
      precurationsStore.submitForReview.mockResolvedValue({})
      const wrapper = mountForm({ precurationId: 'p-1' })
      await flushPromises()
      internals(wrapper).handleEvidenceChange({
        entity_definition: { disease_name: 'X', mode_of_inheritance: 'unknown' }
      })

      await internals(wrapper).handleSubmit()

      expect(precurationsStore.submitForReview).toHaveBeenCalledWith('p-1')
    })

    it('saves the current edits before submitting an existing precuration', async () => {
      precurationsStore.saveDraft.mockResolvedValue({ id: 'p-1' })
      precurationsStore.submitForReview.mockResolvedValue({})
      const wrapper = mountForm({ precurationId: 'p-1' })
      await flushPromises()
      internals(wrapper).handleEvidenceChange({ a: 'edited' })

      await internals(wrapper).handleSubmit()

      expect(precurationsStore.saveDraft).toHaveBeenCalledWith('p-1', { a: 'edited' })
      expect(precurationsStore.saveDraft.mock.invocationCallOrder[0]).toBeLessThan(
        precurationsStore.submitForReview.mock.invocationCallOrder[0]!
      )
    })

    it('does not submit when saving the edits fails', async () => {
      precurationsStore.saveDraft.mockResolvedValue(null)
      const wrapper = mountForm({ precurationId: 'p-1' })
      await flushPromises()

      await internals(wrapper).handleSubmit()

      expect(precurationsStore.submitForReview).not.toHaveBeenCalled()
      expect(addToast).toHaveBeenCalledWith('Failed to submit precuration', 'error')
    })

    it('shows the API detail of a rejected submit', async () => {
      precurationsStore.saveDraft.mockResolvedValue({ id: 'p-1' })
      precurationsStore.submitForReview.mockRejectedValue({
        response: { data: { detail: { message: 'Missing required fields: notes', fields: [] } } }
      })
      const wrapper = mountForm({ precurationId: 'p-1' })
      await flushPromises()

      await internals(wrapper).handleSubmit()

      expect(addToast).toHaveBeenCalledWith('Missing required fields: notes', 'error')
    })

    it('does not claim success when the draft save fails', async () => {
      precurationsStore.saveDraft.mockResolvedValue(null)
      const wrapper = mountForm({ precurationId: 'p-1' })
      await flushPromises()

      await internals(wrapper).handleSaveDraft()

      expect(addToast).not.toHaveBeenCalledWith('Draft saved', 'success')
      expect(addToast).toHaveBeenCalledWith('Failed to save draft', 'error')
      expect(recovery.clearRecovery).not.toHaveBeenCalled()
    })

    it('saves the draft on Ctrl+S pressed inside the form', async () => {
      precurationsStore.saveDraft.mockResolvedValue({ id: 'p-1' })
      const wrapper = mountForm({ precurationId: 'p-1' })
      await flushPromises()

      await wrapper.find('form').trigger('keydown', { key: 's', ctrlKey: true })
      await flushPromises()

      expect(precurationsStore.saveDraft).toHaveBeenCalled()
    })

    it('saves on Ctrl+S pressed with focus inside a text field', async () => {
      precurationsStore.saveDraft.mockResolvedValue({ id: 'p-1' })
      const wrapper = mount(SchemaDrivenPrecurationForm, {
        props: { schemaId: 'schema-1', scopeId: 'scope-1', precurationId: 'p-1' },
        attachTo: document.body,
        global: {
          stubs: {
            ...stubs,
            DynamicForm: { template: '<form><input id="field" type="text" /></form>' }
          }
        }
      })
      await flushPromises()

      const input = wrapper.find('#field')
      ;(input.element as HTMLInputElement).focus()
      const event = new KeyboardEvent('keydown', {
        key: 's',
        ctrlKey: true,
        bubbles: true,
        cancelable: true
      })
      input.element.dispatchEvent(event)
      await flushPromises()

      expect(precurationsStore.saveDraft).toHaveBeenCalled()
      expect(event.defaultPrevented).toBe(true)
      wrapper.unmount()
    })

    it('drops a recovery snapshot equal to the loaded draft', async () => {
      precurationsStore.fetchPrecurationById.mockResolvedValue({
        evidence_data: { a: 1 },
        status: 'draft'
      })
      mountForm({ precurationId: 'p-1' })
      await flushPromises()

      expect(recovery.dropIfSaved).toHaveBeenCalledWith({ a: 1 })
    })

    it('hides Save draft and Submit when read-only', async () => {
      const wrapper = mountForm({ precurationId: 'p-1', readonly: true })
      await flushPromises()

      expect(wrapper.findComponent({ name: 'FormActions' }).exists()).toBe(false)
    })
  })
})
